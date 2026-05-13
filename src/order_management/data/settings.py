"""Simple JSON-based settings persistence."""

from __future__ import annotations

import json
from typing import Any

from order_management.data.db import APP_DIR

_SETTINGS_PATH = APP_DIR / "settings.json"


def _load() -> dict[str, Any]:
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def get_setting(key: str, default: Any = None) -> Any:
    return _load().get(key, default)


def set_setting(key: str, value: Any) -> None:
    data = _load()
    data[key] = value
    APP_DIR.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
