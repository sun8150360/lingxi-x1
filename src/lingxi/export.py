from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


def export_csv(path: str | Path, time_s: np.ndarray, voltage: np.ndarray, metadata: dict[str, object]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        for key, value in metadata.items():
            handle.write(f"# {key}={value}\n")
        writer = csv.writer(handle)
        writer.writerow(["time_s", "voltage_v"])
        writer.writerows(zip(np.asarray(time_s), np.asarray(voltage), strict=True))


def read_csv(path: str | Path) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    metadata: dict[str, str] = {}
    rows: list[tuple[float, float]] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for line in handle:
            if line.startswith("# "):
                key, value = line[2:].strip().split("=", 1)
                metadata[key] = value
                continue
            if line.startswith("time_s"):
                continue
            if line.strip():
                a, b = next(csv.reader([line]))
                rows.append((float(a), float(b)))
    data = np.asarray(rows, dtype=float)
    if data.size == 0:
        return np.array([]), np.array([]), metadata
    return data[:, 0], data[:, 1], metadata
