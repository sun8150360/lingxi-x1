from __future__ import annotations

import numpy as np

from .protocol import SampleFrame


class SignalSimulator:
    def __init__(self, sample_rate: int = 100_000, sample_count: int = 4096, adc_bits: int = 12, vref_mv: int = 3300) -> None:
        self.sample_rate = sample_rate
        self.sample_count = sample_count
        self.adc_bits = adc_bits
        self.vref_mv = vref_mv
        self.sequence = 0
        self.phase = 0.0

    def frame(
        self,
        waveform: str = "sine",
        frequency: float = 1000.0,
        amplitude: float = 1.0,
        offset: float = 0.0,
        noise: float = 0.003,
        third_harmonic: float = 0.0,
        gain_code: int = 0,
        coupling: str = "DC",
    ) -> SampleFrame:
        t = np.arange(self.sample_count) / self.sample_rate
        phase = 2.0 * np.pi * frequency * t + self.phase
        kind = waveform.lower()
        if kind == "square":
            volts = amplitude * np.where(np.sin(phase) >= 0, 1.0, -1.0)
        elif kind == "triangle":
            volts = amplitude * (2.0 / np.pi) * np.arcsin(np.sin(phase))
        elif kind == "distorted":
            volts = amplitude * (np.sin(phase) + third_harmonic * np.sin(3 * phase))
        else:
            volts = amplitude * np.sin(phase)
        if noise:
            volts += np.random.default_rng(self.sequence).normal(0.0, noise, len(volts))
        if coupling.upper() == "DC":
            volts += offset
        zero = 1 << (self.adc_bits - 1)
        max_code = (1 << self.adc_bits) - 1
        gain_code = max(0, min(int(gain_code), 3))
        input_full_scale = 5.0 / (1, 5, 20, 100)[gain_code]
        samples = np.clip(np.rint(zero + volts / input_full_scale * (zero - 1)), 0, max_code).astype(np.uint16)
        result = SampleFrame(
            sequence=self.sequence,
            sample_rate=self.sample_rate,
            samples=samples,
            adc_bits=self.adc_bits,
            vref_mv=self.vref_mv,
            zero_code=zero,
            gain_code=gain_code,
            coupling=coupling.upper(),
        )
        self.sequence = (self.sequence + 1) & 0xFFFF
        self.phase = float((self.phase + 2 * np.pi * frequency * self.sample_count / self.sample_rate) % (2 * np.pi))
        return result
