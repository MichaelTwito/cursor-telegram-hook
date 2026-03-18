"""
Telethon wrapper for the Telegram MCP server.

Two public functions:
  notify(cfg, message)           -> {"sent": bool, "message_id": int|None, "error": str|None}
  ask(cfg, message, timeout, options) -> {"reply": str|None, "timed_out": bool, "stopped": bool}
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from telethon.sessions import StringSession
from telethon.sync import TelegramClient


def _make_client(cfg: dict[str, Any]) -> TelegramClient:
    return TelegramClient(
        StringSession(cfg["session_string"]),
        int(cfg["api_id"]),
        cfg["api_hash"],
    )


def _own_message(text: str, cfg: dict[str, Any]) -> bool:
    prefix = cfg.get("message_prefix", "\U0001f916 Cursor:")
    return text.startswith(prefix) or text.startswith("\U0001f916")


def notify(cfg: dict[str, Any], message: str) -> dict[str, Any]:
    """Send a one-way message. Returns {sent, message_id, error}."""
    client = _make_client(cfg)
    client.connect()
    try:
        if not client.is_user_authorized():
            return {"sent": False, "message_id": None, "error": "Session not authorized"}
        sent = client.send_message(int(cfg["chat_id"]), message)
        return {"sent": True, "message_id": sent.id, "error": None}
    except Exception as exc:
        return {"sent": False, "message_id": None, "error": str(exc)}
    finally:
        client.disconnect()


def ask(
    cfg: dict[str, Any],
    message: str,
    timeout_seconds: int | None = None,
    options: list[str] | None = None,
) -> dict[str, Any]:
    """
    Send a message and wait for a reply.

    Returns:
      {"reply": str, "timed_out": False, "stopped": False}   — user replied
      {"reply": None, "timed_out": True,  "stopped": False}  — timeout
      {"reply": None, "timed_out": False, "stopped": True}   — stop word
      {"reply": None, "timed_out": False, "stopped": False, "error": str} — error
    """
    if timeout_seconds is None:
        timeout_seconds = cfg.get("wait_seconds", 120)
    poll_interval = cfg.get("poll_interval", 10)
    stop_words = {w.lower() for w in cfg.get("stop_words", [])}
    chat_id = int(cfg["chat_id"])

    # Append options list to message
    if options:
        numbered = "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(options))
        message = f"{message}\n\n{numbered}"

    client = _make_client(cfg)
    client.connect()
    try:
        if not client.is_user_authorized():
            return {"reply": None, "timed_out": False, "stopped": False, "error": "Session not authorized"}

        client.send_message(chat_id, message)
        send_time = datetime.now(timezone.utc)
        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval, remaining))

            for msg in client.get_messages(chat_id, limit=5):
                if msg.date is None or msg.text is None:
                    continue
                msg_utc = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
                if msg_utc <= send_time:
                    continue
                if _own_message(msg.text, cfg):
                    continue

                text = msg.text.strip()
                if text.lower() in stop_words:
                    return {"reply": None, "timed_out": False, "stopped": True}

                return {"reply": text, "timed_out": False, "stopped": False}

    except Exception as exc:
        return {"reply": None, "timed_out": False, "stopped": False, "error": str(exc)}
    finally:
        client.disconnect()

    return {"reply": None, "timed_out": True, "stopped": False}
