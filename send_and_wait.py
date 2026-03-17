#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["telethon"]
# ///
"""
Sends a formatted summary to Telegram and polls for a reply.

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
from datetime import datetime, timezone

from telethon.sessions import StringSession
from telethon.sync import TelegramClient


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def run(config_path: str, summary: str) -> int:
    cfg = load_config(config_path)

    api_id = int(cfg["telegram_api_id"])
    api_hash = cfg["telegram_api_hash"]
    session_string = cfg["telegram_session_string"]
    chat_id = int(cfg["telegram_chat_id"])
    prefix = cfg.get("message_prefix", "\U0001f916 Cursor:")
    stop_words = [w.lower() for w in cfg.get("stop_words", [])]
    wait_seconds = cfg.get("wait_seconds", 120)
    poll_interval = cfg.get("poll_interval", 10)

    message = (
        "\U0001f916 **Cursor Update**\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"{summary}\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\U0001f4ac Reply here to send instructions"
    )

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()

    try:
        if not client.is_user_authorized():
            print("ERROR: Session not authorized", file=sys.stderr)
            return 1

        client.send_message(chat_id, message)
        send_time = datetime.now(timezone.utc)
        deadline = time.monotonic() + wait_seconds

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
                if msg.text.startswith(prefix) or msg.text.startswith("\U0001f916"):
                    continue

                text = msg.text.strip()
                if text.lower() in stop_words:
                    print("STOP")
                    return 2

                print(text)
                return 0
    finally:
        client.disconnect()

    return 1


def main():
    parser = argparse.ArgumentParser(description="Send Telegram summary and wait for reply")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--summary", required=True, help="Summary text to send")
    args = parser.parse_args()
    sys.exit(run(args.config, args.summary))


if __name__ == "__main__":
    main()
