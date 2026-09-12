from __future__ import annotations

import json
from pathlib import Path


DEFAULTS = {
    "baud_rate": 256000,
    "theme": "liquid_glass",
    "trigger_mode": "Auto",
    "trigger_edge": "Rising",
    "trigger_level": 0.0,
    "last_port": "",
}


def load_settings(path: str | Path) -> dict:
    try:
        loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        return {**DEFAULTS, **loaded} if isinstance(loaded, dict) else DEFAULTS.copy()
    except (OSError, ValueError, TypeError):
        return DEFAULTS.copy()


def save_settings(path: str | Path, values: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({**DEFAULTS, **values}, ensure_ascii=False, indent=2), encoding="utf-8")
