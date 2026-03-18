#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Sends a formatted summary to Telegram via a BotFather bot and polls for a reply.

Reads the active bot from bots.json (resolves by CWD, falls back to first enabled bot).

Usage:
  uv run send_and_wait.py --config config.json --summary "What happened"

Exit codes:
  0 — reply found (text printed to stdout)
  1 — timeout, no reply
  2 — stop word received (prints "STOP" to stdout)
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# ── Bot API helpers (no external deps) ───────────────────────────────────────

BOT_API = "https://api.telegram.org/bot{token}/{method}"


def _api(token: str, method: str, **params) -> dict:
    url = BOT_API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return {"ok": False, "description": exc.read().decode(errors="replace")}
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


# ── Registry helpers ──────────────────────────────────────────────────────────

def _load_registry(config_path: str) -> dict:
    bots_path = Path(config_path).parent / "bots.json"
    if bots_path.exists():
        with open(bots_path) as f:
            return json.load(f)
    return {"bots": []}


def _resolve_bot(registry: dict) -> dict | None:
    import os
    cwd = os.getcwd()
    for bot in registry.get("bots", []):
        if bot.get("enabled") and bot.get("assigned_project") == cwd:
            return bot
    for bot in registry.get("bots", []):
        if bot.get("enabled"):
            return bot
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def run(config_path: str, summary: str) -> int:
    with open(config_path) as f:
        cfg = json.load(f)

    registry = _load_registry(config_path)
    bot = _resolve_bot(registry)

    if bot is None:
        print("ERROR: No enabled bot found in bots.json. Add a bot via the dashboard.", file=sys.stderr)
        return 1

    if not bot.get("chat_id"):
        print(f"ERROR: Bot '{bot['name']}' has no chat_id. Send /start to it on Telegram first.", file=sys.stderr)
        return 1

    token = bot["token"]
    chat_id = int(bot["chat_id"])
    stop_words = {w.lower() for w in cfg.get("stop_words", [])}
    wait_seconds = cfg.get("wait_seconds", 120)
    poll_interval = cfg.get("poll_interval", 10)

    message = (
        "\U0001f916 **AI Update**\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"{summary}\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\U0001f4ac Reply here to send instructions"
    )

    result = _api(token, "sendMessage", chat_id=chat_id, text=message, parse_mode="Markdown")
    if not result.get("ok"):
        print(f"ERROR: Failed to send message: {result.get('description')}", file=sys.stderr)
        return 1

    send_time = datetime.now(timezone.utc)
    deadline = time.monotonic() + wait_seconds

    # Get current update offset to skip old messages
    offset = 0
    updates = _api(token, "getUpdates", timeout=0)
    if updates.get("ok") and updates["result"]:
        offset = updates["result"][-1]["update_id"] + 1

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break

        long_poll = min(poll_interval, int(remaining))
        updates = _api(token, "getUpdates", offset=offset, timeout=long_poll)

        if not updates.get("ok"):
            time.sleep(2)
            continue

        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message") or update.get("channel_post")
            if not msg:
                continue
            if msg.get("chat", {}).get("id") != chat_id:
                continue

            msg_dt = datetime.fromtimestamp(msg.get("date", 0), tz=timezone.utc)
            if msg_dt <= send_time:
                continue

            text = (msg.get("text") or "").strip()
            if not text:
                continue

            if text.lower() in stop_words:
                print("STOP")
                return 2

            print(text)
            return 0

    return 1


def main():
    parser = argparse.ArgumentParser(description="Send Telegram summary and wait for reply")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--summary", required=True, help="Summary text to send")
    args = parser.parse_args()
    sys.exit(run(args.config, args.summary))


if __name__ == "__main__":
    main()
