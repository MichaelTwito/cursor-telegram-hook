"""
Telegram Bot API wrapper.

Two public functions:
  notify(bot, message)  -> {"sent": bool, "message_id": int|None, "error": str|None}
  ask(bot, message, config, timeout_seconds, options)
                        -> {"reply": str|None, "timed_out": bool, "stopped": bool, "error"?: str}

Uses the Telegram Bot API directly via urllib (no extra library).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

BASE = "https://api.telegram.org/bot{token}/{method}"


# ── low-level HTTP ─────────────────────────────────────────────────────────────

def _call(token: str, method: str, **params) -> dict[str, Any]:
    url = BASE.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        return {"ok": False, "description": body}
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


def send_message(token: str, chat_id: int, text: str, parse_mode: str = "Markdown") -> dict[str, Any]:
    return _call(token, "sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)


def get_updates(token: str, offset: int = 0, timeout: int = 10) -> dict[str, Any]:
    return _call(token, "getUpdates", offset=offset, timeout=timeout)


def get_me(token: str) -> dict[str, Any]:
    return _call(token, "getMe")


# ── public functions ──────────────────────────────────────────────────────────

def notify(bot: dict[str, Any], message: str) -> dict[str, Any]:
    """Send a one-way message. Returns {sent, message_id, error}."""
    result = send_message(bot["token"], int(bot["chat_id"]), message)
    if result.get("ok"):
        return {"sent": True, "message_id": result["result"]["message_id"], "error": None}
    return {"sent": False, "message_id": None, "error": result.get("description", "Unknown error")}


def ask(
    bot: dict[str, Any],
    message: str,
    config: dict[str, Any],
    timeout_seconds: int | None = None,
    options: list[str] | None = None,
) -> dict[str, Any]:
    """
    Send a message and poll for a reply.

    Returns:
      {"reply": str, "timed_out": False, "stopped": False}
      {"reply": None, "timed_out": True, "stopped": False}
      {"reply": None, "timed_out": False, "stopped": True}
      {"reply": None, ..., "error": str}
    """
    if timeout_seconds is None:
        timeout_seconds = config.get("wait_seconds", 120)
    poll_interval = config.get("poll_interval", 10)
    stop_words = {w.lower() for w in config.get("stop_words", [])}
    chat_id = int(bot["chat_id"])
    token = bot["token"]

    # Append options list
    if options:
        numbered = "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(options))
        message = f"{message}\n\n{numbered}"

    result = send_message(token, chat_id, message)
    if not result.get("ok"):
        return {"reply": None, "timed_out": False, "stopped": False,
                "error": result.get("description", "Failed to send message")}

    send_time = datetime.now(timezone.utc)
    deadline = time.monotonic() + timeout_seconds

    # Start update offset just ahead of current position to skip old messages
    offset_result = get_updates(token, timeout=0)
    offset = 0
    if offset_result.get("ok") and offset_result["result"]:
        offset = offset_result["result"][-1]["update_id"] + 1

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        long_poll_timeout = min(poll_interval, int(remaining))
        updates_result = get_updates(token, offset=offset, timeout=long_poll_timeout)

        if not updates_result.get("ok"):
            time.sleep(2)
            continue

        for update in updates_result.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message") or update.get("channel_post")
            if not msg:
                continue
            if msg.get("chat", {}).get("id") != chat_id:
                continue

            # Parse message date
            msg_ts = msg.get("date", 0)
            msg_dt = datetime.fromtimestamp(msg_ts, tz=timezone.utc)
            if msg_dt <= send_time:
                continue

            text = (msg.get("text") or "").strip()
            if not text:
                continue

            if text.lower() in stop_words:
                return {"reply": None, "timed_out": False, "stopped": True}

            return {"reply": text, "timed_out": False, "stopped": False}

    return {"reply": None, "timed_out": True, "stopped": False}
