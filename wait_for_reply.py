#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["telethon"]
# ///
"""
Polls Telegram Saved Messages for a reply newer than a given timestamp.

Exit codes:
  0 — reply found (text printed to stdout)
  1 — timeout, no reply
  2 — stop word received (prints "STOP" to stdout)
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from telethon.sessions import StringSession
from telethon.sync import TelegramClient


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return json.load(f)


def poll(config_path: str, after_ts: float) -> int:
    cfg = load_config(config_path)

    api_id = int(cfg["telegram_api_id"])
    api_hash = cfg["telegram_api_hash"]
    session_string = cfg["telegram_session_string"]
    chat_id = int(cfg["telegram_chat_id"])
    prefix = cfg.get("message_prefix", "Cursor:")
    stop_words = [w.lower() for w in cfg.get("stop_words", [])]
    wait_seconds = cfg.get("wait_seconds", 120)
    poll_interval = cfg.get("poll_interval", 10)

    after_dt = datetime.fromtimestamp(after_ts, tz=timezone.utc)
    deadline = time.monotonic() + wait_seconds

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()

    try:
        if not client.is_user_authorized():
            print("ERROR: Session not authorized. Re-run session_string_generator.py", file=sys.stderr)
            return 1

        while time.monotonic() < deadline:
            messages = client.get_messages(chat_id, limit=5)
            for msg in messages:
                if msg.date is None or msg.text is None:
                    continue
                msg_utc = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
                if msg_utc <= after_dt:
                    continue
                if msg.text.startswith(prefix) or msg.text.startswith("🤖"):
                    continue

                text = msg.text.strip()
                if text.lower() in stop_words:
                    print("STOP")
                    return 2

                print(text)
                return 0

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval, remaining))
    finally:
        client.disconnect()

    return 1


def main():
    parser = argparse.ArgumentParser(description="Poll Telegram for a reply")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--after-timestamp", required=True, type=float, help="UNIX timestamp; only messages after this are considered")
    args = parser.parse_args()

    sys.exit(poll(args.config, args.after_timestamp))


if __name__ == "__main__":
    main()
