import numpy as np

from lingxi.signal_processing import align_trigger, analyze_spectrum, measure_waveform


def test_measure_sine_frequency_vpp_and_rms():
    fs = 100_000
    t = np.arange(5000) / fs
    y = 0.4 + 1.25 * np.sin(2 * np.pi * 1000 * t)
    m = measure_waveform(y, fs)
    assert abs(m.frequency_hz - 1000) < 2
    assert abs(m.vpp - 2.5) < 0.01
    assert abs(m.rms_ac - 1.25 / np.sqrt(2)) < 0.01
    assert abs(m.mean - 0.4) < 0.01


def test_measure_square_duty_cycle():
    fs = 100_000
    phase = np.arange(5000) % 100
    y = np.where(phase < 40, 1.0, -1.0)
    m = measure_waveform(y, fs)
    assert abs(m.frequency_hz - 1000) < 2
    assert abs(m.duty_percent - 40) < 1


def test_trigger_alignment_supports_both_edges():
    y = np.tile(np.array([-1.0, -0.5, 0.3, 1.0, 0.2, -0.4]), 20)
    rising = align_trigger(y, 0.0, "rising", pretrigger=8)
    falling = align_trigger(y, 0.0, "falling", pretrigger=8)
    assert rising is not None and rising[8] >= 0 and rising[7] < 0
    assert falling is not None and falling[8] <= 0 and falling[7] > 0


def test_spectrum_finds_third_harmonic_and_thd():
    fs = 64_000
    t = np.arange(4096) / fs
    y = np.sin(2 * np.pi * 1000 * t) + 0.1 * np.sin(2 * np.pi * 3000 * t)
    s = analyze_spectrum(y, fs)
    assert abs(s.fundamental_hz - 1000) < 2
    assert abs(s.harmonics_percent[3] - 10) < 0.5
    assert abs(s.thd_percent - 10) < 0.5
