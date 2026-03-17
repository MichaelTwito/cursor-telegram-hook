#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Claude Code Stop Hook for Telegram notification.

Claude Code calls this script via stdin when it finishes a response.
Stdin payload (JSON):
  {
    "session_id": "...",
    "stop_hook_active": false,
    "transcript_path": "/path/to/transcript.jsonl"
  }

Exit behavior:
  - Prints {"decision": "block", "reason": "<reply>"} to force Claude to act on reply
  - Exits 0 silently to let Claude stop normally
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent
CONFIG_PATH = PLUGIN_DIR / "config.json"
SEND_SCRIPT = PLUGIN_DIR / "send_and_wait.py"

MAX_SUMMARY_CHARS = 600


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def extract_summary(transcript_path: str) -> str:
    """Extract last assistant text from the transcript JSONL."""
    path = Path(transcript_path)
    if not path.exists():
        # Fallback: find most recently modified JSONL in the same dir
        candidates = sorted(path.parent.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return "Completed a response."
        path = candidates[0]

    last_text = ""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") != "assistant":
                    continue
                msg = event.get("message", {})
                for block in msg.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        last_text = block["text"]
                    elif isinstance(block, str):
                        last_text = block
    except Exception:
        return "Completed a response."

    if not last_text:
        return "Completed a response."

    # Trim to a reasonable summary length
    if len(last_text) > MAX_SUMMARY_CHARS:
        last_text = last_text[:MAX_SUMMARY_CHARS].rsplit(" ", 1)[0] + "…"
    return last_text


def main():
    # Read Stop hook payload from stdin
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    # If already in a hook-forced continuation, don't loop infinitely
    if payload.get("stop_hook_active"):
        sys.exit(0)

    # Check config
    try:
        cfg = load_config()
    except Exception:
        sys.exit(0)

    if not cfg.get("enabled"):
        sys.exit(0)

    transcript_path = payload.get("transcript_path", "")
    summary = extract_summary(transcript_path)

    # Run send_and_wait.py
    try:
        result = subprocess.run(
            ["uv", "run", str(SEND_SCRIPT), "--config", str(CONFIG_PATH), "--summary", summary],
            capture_output=True,
            text=True,
            timeout=cfg.get("wait_seconds", 120) + 30,
        )
    except Exception:
        sys.exit(0)

    if result.returncode == 0:
        reply = result.stdout.strip()
        if reply:
            # Block stop: inject Telegram reply as Claude's next instruction
            print(json.dumps({"decision": "block", "reason": reply}))
            sys.exit(0)

    # Exit 1 (timeout) or 2 (stop word) — let Claude stop
    sys.exit(0)


if __name__ == "__main__":
    main()
