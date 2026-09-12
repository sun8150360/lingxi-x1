from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Measurements:
    minimum: float
    maximum: float
    vpp: float
    mean: float
    rms: float
    rms_ac: float
    frequency_hz: float
    period_s: float
    duty_percent: float


@dataclass(frozen=True)
class SpectrumResult:
    frequencies: np.ndarray
    amplitudes: np.ndarray
    fundamental_hz: float
    harmonics_percent: dict[int, float]
    thd_percent: float


def adc_to_voltage(samples: np.ndarray, adc_bits: int, vref_mv: int, zero_code: int, input_scale: float = 1.0) -> np.ndarray:
    volts_per_code = (vref_mv / 1000.0) / ((1 << adc_bits) - 1)
    return (np.asarray(samples, dtype=float) - zero_code) * volts_per_code * input_scale


def _crossings(signal: np.ndarray, threshold: float, rising: bool = True) -> np.ndarray:
    if rising:
        return np.flatnonzero((signal[:-1] < threshold) & (signal[1:] >= threshold)) + 1
    return np.flatnonzero((signal[:-1] > threshold) & (signal[1:] <= threshold)) + 1


def measure_waveform(voltage: np.ndarray, sample_rate: float) -> Measurements:
    y = np.asarray(voltage, dtype=float)
    if len(y) < 3 or sample_rate <= 0:
        raise ValueError("at least three samples and a positive sample rate are required")
    minimum = float(np.min(y))
    maximum = float(np.max(y))
    mean = float(np.mean(y))
    centered = y - mean
    threshold = (minimum + maximum) / 2.0
    crossings = _crossings(y, threshold, True)
    if len(crossings) >= 2:
        period_samples = float(np.mean(np.diff(crossings)))
        frequency = float(sample_rate / period_samples)
        period = 1.0 / frequency
    else:
        frequency = 0.0
        period = 0.0
    duty = float(np.mean(y >= threshold) * 100.0) if maximum > minimum else 0.0
    return Measurements(
        minimum=minimum,
        maximum=maximum,
        vpp=maximum - minimum,
        mean=mean,
        rms=float(np.sqrt(np.mean(y * y))),
        rms_ac=float(np.sqrt(np.mean(centered * centered))),
        frequency_hz=frequency,
        period_s=period,
        duty_percent=duty,
    )


def align_trigger(voltage: np.ndarray, level: float, edge: str, pretrigger: int | None = None) -> np.ndarray | None:
    y = np.asarray(voltage, dtype=float)
    if len(y) < 2:
        return None
    pre = len(y) // 5 if pretrigger is None else max(0, min(int(pretrigger), len(y) - 1))
    candidates = _crossings(y, level, edge.lower() != "falling")
    candidates = candidates[candidates >= pre]
    if not len(candidates):
        return None
    start = int(candidates[0] - pre)
    return np.concatenate((y[start:], y[:start]))


def analyze_spectrum(voltage: np.ndarray, sample_rate: float) -> SpectrumResult:
    y = np.asarray(voltage, dtype=float)
    if len(y) < 8 or sample_rate <= 0:
        raise ValueError("at least eight samples and a positive sample rate are required")
    y = y - np.mean(y)
    window = np.hanning(len(y))
    spectrum = np.fft.rfft(y * window)
    amplitudes = np.abs(spectrum) * (2.0 / np.sum(window))
    amplitudes[0] *= 0.5
    frequencies = np.fft.rfftfreq(len(y), d=1.0 / sample_rate)
    fundamental_index = int(np.argmax(amplitudes[1:]) + 1)
    fundamental_hz = float(frequencies[fundamental_index])
    fundamental_amp = float(amplitudes[fundamental_index])
    harmonics: dict[int, float] = {}
    for harmonic in range(2, 6):
        target = fundamental_hz * harmonic
        if target > frequencies[-1]:
            harmonics[harmonic] = 0.0
            continue
        index = int(np.argmin(np.abs(frequencies - target)))
        lo, hi = max(1, index - 1), min(len(amplitudes), index + 2)
        amp = float(np.max(amplitudes[lo:hi]))
        harmonics[harmonic] = 100.0 * amp / fundamental_amp if fundamental_amp else 0.0
    thd = float(np.sqrt(sum(value * value for value in harmonics.values())))
    return SpectrumResult(frequencies, amplitudes, fundamental_hz, harmonics, thd)
