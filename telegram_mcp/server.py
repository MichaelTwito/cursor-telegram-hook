"""
Telegram MCP server for Claude Code.

Exposes three tools:
  notify      — send a one-way message (fire and forget)
  ask         — send a message and wait for a reply
  get_status  — check whether Telegram is configured and enabled

Run:
  uv run python server.py
"""

from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

import config
import telegram_client

mcp = FastMCP("telegram", json_response=True)


def _load_cfg() -> tuple[dict, None] | tuple[None, str]:
    """Returns (cfg, None) or (None, error_message)."""
    try:
        cfg = config.load()
    except FileNotFoundError:
        return None, f"config.json not found. Run cursor-telegram-hook/setup.py first."
    except Exception as exc:
        return None, f"Failed to read config: {exc}"

    if not cfg.get("enabled"):
        return None, "Telegram hook is disabled. Set enabled=true in config.json."

    if not config.is_configured(cfg):
        return None, "Telegram credentials not set. Run cursor-telegram-hook/setup.py."

    return cfg, None


@mcp.tool()
def notify(message: str) -> str:
    """
    Send a one-way Telegram notification. Does not wait for a reply.
    Returns JSON: {"sent": bool, "message_id": int|null, "error": str|null}
    """
    cfg, err = _load_cfg()
    if err:
        return json.dumps({"sent": False, "message_id": None, "error": err})

    result = telegram_client.notify(cfg, message)
    return json.dumps(result)


@mcp.tool()
def ask(
    message: str,
    timeout_seconds: Optional[int] = None,
    options: Optional[list[str]] = None,
) -> str:
    """
    Send a Telegram message and wait for a reply.

    - timeout_seconds: how long to wait (defaults to wait_seconds from config)
    - options: optional list of choices appended to the message as a numbered list

    Returns JSON:
      {"reply": "...", "timed_out": false, "stopped": false}   — user replied
      {"reply": null, "timed_out": true,  "stopped": false}    — timeout
      {"reply": null, "timed_out": false, "stopped": true}     — stop word received
      {"reply": null, "timed_out": false, "stopped": false, "error": "..."}  — error
    """
    cfg, err = _load_cfg()
    if err:
        return json.dumps({"reply": None, "timed_out": False, "stopped": False, "error": err})

    result = telegram_client.ask(cfg, message, timeout_seconds=timeout_seconds, options=options)
    return json.dumps(result)


@mcp.tool()
def get_status() -> str:
    """
    Return Telegram hook status from config.json.
    Returns JSON: {"enabled": bool, "chat_id": int|null, "configured": bool}
    """
    try:
        cfg = config.load()
    except FileNotFoundError:
        return json.dumps({"enabled": False, "chat_id": None, "configured": False})
    except Exception as exc:
        return json.dumps({"enabled": False, "chat_id": None, "configured": False, "error": str(exc)})

    return json.dumps({
        "enabled": bool(cfg.get("enabled")),
        "chat_id": cfg.get("chat_id") or cfg.get("telegram_chat_id"),
        "configured": config.is_configured(cfg),
    })


if __name__ == "__main__":
    mcp.run(transport="stdio")
