import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lingxi.main_window import MainWindow
from lingxi.protocol import SampleFrame
from lingxi.theme import LIQUID_GLASS_QSS
import numpy as np


def test_main_window_constructs_and_closes():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(start_simulator=False)
    assert window.windowTitle().startswith("灵析 X1")
    assert window.time_plot is not None
    assert window.spectrum_plot is not None
    window.close()
    app.processEvents()


def test_theme_uses_light_liquid_glass_palette():
    assert "#F5F5F7" in LIQUID_GLASS_QSS
    assert "#1D1D1F" in LIQUID_GLASS_QSS
    assert "#07111F" not in LIQUID_GLASS_QSS


def _frame(sequence: int) -> SampleFrame:
    phase = np.arange(512)
    samples = np.rint(2048 + 900 * np.sin(2 * np.pi * phase / 32)).astype(np.uint16)
    return SampleFrame(sequence=sequence, sample_rate=32_000, samples=samples)


def test_single_shot_waits_for_a_new_frame():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(start_simulator=False)
    window._accept_frame(_frame(4))
    window._single()
    window._tick()
    assert window.running is True
    window._accept_frame(_frame(5))
    window._tick()
    assert window.running is False
    window.close()
    app.processEvents()


def test_protocol_error_count_survives_rendering():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(start_simulator=False)
    window._protocol_counters(3, 4)
    window._render_frame(_frame(1))
    assert "协议错误 7" in window.status_errors.text()
    window.close()
    app.processEvents()


def test_source_reset_does_not_create_false_dropped_frames():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(start_simulator=False)
    window._accept_frame(_frame(40000))
    window._reset_stream_state("serial")
    window._accept_frame(_frame(0))
    assert window.dropped_frames == 0
    window._accept_frame(_frame(2))
    assert window.dropped_frames == 1
    window.close()
    app.processEvents()


def test_gain_and_coupling_controls_send_device_commands():
    class FakeWorker:
        def __init__(self):
            self.commands = []

        def send_command(self, command):
            self.commands.append(command)

        def isRunning(self):
            return True

        def stop(self):
            pass

    app = QApplication.instance() or QApplication([])
    window = MainWindow(start_simulator=False)
    worker = FakeWorker()
    window.serial_worker = worker
    window.gain_combo.setCurrentIndex(2)
    window.coupling_combo.setCurrentText("AC")
    assert "GAIN 2" in worker.commands
    assert "COUPLING AC" in worker.commands
    window.serial_worker = None
    window.close()
    app.processEvents()
