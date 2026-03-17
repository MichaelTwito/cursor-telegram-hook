---
name: telegram-hook
description: >-
  Control the Telegram hook plugin for remote Cursor control via Telegram.
  Use when the user says telegram on, telegram off, enable telegram, disable
  telegram, telegram status, telegram hebrew, telegram english,
  /telegram_on, /telegram_off, /telegram_status, /telegram_lang_he,
  /telegram_lang_en, or any variation of activating/deactivating the
  Telegram notification hook.
---

# Telegram Hook Control

Config: `cursor-telegram-hook/config.json` (relative to project root).

## Commands

**Enable** (`telegram on`, `/telegram_on`): set `"enabled": true` in config. Confirm: "Telegram hook is ON."

**Disable** (`telegram off`, `/telegram_off`): set `"enabled": false` in config. Confirm: "Telegram hook is OFF."

**Status** (`telegram status`, `/telegram_status`): read config, report enabled/language/wait_seconds/poll_interval/max_loops.

**Hebrew** (`telegram hebrew`, `/telegram_lang_he`): set `"language": "he"`. Confirm.

**English** (`telegram english`, `/telegram_lang_en`): set `"language": "en"`. Confirm.
