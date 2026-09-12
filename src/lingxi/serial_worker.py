from __future__ import annotations

import time

from PySide6.QtCore import QThread, Signal
import serial
from serial.tools import list_ports

from .protocol import BinaryFrameParser, LegacyFrameParser


def available_ports() -> list[str]:
    return [port.device for port in list_ports.comports()]


class SerialWorker(QThread):
    frame_received = Signal(object)
    connection_changed = Signal(bool, str)
    counters_changed = Signal(int, int)

    def __init__(self, port: str, baud_rate: int = 256000, parent=None) -> None:
        super().__init__(parent)
        self.port = port
        self.baud_rate = baud_rate
        self._running = True
        self._serial: serial.Serial | None = None
        self.binary = BinaryFrameParser()
        self.legacy = LegacyFrameParser()

    def run(self) -> None:
        try:
            self._serial = serial.Serial(self.port, self.baud_rate, timeout=0.1)
            self.connection_changed.emit(True, f"已连接 {self.port}")
            while self._running:
                data = self._serial.read(max(1, self._serial.in_waiting))
                if not data:
                    time.sleep(0.005)
                    continue
                frames = self.binary.feed(data)
                if not frames:
                    frames = self.legacy.feed(data)
                for frame in frames:
                    self.frame_received.emit(frame)
                self.counters_changed.emit(self.binary.crc_errors, self.binary.format_errors + self.legacy.format_errors)
        except serial.SerialException as exc:
            self.connection_changed.emit(False, f"串口错误：{exc}")
        finally:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self.connection_changed.emit(False, "未连接")

    def send_command(self, command: str) -> None:
        if self._serial and self._serial.is_open:
            try:
                self._serial.write((command.strip() + "\n").encode("ascii"))
            except serial.SerialException:
                self._running = False

    def stop(self) -> None:
        self._running = False
        self.wait(1000)
