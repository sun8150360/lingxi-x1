# Lingxi X1 Upper Computer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows oscilloscope application with an Apple-inspired liquid-glass interface, simulator, serial protocol, measurements, triggering, FFT/THD, and export.

**Architecture:** Keep protocol parsing and signal calculations independent from Qt. A serial worker or simulator produces immutable frames; the UI consumes the newest frame at a capped refresh rate.

**Tech Stack:** Python 3.12, PySide6, pyqtgraph, NumPy, pyserial, pytest, PyInstaller.

---

### Task 1: Core protocol and frame model

**Files:** `src/lingxi/protocol.py`, `tests/test_protocol.py`

- [ ] Write tests that encode and decode a binary frame, reject a bad CRC, recover after noise, and parse a legacy text frame.
- [ ] Run `python -m pytest tests/test_protocol.py -q` and verify failure because `lingxi.protocol` does not exist.
- [ ] Implement `SampleFrame`, CRC-16/MODBUS, `encode_frame`, `BinaryFrameParser`, and `LegacyFrameParser`.
- [ ] Run the protocol tests and verify they pass.

### Task 2: Signal processing

**Files:** `src/lingxi/signal_processing.py`, `tests/test_signal_processing.py`

- [ ] Write tests for sine frequency/Vpp/RMS, square-wave duty cycle, rising/falling trigger alignment, and 10% third-harmonic THD.
- [ ] Run the signal tests and verify failure because the functions do not exist.
- [ ] Implement voltage conversion, measurements, trigger alignment, Hann-window FFT, harmonic extraction, and THD.
- [ ] Run the signal tests and verify they pass.

### Task 3: Simulator and transport

**Files:** `src/lingxi/simulator.py`, `src/lingxi/serial_worker.py`, `tests/test_simulator.py`

- [ ] Write tests that verify simulator length, sample rate, amplitude, and monotonic sequence numbers.
- [ ] Run the simulator tests and verify failure.
- [ ] Implement sine/square/triangle/distorted-sine generation and a Qt serial worker with reconnect-safe state.
- [ ] Run the simulator tests and verify they pass.

### Task 4: Liquid-glass desktop interface

**Files:** `src/lingxi/main.py`, `src/lingxi/main_window.py`, `src/lingxi/widgets.py`, `src/lingxi/theme.py`

- [ ] Write a smoke test that constructs and closes the main window in offscreen mode.
- [ ] Run the smoke test and verify failure because the window does not exist.
- [ ] Implement the translucent gradient background, glass cards, toolbar, time/spectrum plots, controls, measurement cards, and status bar.
- [ ] Connect simulator and live serial modes with a 30 FPS display timer.
- [ ] Run the smoke test and verify it passes.

### Task 5: Export, settings, and packaging

**Files:** `src/lingxi/export.py`, `src/lingxi/settings.py`, `lingxi-x1.spec`, `requirements.txt`, `README.md`

- [ ] Write tests for CSV round-trip metadata and corrupted-settings fallback.
- [ ] Run the tests and verify failure.
- [ ] Implement CSV/PNG export, JSON settings, entry point, documentation, and PyInstaller configuration.
- [ ] Run the focused tests and verify they pass.

### Task 6: Final verification and delivery

**Files:** all files above; deliver to `outputs/lingxi-x1-upper-computer`.

- [ ] Run the full test suite once.
- [ ] Launch the application in simulator mode and capture a screenshot.
- [ ] Build the Windows EXE and launch it in simulator mode.
- [ ] Copy source, EXE, README, protocol document, and screenshot to the output folder.
