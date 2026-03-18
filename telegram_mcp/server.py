"""
Telegram MCP server for Claude Code.

Exposes three tools:
  notify      — send a one-way Telegram message (fire and forget)
  ask         — send a message and wait for a reply
  get_status  — check bot pool status for the current project

Run:
  uv run python server.py
"""

from __future__ import annotations

import json
import os
from typing import Optional

from mcp.server.fastmcp import FastMCP

import bot_client
import config as global_config
import registry

mcp = FastMCP("telegram", json_response=True)


def _resolve() -> tuple[dict, dict, None] | tuple[None, None, str]:
    """Returns (bot, cfg, None) or (None, None, error_message)."""
    bot, err = registry.resolve_bot_or_error()
    if err:
        return None, None, err

    try:
        cfg = global_config.load()
    except FileNotFoundError:
        cfg = {}

    return bot, cfg, None


@mcp.tool()
def notify(message: str) -> str:
    """
    Send a one-way Telegram notification via the active bot for this project.
    Does not wait for a reply.
    Returns JSON: {"sent": bool, "message_id": int|null, "error": str|null}
    """
    bot, cfg, err = _resolve()
    if err:
        return json.dumps({"sent": False, "message_id": None, "error": err})

    result = bot_client.notify(bot, message)
    if result.get("sent"):
        registry.touch_bot(bot["id"])
    return json.dumps(result)


@mcp.tool()
def ask(
    message: str,
    timeout_seconds: Optional[int] = None,
    options: Optional[list[str]] = None,
) -> str:
    """
    Send a Telegram message via the active bot and wait for a reply.

    - timeout_seconds: how long to wait (defaults to wait_seconds from config.json)
    - options: optional list of choices appended to the message as a numbered list

    Returns JSON:
      {"reply": "...", "timed_out": false, "stopped": false}   — user replied
      {"reply": null, "timed_out": true,  "stopped": false}    — timeout
      {"reply": null, "timed_out": false, "stopped": true}     — stop word received
      {"reply": null, "timed_out": false, "stopped": false, "error": "..."}  — error
    """
    bot, cfg, err = _resolve()
    if err:
        return json.dumps({"reply": None, "timed_out": False, "stopped": False, "error": err})

    result = bot_client.ask(bot, message, cfg, timeout_seconds=timeout_seconds, options=options)
    if result.get("reply") is not None:
        registry.touch_bot(bot["id"])
    return json.dumps(result)


@mcp.tool()
def get_status() -> str:
    """
    Return Telegram bot pool status for the current project.
    Returns JSON: {"enabled": bool, "bot_name": str|null, "chat_id": int|null, "configured": bool, "project": str}
    """
    cwd = os.getcwd()
    bot = registry.resolve_bot(cwd)
    bots = registry.list_bots()

    if bot is None:
        return json.dumps({
            "enabled": False,
            "bot_name": None,
            "chat_id": None,
            "configured": False,
            "project": cwd,
            "total_bots": len(bots),
        })

    return json.dumps({
        "enabled": bot.get("enabled", False),
        "bot_name": bot.get("name"),
        "chat_id": bot.get("chat_id"),
        "configured": bool(bot.get("chat_id")),
        "project": cwd,
        "assigned_project": bot.get("assigned_project"),
        "total_bots": len(bots),
    })


if __name__ == "__main__":
    mcp.run(transport="stdio")
