import json

import numpy as np

from lingxi.export import export_csv, read_csv
from lingxi.settings import load_settings
from lingxi.simulator import SignalSimulator


def test_simulator_produces_monotonic_frames():
    sim = SignalSimulator(sample_rate=100_000, sample_count=1000)
    a = sim.frame("sine", frequency=1000, amplitude=1.0)
    b = sim.frame("sine", frequency=1000, amplitude=1.0)
    assert len(a.samples) == 1000
    assert a.sample_rate == 100_000
    assert b.sequence == a.sequence + 1


def test_simulator_applies_gain_and_ac_coupling_metadata():
    sim = SignalSimulator(sample_rate=100_000, sample_count=1000)
    frame = sim.frame("sine", frequency=1000, amplitude=0.2, offset=0.5, noise=0, gain_code=2, coupling="AC")
    assert frame.gain_code == 2
    assert frame.coupling == "AC"
    assert abs(float(np.mean(frame.samples)) - frame.zero_code) < 2


def test_csv_round_trip(tmp_path):
    time_s = np.array([0.0, 0.001, 0.002])
    voltage = np.array([-1.0, 0.0, 1.0])
    path = tmp_path / "wave.csv"
    export_csv(path, time_s, voltage, {"sample_rate": 1000, "coupling": "DC"})
    loaded_t, loaded_v, metadata = read_csv(path)
    np.testing.assert_allclose(loaded_t, time_s)
    np.testing.assert_allclose(loaded_v, voltage)
    assert metadata["sample_rate"] == "1000"


def test_corrupt_settings_fall_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{broken", encoding="utf-8")
    settings = load_settings(path)
    assert settings["baud_rate"] == 256000
    assert settings["theme"] == "liquid_glass"
