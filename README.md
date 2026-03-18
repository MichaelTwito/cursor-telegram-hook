# Cursor / Claude Code Telegram Hook

Control Cursor or Claude Code from your phone via Telegram. After each AI response, a summary is sent to your Telegram. Reply within the timeout to send follow-up instructions — no need to be at your computer.

Uses **Telegram bots** (created via @BotFather) — no user account or session string required.

## Quick Start

### 1. Run the setup wizard

```bash
cd cursor-telegram-hook
python setup.py
```

### 2. Launch the dashboard

```bash
cd cursor-telegram-hook/dashboard
pip install fastapi uvicorn jinja2
python run.py
```

Open **http://localhost:8080** — add bots, assign them to projects, and test them.

### 3. Install hooks

```bash
# Claude Code stop hook (fires automatically after every response — 0 token cost)
python install_claude_code.py install

# Telegram MCP tools (notify, ask, get_status — call mid-task from Claude Code)
python telegram_mcp/install.py install
```

Restart Claude Code to activate.

---

## Dashboard

The local web dashboard at `http://localhost:8080` lets you:

- **Add bots** — paste a token from @BotFather; the dashboard verifies it automatically
- **Detect Chat ID** — send `/start` to your bot on Telegram, then click Detect
- **Assign to project** — one bot per project directory; unassigned bots are the global fallback
- **Test** — send a test message with one click
- **Enable/disable** individual bots
- **Global settings** — wait timeout, poll interval, language, stop words

---

## How bots are selected

When a hook or MCP tool fires, the active bot is resolved:

1. Bot with `assigned_project` matching the current working directory
2. First enabled bot (global fallback)
3. Error if no enabled bot exists

---

## Claude Code — Stop Hook

The stop hook fires automatically after every Claude Code response with **zero token cost**. It extracts the last assistant message from the session transcript and sends it to your Telegram.

```bash
# Install
python install_claude_code.py install

# Check
python install_claude_code.py status

# Remove
python install_claude_code.py uninstall
```

---

## Telegram MCP Tools

Three tools available to Claude Code mid-task:

### `notify(message)`
Fire-and-forget notification.
```
Claude: Build complete!
  → notify("Build finished: 0 errors, 2 warnings.")
```

### `ask(message, timeout_seconds?, options?)`
Send a message and wait for a reply. Useful for confirmation before destructive operations.
```
Claude: About to drop the users table.
  → ask("Delete 3000 records? Reply YES to confirm.", options=["yes", "no"])
User replies: "yes"
Claude: Confirmed. Proceeding...
```

### `get_status()`
Check which bot is active for the current project.

---

## Configuration

Edit `config.json` for global settings:

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Master toggle |
| `wait_seconds` | `120` | Max wait for reply |
| `poll_interval` | `10` | Check every N seconds |
| `max_loops` | `3` | Max send-wait cycles (Cursor rule) |
| `language` | `"en"` | Summary language: `en` or `he` |
| `stop_words` | `["stop","exit",…]` | End the loop |

Bot credentials are in `bots.json` (managed by the dashboard — do not edit manually).

---

## Architecture

```
cursor-telegram-hook/
  bots.json                  # bot pool registry
  config.json                # global settings
  send_and_wait.py           # used by claude-hook.py (stop hook)
  claude-hook.py             # Claude Code stop hook (fires after every response)
  install_claude_code.py     # installs stop hook into ~/.claude/settings.json
  setup.py                   # Cursor setup wizard
  telegram_mcp/
    server.py                # MCP server (notify, ask, get_status)
    bot_client.py            # Telegram Bot API wrapper
    registry.py              # bot pool loader + resolver
    config.py                # global config loader
    install.py               # installs MCP server into ~/.claude/settings.json
    pyproject.toml
  dashboard/
    app.py                   # FastAPI dashboard + REST API
    templates/index.html     # single-page UI
    run.py                   # uvicorn entry point
```

| Component | Token cost | Trigger |
|---|---|---|
| Stop hook (`claude-hook.py`) | 0 | Automatic after every response |
| MCP tools (`server.py`) | ~50/call | Claude calls explicitly |
| Cursor rule | ~60 always-on | Agent reads rule |

---

## Troubleshooting

**Bot not receiving messages**: Make sure you sent `/start` to the bot in Telegram, then click "Detect Chat ID" in the dashboard.

**"No enabled bot found"**: Add a bot in the dashboard and make sure it's enabled.

**Dashboard not starting**: `pip install fastapi uvicorn jinja2` and re-run `python run.py`.

**Claude Code hook not firing**: Run `python install_claude_code.py status` to verify installation. Restart Claude Code after installing.
