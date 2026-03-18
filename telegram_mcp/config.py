"""
Config loader for cursor-telegram-hook.

Resolution order:
  1. CURSOR_TELEGRAM_HOOK_CONFIG env var
  2. ~/.cursor-telegram-hook/config.json
  3. ../config.json  (sibling to the telegram_mcp/ folder)

Supports both the original long key names (telegram_api_id, telegram_chat_id, …)
and short aliases (api_id, chat_id, …).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


_LONG_TO_SHORT = {
    "telegram_api_id": "api_id",
    "telegram_api_hash": "api_hash",
    "telegram_session_string": "session_string",
    "telegram_chat_id": "chat_id",
}


def _resolve_path() -> Path:
    env = os.environ.get("CURSOR_TELEGRAM_HOOK_CONFIG")
    if env:
        return Path(env)

    home_candidate = Path.home() / ".cursor-telegram-hook" / "config.json"
    if home_candidate.exists():
        return home_candidate

    sibling = Path(__file__).parent.parent / "config.json"
    return sibling


def load() -> dict[str, Any]:
    """Load and normalise config. Raises FileNotFoundError if no config found."""
    path = _resolve_path()
    with open(path) as f:
        raw = json.load(f)

    # Normalise: add short aliases alongside the original keys
    for long_key, short_key in _LONG_TO_SHORT.items():
        if long_key in raw and short_key not in raw:
            raw[short_key] = raw[long_key]
        elif short_key in raw and long_key not in raw:
            raw[long_key] = raw[short_key]

    return raw


def is_configured(cfg: dict[str, Any]) -> bool:
    """True if all Telegram credentials are present."""
    return all(
        cfg.get(k) not in (None, "")
        for k in ("api_id", "api_hash", "session_string", "chat_id")
    )


def config_path() -> Path:
    return _resolve_path()
