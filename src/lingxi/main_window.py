from __future__ import annotations

from pathlib import Path
import time

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QStandardPaths, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .export import export_csv
from .protocol import SampleFrame
from .serial_worker import SerialWorker, available_ports
from .settings import load_settings, save_settings
from .signal_processing import adc_to_voltage, align_trigger, analyze_spectrum, measure_waveform
from .simulator import SignalSimulator
from .theme import LIQUID_GLASS_QSS, load_chinese_font
from .widgets import GlassCard, LiquidBackground, MetricCard


GAIN_LABELS = ["×1", "×5", "×20", "×100"]
INPUT_SCALES = {0: 5.0 / 1.65, 1: 1.0 / 1.65, 2: 0.25 / 1.65, 3: 0.05 / 1.65}


class MainWindow(QMainWindow):
    def __init__(self, start_simulator: bool = True) -> None:
        super().__init__()
        self.setWindowTitle("灵析 X1 · 智能信号分析终端")
        self.resize(1440, 860)
        self.setMinimumSize(1120, 700)
        load_chinese_font()
        self.setStyleSheet(LIQUID_GLASS_QSS)
        self._settings_path = Path(QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)) / "settings.json"
        self.settings_data = load_settings(self._settings_path)
        self.simulator = SignalSimulator(sample_rate=100_000, sample_count=4096)
        self.serial_worker: SerialWorker | None = None
        self.latest_frame: SampleFrame | None = None
        self.latest_voltage: np.ndarray | None = None
        self.running = start_simulator
        self.single_pending = False
        self.single_wait_sequence: int | None = None
        self.single_frame_ready = False
        self.single_deadline = 0.0
        self.simulator_enabled = start_simulator
        self.stream_source = "simulator" if start_simulator else "none"
        self.last_sequence: int | None = None
        self.dropped_frames = 0
        self.protocol_errors = 0
        self.received_frames = 0
        self.rendered_frames = 0
        self.last_fps_time = time.monotonic()
        self.last_analysis_time = 0.0
        self._time_axis_key: tuple[int, int] | None = None
        self._time_axis = np.empty(0)

        self._build_ui()
        self._configure_plots()
        self._refresh_ports()

        self.display_timer = QTimer(self)
        self.display_timer.timeout.connect(self._tick)
        self.display_timer.setTimerType(Qt.PreciseTimer)
        self.display_timer.start(16)
        if start_simulator:
            self.statusBar().showMessage("模拟信号模式 · 设备未连接")

    def _build_ui(self) -> None:
        background = LiquidBackground()
        self.setCentralWidget(background)
        root = QVBoxLayout(background)
        root.setContentsMargins(22, 18, 22, 16)
        root.setSpacing(14)

        header = GlassCard()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("灵析 X1")
        title.setObjectName("appTitle")
        subtitle = QLabel("便携式智能信号测量与频谱分析系统")
        subtitle.setObjectName("appSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(110)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["115200", "256000", "460800", "921600"])
        self.baud_combo.setCurrentText(str(self.settings_data["baud_rate"]))
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self._refresh_ports)
        self.connect_button = QPushButton("连接设备")
        self.connect_button.setObjectName("primaryButton")
        self.connect_button.clicked.connect(self._toggle_connection)
        self.mode_button = QPushButton("模拟模式")
        self.mode_button.clicked.connect(self._toggle_simulator)
        self.run_button = QPushButton("暂停" if self.running else "运行")
        self.run_button.clicked.connect(self._toggle_run)
        single_button = QPushButton("单次")
        single_button.clicked.connect(self._single)
        export_button = QPushButton("导出")
        export_button.clicked.connect(self._export_data)
        screenshot_button = QPushButton("截图")
        screenshot_button.clicked.connect(self._save_screenshot)
        for widget in (self.port_combo, self.baud_combo, refresh_button, self.connect_button, self.mode_button, self.run_button, single_button, export_button, screenshot_button):
            header_layout.addWidget(widget)
        root.addWidget(header)

        content = QHBoxLayout()
        content.setSpacing(14)
        content.addWidget(self._build_control_card(), 0)
        content.addWidget(self._build_plot_card(), 1)
        content.addWidget(self._build_metrics_card(), 0)
        root.addLayout(content, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_connection = QLabel("● 模拟模式")
        self.status_rate = QLabel("0 FPS")
        self.status_errors = QLabel("丢帧 0 · 协议错误 0")
        status.addWidget(self.status_connection)
        status.addPermanentWidget(self.status_rate)
        status.addPermanentWidget(self.status_errors)

    def _build_control_card(self) -> QFrame:
        card = GlassCard()
        card.setFixedWidth(215)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(9)
        section = QLabel("采集控制")
        section.setObjectName("sectionTitle")
        layout.addWidget(section)

        self.waveform_combo = self._labeled_combo(layout, "模拟波形", ["正弦波", "方波", "三角波", "失真正弦"])
        self.frequency_spin = self._labeled_spin(layout, "频率 / Hz", 1, 50_000, 1000, 100)
        self.amplitude_spin = self._labeled_double(layout, "峰值 / V", 0.01, 4.5, 1.0, 0.1)
        self.offset_spin = self._labeled_double(layout, "偏置 / V", -4.0, 4.0, 0.0, 0.1)
        self.gain_combo = self._labeled_combo(layout, "模拟增益", GAIN_LABELS)
        self.coupling_combo = self._labeled_combo(layout, "输入耦合", ["DC", "AC"])
        self.gain_combo.currentIndexChanged.connect(self._gain_changed)
        self.coupling_combo.currentTextChanged.connect(self._coupling_changed)
        layout.addSpacing(5)
        trigger_title = QLabel("触发")
        trigger_title.setObjectName("sectionTitle")
        layout.addWidget(trigger_title)
        self.trigger_mode_combo = self._labeled_combo(layout, "模式", ["自动", "正常", "单次"])
        self.trigger_edge_combo = self._labeled_combo(layout, "触发沿", ["上升沿", "下降沿"])
        self.trigger_level_spin = self._labeled_double(layout, "触发电平 / V", -10.0, 10.0, 0.0, 0.05)
        layout.addStretch()
        hint = QLabel("提示：先用模拟模式检查界面，\n接板后切换至串口模式。")
        hint.setObjectName("appSubtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return card

    def _build_plot_card(self) -> QFrame:
        card = GlassCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 12)
        self.tabs = QTabWidget()
        self.time_plot = pg.PlotWidget()
        self.spectrum_plot = pg.PlotWidget()
        self.tabs.addTab(self.time_plot, "时域")
        self.tabs.addTab(self.spectrum_plot, "频谱 / FFT")
        layout.addWidget(self.tabs)
        return card

    def _build_metrics_card(self) -> QFrame:
        card = GlassCard()
        card.setFixedWidth(270)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        title = QLabel("实时测量")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        grid = QGridLayout()
        grid.setSpacing(8)
        definitions = [
            ("frequency", "频率", "— Hz"),
            ("vpp", "峰峰值", "— V"),
            ("rms", "交流 RMS", "— V"),
            ("mean", "直流偏置", "— V"),
            ("duty", "占空比", "— %"),
            ("thd", "总谐波失真", "— %"),
        ]
        self.metric_cards: dict[str, MetricCard] = {}
        for index, (key, caption, value) in enumerate(definitions):
            metric = MetricCard(caption, value)
            self.metric_cards[key] = metric
            grid.addWidget(metric, index // 2, index % 2)
        layout.addLayout(grid)
        harmonic_title = QLabel("谐波成分")
        harmonic_title.setObjectName("sectionTitle")
        layout.addWidget(harmonic_title)
        self.harmonic_labels: dict[int, QLabel] = {}
        for number in range(2, 6):
            row = QHBoxLayout()
            label = QLabel(f"H{number}")
            value = QLabel("— %")
            value.setAlignment(Qt.AlignRight)
            value.setObjectName("appSubtitle")
            row.addWidget(label)
            row.addStretch()
            row.addWidget(value)
            layout.addLayout(row)
            self.harmonic_labels[number] = value
        layout.addStretch()
        self.frame_info = QLabel("等待数据")
        self.frame_info.setWordWrap(True)
        self.frame_info.setObjectName("appSubtitle")
        layout.addWidget(self.frame_info)
        return card

    def _configure_plots(self) -> None:
        pg.setConfigOptions(antialias=False, foreground="#687386")
        for plot in (self.time_plot, self.spectrum_plot):
            plot.setBackground(QColor(255, 255, 255, 165))
            plot.showGrid(x=True, y=True, alpha=0.12)
            plot.getPlotItem().getViewBox().setBorder(pg.mkPen((95, 107, 125, 35)))
        self.time_plot.setLabel("bottom", "时间", units="s")
        self.time_plot.setLabel("left", "电压", units="V")
        self.spectrum_plot.setLabel("bottom", "频率", units="Hz")
        self.spectrum_plot.setLabel("left", "幅值", units="V")
        self.time_curve = self.time_plot.plot(pen=pg.mkPen(QColor("#007AFF"), width=1.5))
        self.spectrum_curve = self.spectrum_plot.plot(pen=pg.mkPen(QColor("#AF52DE"), width=2.0), fillLevel=0, brush=(175, 82, 222, 28))
        self.time_curve.setDownsampling(auto=True, method="peak")
        self.time_curve.setClipToView(True)
        self.spectrum_curve.setDownsampling(auto=True, method="peak")
        self.spectrum_curve.setClipToView(True)
        self.trigger_line = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen((255, 149, 0, 185), width=1, style=Qt.DashLine))
        self.trigger_line.sigPositionChanged.connect(lambda: self.trigger_level_spin.setValue(self.trigger_line.value()))
        self.time_plot.addItem(self.trigger_line)

    @staticmethod
    def _labeled_combo(layout: QVBoxLayout, label: str, values: list[str]) -> QComboBox:
        layout.addWidget(QLabel(label))
        combo = QComboBox()
        combo.addItems(values)
        layout.addWidget(combo)
        return combo

    @staticmethod
    def _labeled_spin(layout: QVBoxLayout, label: str, minimum: int, maximum: int, value: int, step: int) -> QSpinBox:
        layout.addWidget(QLabel(label))
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSingleStep(step)
        spin.setGroupSeparatorShown(True)
        MainWindow._add_stepper(layout, spin)
        return spin

    @staticmethod
    def _labeled_double(layout: QVBoxLayout, label: str, minimum: float, maximum: float, value: float, step: float) -> QDoubleSpinBox:
        layout.addWidget(QLabel(label))
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSingleStep(step)
        spin.setDecimals(2)
        MainWindow._add_stepper(layout, spin)
        return spin

    @staticmethod
    def _add_stepper(layout: QVBoxLayout, spin: QSpinBox | QDoubleSpinBox) -> None:
        spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(spin, 1)
        minus = QPushButton("−")
        plus = QPushButton("+")
        for button in (minus, plus):
            button.setObjectName("roundStepper")
            button.setCursor(Qt.PointingHandCursor)
        minus.clicked.connect(spin.stepDown)
        plus.clicked.connect(spin.stepUp)
        row.addWidget(minus)
        row.addWidget(plus)
        layout.addLayout(row)

    def _refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        ports = available_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports or ["未发现串口"])
        if current in ports:
            self.port_combo.setCurrentText(current)

    def _toggle_connection(self) -> None:
        if self.serial_worker and self.serial_worker.isRunning():
            self.serial_worker.stop()
            self.serial_worker = None
            self.connect_button.setText("连接设备")
            self._reset_stream_state("none")
            return
        port = self.port_combo.currentText()
        if not port or port == "未发现串口":
            QMessageBox.information(self, "未发现设备", "请连接设备后刷新串口列表。也可以先使用模拟模式。")
            return
        self.simulator_enabled = False
        self.mode_button.setText("启用模拟")
        self._reset_stream_state("serial")
        self.serial_worker = SerialWorker(port, int(self.baud_combo.currentText()), self)
        self.serial_worker.frame_received.connect(self._accept_frame)
        self.serial_worker.connection_changed.connect(self._connection_changed)
        self.serial_worker.counters_changed.connect(self._protocol_counters)
        self.serial_worker.start()

    def _connection_changed(self, connected: bool, message: str) -> None:
        self.connect_button.setText("断开设备" if connected else "连接设备")
        self.status_connection.setText(("● " if connected else "○ ") + message)

    def _protocol_counters(self, crc_errors: int, format_errors: int) -> None:
        self.protocol_errors = crc_errors + format_errors
        self._update_error_status()

    def _toggle_simulator(self) -> None:
        self.simulator_enabled = not self.simulator_enabled
        if self.simulator_enabled and self.serial_worker and self.serial_worker.isRunning():
            self.serial_worker.stop()
            self.serial_worker = None
            self.connect_button.setText("连接设备")
        self._reset_stream_state("simulator" if self.simulator_enabled else "none")
        self.mode_button.setText("关闭模拟" if self.simulator_enabled else "启用模拟")
        self.status_connection.setText("● 模拟模式" if self.simulator_enabled else "○ 等待设备")

    def _toggle_run(self) -> None:
        self.running = not self.running
        self.run_button.setText("暂停" if self.running else "运行")
        if self.serial_worker:
            self.serial_worker.send_command("RUN" if self.running else "STOP")

    def _single(self) -> None:
        self.single_pending = True
        self.single_wait_sequence = self.last_sequence
        self.single_frame_ready = False
        self.single_deadline = time.monotonic() + 2.0
        self.running = True
        if self.serial_worker:
            self.serial_worker.send_command("SINGLE")

    def _tick(self) -> None:
        if not self.running:
            return
        if self.simulator_enabled:
            names = {"正弦波": "sine", "方波": "square", "三角波": "triangle", "失真正弦": "distorted"}
            self._accept_frame(
                self.simulator.frame(
                    names[self.waveform_combo.currentText()],
                    self.frequency_spin.value(),
                    self.amplitude_spin.value(),
                    self.offset_spin.value(),
                    noise=0.0,
                    third_harmonic=0.12,
                    gain_code=self.gain_combo.currentIndex(),
                    coupling=self.coupling_combo.currentText(),
                )
            )
        if self.single_pending and not self.single_frame_ready:
            if time.monotonic() >= self.single_deadline:
                self.single_pending = False
                self.running = False
                self.run_button.setText("运行")
                self.statusBar().showMessage("单次采集超时：未收到新数据帧", 5000)
            return
        rendered = self.latest_frame is not None and self._render_frame(self.latest_frame)
        if self.single_pending and self.single_frame_ready and rendered:
            self.single_pending = False
            self.single_frame_ready = False
            self.running = False
            self.run_button.setText("运行")

    def _accept_frame(self, frame: SampleFrame) -> None:
        if self.last_sequence is not None:
            delta = (frame.sequence - self.last_sequence) & 0xFFFF
            if 1 < delta < 0x8000:
                self.dropped_frames += delta - 1
        self.last_sequence = frame.sequence
        self.latest_frame = frame
        self.received_frames += 1
        if self.single_pending and (self.single_wait_sequence is None or frame.sequence != self.single_wait_sequence):
            self.single_frame_ready = True

    def _render_frame(self, frame: SampleFrame) -> bool:
        scale = INPUT_SCALES.get(frame.gain_code, INPUT_SCALES[0])
        voltage = adc_to_voltage(frame.samples, frame.adc_bits, frame.vref_mv, frame.zero_code, scale)
        level = self.trigger_level_spin.value()
        edge = "falling" if self.trigger_edge_combo.currentText() == "下降沿" else "rising"
        aligned = align_trigger(voltage, level, edge)
        mode = self.trigger_mode_combo.currentText()
        if aligned is not None:
            voltage = aligned
        elif mode in ("正常", "单次"):
            return False
        self.latest_voltage = voltage
        axis_key = (len(voltage), frame.sample_rate)
        if axis_key != self._time_axis_key:
            self._time_axis_key = axis_key
            self._time_axis = np.arange(len(voltage)) / frame.sample_rate
        self.time_curve.setData(self._time_axis, voltage, skipFiniteCheck=True)
        if abs(self.trigger_line.value() - level) > 1e-9:
            self.trigger_line.setValue(level)
        now = time.monotonic()
        if now - self.last_analysis_time >= 0.1:
            self.last_analysis_time = now
            measurements = measure_waveform(voltage, frame.sample_rate)
            spectrum = analyze_spectrum(voltage, frame.sample_rate)
            self.spectrum_curve.setData(spectrum.frequencies, spectrum.amplitudes, skipFiniteCheck=True)
            self.metric_cards["frequency"].set_value(self._format_frequency(measurements.frequency_hz))
            self.metric_cards["vpp"].set_value(f"{measurements.vpp:.3f} V")
            self.metric_cards["rms"].set_value(f"{measurements.rms_ac:.3f} V")
            self.metric_cards["mean"].set_value(f"{measurements.mean:+.3f} V")
            self.metric_cards["duty"].set_value(f"{measurements.duty_percent:.1f} %")
            self.metric_cards["thd"].set_value(f"{spectrum.thd_percent:.2f} %")
            for number, label in self.harmonic_labels.items():
                label.setText(f"{spectrum.harmonics_percent[number]:.2f} %")
            self.frame_info.setText(
                f"{len(voltage)} 点 · {frame.sample_rate / 1000:.1f} kSa/s\n"
                f"{GAIN_LABELS[min(frame.gain_code, 3)]} · {frame.coupling} · 序号 {frame.sequence}"
            )
        self.rendered_frames += 1
        elapsed = time.monotonic() - self.last_fps_time
        if elapsed >= 0.5:
            fps = self.rendered_frames / elapsed
            self.status_rate.setText(f"显示 {fps:.1f} FPS · {frame.sample_rate / 1000:.0f} kSa/s")
            self.received_frames = 0
            self.rendered_frames = 0
            self.last_fps_time = time.monotonic()
        self._update_error_status()
        return True

    def _reset_stream_state(self, source: str) -> None:
        self.stream_source = source
        self.last_sequence = None
        self.dropped_frames = 0
        self.protocol_errors = 0
        self.received_frames = 0
        self.rendered_frames = 0
        self.last_fps_time = time.monotonic()
        self.last_analysis_time = 0.0
        self._time_axis_key = None
        self.latest_frame = None
        self.latest_voltage = None
        self.single_pending = False
        self.single_frame_ready = False
        self._update_error_status()

    def _update_error_status(self) -> None:
        self.status_errors.setText(f"丢帧 {self.dropped_frames} · 协议错误 {self.protocol_errors}")

    def _gain_changed(self, index: int) -> None:
        if self.serial_worker and self.serial_worker.isRunning():
            self.serial_worker.send_command(f"GAIN {index}")

    def _coupling_changed(self, coupling: str) -> None:
        if self.serial_worker and self.serial_worker.isRunning():
            self.serial_worker.send_command(f"COUPLING {coupling}")

    @staticmethod
    def _format_frequency(value: float) -> str:
        if value >= 1_000_000:
            return f"{value / 1_000_000:.3f} MHz"
        if value >= 1000:
            return f"{value / 1000:.3f} kHz"
        return f"{value:.1f} Hz"

    def _export_data(self) -> None:
        if self.latest_voltage is None or self.latest_frame is None:
            QMessageBox.information(self, "没有数据", "请先采集或生成一帧波形。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出波形数据", "lingxi-wave.csv", "CSV 文件 (*.csv)")
        if path:
            time_s = np.arange(len(self.latest_voltage)) / self.latest_frame.sample_rate
            export_csv(path, time_s, self.latest_voltage, {"sample_rate": self.latest_frame.sample_rate, "coupling": self.latest_frame.coupling, "gain_code": self.latest_frame.gain_code})
            self.statusBar().showMessage(f"已导出 {path}", 5000)

    def _save_screenshot(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存界面截图", "lingxi-x1.png", "PNG 图片 (*.png)")
        if path:
            self.grab().save(path, "PNG")
            self.statusBar().showMessage(f"已保存 {path}", 5000)

    def closeEvent(self, event) -> None:
        if self.serial_worker:
            self.serial_worker.stop()
        save_settings(
            self._settings_path,
            {"baud_rate": int(self.baud_combo.currentText()), "last_port": self.port_combo.currentText(), "trigger_mode": self.trigger_mode_combo.currentText(), "trigger_edge": self.trigger_edge_combo.currentText(), "trigger_level": self.trigger_level_spin.value()},
        )
        super().closeEvent(event)
