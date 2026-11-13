from __future__ import annotations

import functools
import json
from typing import Any, Final

import Utils
from CommonClient import logger

STATE_DIR: Final = "data"
STATE_FILE: Final = "gotcha_force_client.json"


def client_state_get(key: str, field: str, default: Any) -> Any:
    return _load().get(key, {}).get(field, default)


def _load() -> dict:
    try:
        with open(_state_file(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


@functools.cache
def _state_file() -> str:
    return Utils.user_path(STATE_DIR, STATE_FILE)


def client_state_set(key: str, field: str, value: Any) -> None:
    data = _load()
    data.setdefault(key, {})[field] = value
    try:
        with open(_state_file(), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError as exc:
        logger.warning(f"could not save the client state to {_state_file()}: {exc}")
