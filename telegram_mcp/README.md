# Telegram MCP Server

A Python MCP server that lets Claude Code send Telegram notifications and wait for replies **mid-task** — before a destructive operation, after completing a subtask, or whenever human input is needed.

Complements the existing [stop hook](../claude-hook.py) (which fires end-of-response). This server adds on-demand tools Claude can call explicitly.

## Prerequisites

You must have already run `../setup.py` from the parent `cursor-telegram-hook` directory. This server reuses the same `config.json`.

## Installation

```bash
cd cursor-telegram-hook/telegram_mcp
python install.py install
```

Then restart Claude Code (or reload MCP servers in settings).

## Tools

### `notify(message)`

Send a one-way Telegram message. Does not wait for a reply.

```
Claude: Build finished in 4m 32s.
        → calls notify("Build complete: 0 errors, 2 warnings.")
```

Returns:
```json
{"sent": true, "message_id": 12345, "error": null}
```

### `ask(message, timeout_seconds?, options?)`

Send a message and wait for a reply. Claude blocks until the user responds or the timeout is reached.

```
Claude: About to drop the users table in production.
        → calls ask(
            "Delete 3000 records from orders? Reply to confirm.",
            timeout_seconds=60,
            options=["yes", "no"]
          )
User replies on Telegram: "yes"
Claude: Confirmed. Proceeding...
```

- `timeout_seconds` defaults to `wait_seconds` from `config.json` (120s)
- `options` is optional — if provided, they are appended as a numbered list
- Reply matches a stop word (`stop`, `exit`, `quit`, `עצור`, `יציאה`) → `stopped: true`

Returns:
```json
{"reply": "yes", "timed_out": false, "stopped": false}
```

### `get_status()`

Check whether Telegram is configured and enabled.

```json
{"enabled": true, "chat_id": 123456789, "configured": true}
```

Use this before calling `notify` or `ask` to skip gracefully when not configured.

## How It Works

```
Claude calls ask() or notify()
        |
   server.py receives tool call (MCP stdio)
        |
   config.py reads config.json
        |
   telegram_client.py connects via Telethon
        |
   Sends message to your Telegram
        |
   Polls every poll_interval seconds (for ask)
        |
   Returns result to Claude
```

## Config

Reuses `cursor-telegram-hook/config.json`. Relevant fields:

| Field | Description |
|-------|-------------|
| `enabled` | Must be `true` for tools to work |
| `wait_seconds` | Default timeout for `ask` |
| `poll_interval` | How often to check for replies |
| `stop_words` | Words that trigger `stopped: true` |

## Manual Hook Management

```bash
python install.py install    # Add to ~/.claude/settings.json
python install.py status     # Check installation
python install.py uninstall  # Remove
```

## Difference from Stop Hook

| | Stop Hook (`claude-hook.py`) | MCP Server (`server.py`) |
|---|---|---|
| When | After every response | Explicitly called by Claude |
| Token cost | 0 | Tool call overhead (~50 tokens) |
| Use case | End-of-response summary | Mid-task notifications, approvals |
| Control | Automatic | Claude decides when to call |
