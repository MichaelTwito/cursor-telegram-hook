"""
Bot registry — load/save bots.json and resolve the active bot for the current CWD.

Schema:
{
  "bots": [
    {
      "id": "<uuid>",
      "name": "My Bot",
      "token": "123:ABC...",
      "chat_id": 929071872,       // null until user sends /start
      "assigned_project": "/abs/path/to/project",  // null = unassigned (fallback)
      "enabled": true,
      "last_used": "2026-03-14T12:00:00Z"   // ISO, or null
    }
  ]
}
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PLUGIN_DIR = Path(__file__).parent.parent
BOTS_PATH = PLUGIN_DIR / "bots.json"


# ── persistence ──────────────────────────────────────────────────────────────

def load_registry() -> dict[str, Any]:
    if not BOTS_PATH.exists():
        return {"bots": []}
    with open(BOTS_PATH) as f:
        data = json.load(f)
    data.setdefault("bots", [])
    return data


def save_registry(data: dict[str, Any]) -> None:
    with open(BOTS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def list_bots() -> list[dict[str, Any]]:
    return load_registry()["bots"]


def get_bot(bot_id: str) -> dict[str, Any] | None:
    for bot in list_bots():
        if bot["id"] == bot_id:
            return bot
    return None


def add_bot(token: str, name: str, chat_id: int | None = None) -> dict[str, Any]:
    data = load_registry()
    bot: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "name": name,
        "token": token,
        "chat_id": chat_id,
        "assigned_project": None,
        "enabled": True,
        "last_used": None,
    }
    data["bots"].append(bot)
    save_registry(data)
    return bot


def update_bot(bot_id: str, **fields) -> dict[str, Any] | None:
    data = load_registry()
    for bot in data["bots"]:
        if bot["id"] == bot_id:
            bot.update(fields)
            save_registry(data)
            return bot
    return None


def delete_bot(bot_id: str) -> bool:
    data = load_registry()
    before = len(data["bots"])
    data["bots"] = [b for b in data["bots"] if b["id"] != bot_id]
    if len(data["bots"]) < before:
        save_registry(data)
        return True
    return False


def touch_bot(bot_id: str) -> None:
    """Update last_used timestamp."""
    update_bot(bot_id, last_used=datetime.now(timezone.utc).isoformat())


# ── resolution ────────────────────────────────────────────────────────────────

def resolve_bot(cwd: str | None = None) -> dict[str, Any] | None:
    """
    Find the best bot for the given working directory.

    1. Bot with assigned_project == cwd (exact match)
    2. First enabled bot (fallback)
    """
    cwd = cwd or os.getcwd()
    bots = list_bots()

    # Exact project match
    for bot in bots:
        if bot.get("enabled") and bot.get("assigned_project") == cwd:
            return bot

    # Fallback: first enabled bot
    for bot in bots:
        if bot.get("enabled"):
            return bot

    return None


def resolve_bot_or_error(cwd: str | None = None) -> tuple[dict[str, Any], None] | tuple[None, str]:
    bot = resolve_bot(cwd)
    if bot is None:
        return None, "No enabled bot found. Add a bot at http://localhost:8080 or run install.py."
    if not bot.get("chat_id"):
        return None, f"Bot '{bot['name']}' has no chat_id. Send /start to @{bot['name']} on Telegram first."
    return bot, None
