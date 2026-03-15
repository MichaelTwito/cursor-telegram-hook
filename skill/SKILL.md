---
name: telegram-hook
description: >-
  Control the Telegram hook plugin for remote Cursor control via Telegram.
  Use when the user says telegram on, telegram off, enable telegram, disable
  telegram, telegram status, telegram hebrew, telegram english, or any
  variation of activating/deactivating the Telegram notification hook.
---

# Telegram Hook Control

## Config Path

The config file is at: `cursor-telegram-hook/config.json` (relative to project root).

## Commands

When the user wants to **enable** the hook (`telegram on`, `enable telegram`, `activate telegram`):

1. Read `cursor-telegram-hook/config.json`
2. Set `"enabled"` to `true`
3. Write it back
4. Confirm: "Telegram hook is ON. I'll send summaries to Telegram after each response and wait for your reply."

When the user wants to **disable** the hook (`telegram off`, `disable telegram`, `deactivate telegram`):

1. Read `cursor-telegram-hook/config.json`
2. Set `"enabled"` to `false`
3. Write it back
4. Confirm: "Telegram hook is OFF."

When the user wants **status** (`telegram status`):

1. Read `cursor-telegram-hook/config.json`
2. Report: enabled, language, wait_seconds, poll_interval, max_loops

When the user wants to **change language** (`telegram hebrew`, `telegram english`):

1. Read `cursor-telegram-hook/config.json`
2. Set `"language"` to `"he"` or `"en"`
3. Write it back
4. Confirm the change

## Post-Response Hook

After completing any regular (non-command) response, if `"enabled"` is `true`:

1. Send a formatted summary to Telegram via `user-telegram-mcp` MCP `send_message`:

```
🤖 **Cursor Update**
━━━━━━━━━━━━━━━
<2-4 sentence summary: what was asked, what was done, the outcome>
━━━━━━━━━━━━━━━
💬 Reply here to send instructions
```

   Use `chat_id` from config. Write in the configured `language`.

2. Get timestamp: `python3 -c "import time; print(int(time.time()))"`

3. Run polling script:

```bash
uv run cursor-telegram-hook/wait_for_reply.py --config cursor-telegram-hook/config.json --after-timestamp <TIMESTAMP>
```

   Set `block_until_ms` to `(wait_seconds + 5) * 1000`.

4. Check exit code:
   - **0**: stdout = reply text. Execute as new instruction. Loop (max `max_loops` times).
   - **1**: timeout. Stop.
   - **2**: stop word. Stop.
