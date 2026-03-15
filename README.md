# Cursor Telegram Hook

Control Cursor IDE from your phone via Telegram. After each AI response, a summary is sent to your Telegram. Reply within the timeout to send follow-up instructions — no need to be at your computer.

## Setup (one-time, ~5 minutes)

### 1. Copy the plugin

```bash
cp -r cursor-telegram-hook /path/to/your/project/
```

### 2. Run the setup wizard

```bash
cd cursor-telegram-hook
python setup.py
```

The wizard walks you through everything:

| Step | What it does |
|------|-------------|
| 1 | Checks prerequisites (`uv`, `git`, Python 3) |
| 2 | Clones [telegram-mcp](https://github.com/chigwell/telegram-mcp) if missing |
| 3 | Configures Telegram API credentials (defaults available) |
| 4 | Guides you through generating a session string |
| 5 | Asks for your Telegram user ID |
| 6 | Sets your wait timer, poll interval, language, etc. |
| 7 | Installs the MCP server in `~/.cursor/mcp.json` |
| 8 | Installs the Cursor rule and skill in your project |

### 3. Restart Cursor

Restart Cursor IDE to load the new MCP server.

### 4. Activate

In any Cursor chat, say **"telegram on"** or type `/telegram_on`.

## Usage

### In Cursor Chat

Say these in natural language or as commands:

| Trigger | Action |
|---------|--------|
| `telegram on` / `/telegram_on` | Enable the hook |
| `telegram off` / `/telegram_off` | Disable the hook |
| `telegram status` / `/telegram_status` | Show current settings |
| `telegram hebrew` / `/telegram_lang_he` | Switch summaries to Hebrew |
| `telegram english` / `/telegram_lang_en` | Switch summaries to English |

### In Terminal

```bash
python setup.py on       # Enable
python setup.py off      # Disable
python setup.py toggle   # Toggle
python setup.py status   # Show config
python setup.py help     # All commands
```

### In Telegram

- Reply to a Cursor message with any instruction
- Cursor picks it up within 10 seconds and executes it
- Reply `stop`, `exit`, `quit`, `עצור`, or `יציאה` to end the loop

## How It Works

```
You ask Cursor a question
        |
   Cursor answers
        |
   🤖 Sends formatted summary ──────> You see it on Telegram
        |
   Polls every 10s (up to 120s)
        |   (direct Telethon, no MCP overhead)
        |
   Reply arrives? ─── YES ──> Agent executes it ──> loops
        |
       NO (timeout) ──> Done
```

## Configuration

Edit `config.json`:

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Master toggle |
| `wait_seconds` | `120` | Max time to wait for a reply |
| `poll_interval` | `10` | Check for replies every N seconds |
| `max_loops` | `3` | Max send-wait-read cycles |
| `language` | `"en"` | Summary language: `"en"` or `"he"` |
| `telegram_chat_id` | — | Your Telegram numeric user ID |
| `message_prefix` | `"🤖 Cursor:"` | Identifies Cursor messages |
| `stop_words` | `["stop","exit",...]` | Reply words that end the loop |

## Prerequisites

- Python 3.10+
- `uv` ([install](https://astral.sh/uv))
- `git`
- A Telegram account

The setup wizard handles everything else (cloning telegram-mcp, installing dependencies, etc).

## Troubleshooting

**MCP server won't start**: Run `python setup.py` again to re-configure credentials. Then restart Cursor.

**"Session not authorized"**: Your session string expired. Regenerate it:
```bash
cd ~/projects/telegram-mcp
uv run session_string_generator.py
```
Then update `telegram_session_string` in `config.json` and re-run `python setup.py`.

**No Telegram messages**: Make sure `enabled` is `true` in config.json and the MCP server is running (check Cursor Settings > MCP).

**Hook not triggering in chat**: Say "telegram on" or start a new chat. The rule loads when chats start.
