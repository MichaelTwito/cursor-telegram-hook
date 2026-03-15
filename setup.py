#!/usr/bin/env python3
"""
Cursor Telegram Hook - Setup Script

Complete guided setup for the Telegram hook plugin.
Walks a new user through every step: dependencies, telegram-mcp,
session string, credentials, MCP config, Cursor rule, and skill.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent
CONFIG_PATH = PLUGIN_DIR / "config.json"
WAIT_SCRIPT = PLUGIN_DIR / "wait_for_reply.py"
SKILL_SRC = PLUGIN_DIR / "skill" / "SKILL.md"

RULE_TEMPLATE = '''---
description: Telegram hook with slash command control
alwaysApply: {always_apply}
---

# Telegram Response Hook

## Slash Commands (check FIRST, before anything else)

Before doing anything, check if the user's message is one of these commands:

- `/telegram_on` — Enable the hook. Read `{config_path}`, set `"enabled"` to `true`, write it back. Reply "Telegram hook is now ON. I'll send summaries after each response." Then stop — do not run the hook flow for this message.

- `/telegram_off` — Disable the hook. Read `{config_path}`, set `"enabled"` to `false`, write it back. Reply "Telegram hook is now OFF." Then stop.

- `/telegram_status` — Read `{config_path}` and report the current settings (enabled, language, wait time, poll interval). Then stop.

- `/telegram_lang_he` — Set `"language"` to `"he"` in config. Reply confirming. Then stop.

- `/telegram_lang_en` — Set `"language"` to `"en"` in config. Reply confirming. Then stop.

If the message is NOT a slash command, continue below.

## Post-response Hook

After completing your answer to the user's (non-command) message:

1. Read `{config_path}` and parse the JSON.
2. If `"enabled"` is `false`, **skip the entire hook** — do nothing more.
3. Note the `"language"` field.

### Flow (only if enabled)

1. **Send run summary to Telegram**: Use the `user-telegram-mcp` MCP server's `send_message` tool to send a summary of **everything you did in this run** to chat_id `{chat_id}`. Format the message like this:

   ```
   🤖 **Cursor Update**
   ━━━━━━━━━━━━━━━
   <2-4 sentence summary covering: what the user asked, what you did, the outcome>
   ━━━━━━━━━━━━━━━
   💬 Reply here to send instructions
   ```

   Use Telegram markdown: **bold** for the header.

   **Language**: If `language` is `he`, write the entire summary in Hebrew. If `en`, write in English.

2. **Get current timestamp**: Use Shell tool to run `python3 -c "import time; print(int(time.time()))"` and capture the UNIX timestamp. Call it `SEND_TS`.

3. **Wait for reply**: Run the polling script via Shell tool:
   ```
   uv run {wait_script} --config {config_path} --after-timestamp SEND_TS
   ```
   Set `block_until_ms` to `{block_ms}`. The script polls Telegram every {poll_interval}s and exits as soon as a reply arrives.

4. **Check the result** based on the exit code:
   - **Exit 0** — stdout contains the reply text. Treat it as a new user instruction. Execute it fully, then repeat from step 1 (max {max_loops} loops total).
   - **Exit 1** — timeout, no reply received. Stop.
   - **Exit 2** — stop word received. Stop immediately.
'''

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"  ✓ Config saved to {CONFIG_PATH}")


def prompt(msg, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"  {msg}{suffix}: ").strip()
    return val if val else default


def run_cmd(cmd, check=False):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        return None
    return result


def header(title):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")

# ─── Step 1: Check Prerequisites ─────────────────────────────────────────────

def check_prerequisites():
    header("Step 1: Checking Prerequisites")

    uv = run_cmd("uv --version", check=True)
    if uv is None:
        print("  ✗ 'uv' is not installed.")
        print("    Install it: curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("    Then re-run this setup.")
        sys.exit(1)
    print(f"  ✓ uv found: {uv.stdout.strip()}")

    git = run_cmd("git --version", check=True)
    if git is None:
        print("  ✗ 'git' is not installed. Install git and re-run.")
        sys.exit(1)
    print(f"  ✓ git found: {git.stdout.strip()}")

    print("  ✓ Python 3 (you're running this script)")

# ─── Step 2: Clone telegram-mcp ──────────────────────────────────────────────

def setup_telegram_mcp():
    header("Step 2: Telegram MCP Server")
    print("  The plugin needs the telegram-mcp server to send messages.")
    print("  https://github.com/chigwell/telegram-mcp\n")

    default_dir = str(Path.home() / "projects" / "telegram-mcp")
    telegram_mcp_dir = prompt("Path to telegram-mcp (will clone if missing)", default_dir)
    telegram_mcp_path = Path(telegram_mcp_dir)

    if telegram_mcp_path.exists() and (telegram_mcp_path / "main.py").exists():
        print(f"  ✓ telegram-mcp already exists at {telegram_mcp_dir}")
    else:
        print(f"  Cloning telegram-mcp to {telegram_mcp_dir}...")
        telegram_mcp_path.parent.mkdir(parents=True, exist_ok=True)
        result = run_cmd(f'git clone https://github.com/chigwell/telegram-mcp.git "{telegram_mcp_dir}"')
        if result.returncode != 0:
            print(f"  ✗ Clone failed: {result.stderr.strip()}")
            print("  Clone it manually and re-run setup.")
            sys.exit(1)
        print(f"  ✓ Cloned successfully")

    return telegram_mcp_dir

# ─── Step 3: Telegram Credentials ────────────────────────────────────────────

def setup_credentials(cfg):
    header("Step 3: Telegram API Credentials")
    print("  You need API credentials to connect to Telegram.")
    print("  You can get your own from https://my.telegram.org/apps")
    print("  OR use the public Telegram Desktop defaults (recommended).\n")

    use_defaults = prompt("Use Telegram Desktop default credentials? (y/n)", "y")
    if use_defaults.lower() == "y":
        cfg["telegram_api_id"] = "2040"
        cfg["telegram_api_hash"] = "b18441a1ff607e10a989891a5462e627"
        print("  ✓ Using Telegram Desktop credentials (API ID: 2040)")
    else:
        cfg["telegram_api_id"] = prompt("Telegram API ID")
        cfg["telegram_api_hash"] = prompt("Telegram API Hash")
        print("  ✓ Custom credentials saved")

# ─── Step 4: Session String ──────────────────────────────────────────────────

def setup_session_string(cfg, telegram_mcp_dir):
    header("Step 4: Telegram Session String")
    print("  A session string authenticates Cursor as your Telegram account.")
    print("  You only need to generate this once.\n")

    if cfg.get("telegram_session_string"):
        reuse = prompt("Session string already set. Keep it? (y/n)", "y")
        if reuse.lower() == "y":
            print("  ✓ Keeping existing session string")
            return

    print("  To generate a session string:")
    print(f"    1. Open a NEW terminal (not this one)")
    print(f"    2. Run: cd {telegram_mcp_dir}")
    print(f"    3. Create a .env file with:")
    print(f"         TELEGRAM_API_ID={cfg.get('telegram_api_id', '2040')}")
    print(f"         TELEGRAM_API_HASH={cfg.get('telegram_api_hash', 'b18441a1ff607e10a989891a5462e627')}")
    print(f"    4. Run: uv run session_string_generator.py")
    print(f"    5. Scan the QR code with Telegram:")
    print(f"         Settings > Devices > Link Desktop Device")
    print(f"    6. Copy the session string it outputs\n")

    session = prompt("Paste your session string here (or Enter to skip)")
    if session:
        cfg["telegram_session_string"] = session
        print("  ✓ Session string saved")
    else:
        print("  ⚠ Skipped — you'll need to set this before the hook works.")
        print("    Edit config.json and add your session string later.")

# ─── Step 5: Chat ID ─────────────────────────────────────────────────────────

def setup_chat_id(cfg):
    header("Step 5: Your Telegram User ID")
    print("  Messages are sent to your Saved Messages (chat with yourself).")
    print("  You need your numeric Telegram user ID.\n")
    print("  To find it:")
    print("    - Open @userinfobot on Telegram and send /start")
    print("    - Or check https://web.telegram.org — your ID is in the URL\n")

    if cfg.get("telegram_chat_id"):
        keep = prompt(f"Current ID: {cfg['telegram_chat_id']}. Keep it? (y/n)", "y")
        if keep.lower() == "y":
            return

    chat_id = prompt("Enter your Telegram user ID (numeric)")
    if chat_id:
        cfg["telegram_chat_id"] = int(chat_id)
        print(f"  ✓ Chat ID set to {chat_id}")
    else:
        print("  ⚠ Skipped — you'll need to set this in config.json")

# ─── Step 6: Preferences ─────────────────────────────────────────────────────

def setup_preferences(cfg):
    header("Step 6: Hook Preferences")

    cfg["wait_seconds"] = int(prompt("Max wait time for a reply (seconds)", str(cfg.get("wait_seconds", 120))))
    cfg["poll_interval"] = int(prompt("Poll interval — check for replies every N seconds", str(cfg.get("poll_interval", 10))))
    cfg["max_loops"] = int(prompt("Max reply loops per response", str(cfg.get("max_loops", 3))))
    cfg["message_prefix"] = prompt("Message prefix (identifies Cursor messages)", cfg.get("message_prefix", "🤖 Cursor:"))

    print("\n  Summary language:")
    print("    en = English (default)")
    print("    he = Hebrew (עברית)")
    cfg["language"] = prompt("Language for Telegram summaries", cfg.get("language", "en"))

    print("  ✓ Preferences saved")

# ─── Step 7: Install MCP Config ──────────────────────────────────────────────

def install_mcp_config(cfg, telegram_mcp_dir):
    header("Step 7: Install MCP Server in Cursor")
    print("  Adding telegram-mcp to ~/.cursor/mcp.json")
    print("  This lets Cursor send Telegram messages.\n")

    mcp_path = Path.home() / ".cursor" / "mcp.json"

    if not mcp_path.exists():
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_data = {"mcpServers": {}}
    else:
        with open(mcp_path) as f:
            mcp_data = json.load(f)

    if "telegram-mcp" in mcp_data.get("mcpServers", {}):
        update = prompt("telegram-mcp already exists in MCP config. Overwrite? (y/n)", "y")
        if update.lower() != "y":
            print("  → Skipped")
            return

    mcp_data.setdefault("mcpServers", {})["telegram-mcp"] = {
        "command": "uv",
        "args": ["--directory", telegram_mcp_dir, "run", "main.py"],
        "type": "stdio",
        "env": {
            "TELEGRAM_API_ID": str(cfg.get("telegram_api_id", "")),
            "TELEGRAM_API_HASH": cfg.get("telegram_api_hash", ""),
            "TELEGRAM_SESSION_STRING": cfg.get("telegram_session_string", ""),
        },
    }

    with open(mcp_path, "w") as f:
        json.dump(mcp_data, f, indent=2)
    print(f"  ✓ MCP config updated at {mcp_path}")

# ─── Step 8: Install Cursor Rule + Skill ─────────────────────────────────────

def install_cursor_assets(cfg):
    header("Step 8: Install Cursor Rule & Skill")

    project_dir = prompt("Path to your Cursor project root", str(Path.cwd()))

    # Rule
    rules_dir = Path(project_dir) / ".cursor" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    always_apply = prompt("Always apply the rule to new chats? (y/n)", "y").lower() == "y"
    block_ms = (cfg["wait_seconds"] + 5) * 1000

    rule_content = RULE_TEMPLATE.format(
        always_apply=str(always_apply).lower(),
        config_path=str(CONFIG_PATH),
        wait_script=str(WAIT_SCRIPT),
        chat_id=cfg.get("telegram_chat_id", "YOUR_CHAT_ID"),
        prefix=cfg.get("message_prefix", "🤖 Cursor:"),
        wait_seconds=cfg["wait_seconds"],
        poll_interval=cfg.get("poll_interval", 10),
        block_ms=block_ms,
        max_loops=cfg["max_loops"],
        language=cfg.get("language", "en"),
    )

    rule_path = rules_dir / "telegram-hook.mdc"
    with open(rule_path, "w") as f:
        f.write(rule_content)
    print(f"  ✓ Cursor rule installed at {rule_path}")

    # Skill
    skills_dir = Path(project_dir) / ".cursor" / "skills" / "telegram-hook"
    skills_dir.mkdir(parents=True, exist_ok=True)
    if SKILL_SRC.exists():
        shutil.copy2(SKILL_SRC, skills_dir / "SKILL.md")
        print(f"  ✓ Cursor skill installed at {skills_dir / 'SKILL.md'}")
    else:
        print(f"  ⚠ Skill source not found at {SKILL_SRC} — skipped")

# ─── Quick commands ───────────────────────────────────────────────────────────

def toggle():
    cfg = load_config()
    cfg["enabled"] = not cfg.get("enabled", False)
    save_config(cfg)
    state = "ON" if cfg["enabled"] else "OFF"
    print(f"  Telegram hook is now {state}")


def main():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║     Cursor Telegram Hook — Setup Wizard      ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print("  Control Cursor from your phone via Telegram.")
    print("  This wizard will walk you through everything.")

    # Quick commands
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "toggle":
            toggle()
            return
        if cmd == "on":
            cfg = load_config()
            cfg["enabled"] = True
            save_config(cfg)
            print("  Telegram hook is now ON")
            return
        if cmd == "off":
            cfg = load_config()
            cfg["enabled"] = False
            save_config(cfg)
            print("  Telegram hook is now OFF")
            return
        if cmd == "status":
            cfg = load_config()
            print(json.dumps(cfg, indent=2))
            return
        if cmd == "help":
            print("\n  Usage:")
            print("    python setup.py          Full setup wizard")
            print("    python setup.py on       Enable hook")
            print("    python setup.py off      Disable hook")
            print("    python setup.py toggle   Toggle on/off")
            print("    python setup.py status   Show config")
            print("    python setup.py help     This message")
            return

    cfg = load_config()

    # Step 1: Prerequisites
    check_prerequisites()

    # Step 2: telegram-mcp
    telegram_mcp_dir = setup_telegram_mcp()

    # Step 3: API credentials
    setup_credentials(cfg)

    # Step 4: Session string
    setup_session_string(cfg, telegram_mcp_dir)

    # Step 5: Chat ID
    setup_chat_id(cfg)

    # Step 6: Preferences
    setup_preferences(cfg)

    # Save config
    save_config(cfg)

    # Step 7: MCP config
    install_mcp_config(cfg, telegram_mcp_dir)

    # Step 8: Cursor rule + skill
    install_cursor_assets(cfg)

    # Done
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║            Setup Complete!                    ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print(f"  Hook:     {'ENABLED' if cfg.get('enabled') else 'DISABLED (type /telegram_on in Cursor to enable)'}")
    print(f"  Language: {'Hebrew' if cfg.get('language') == 'he' else 'English'}")
    print(f"  Timer:    {cfg.get('wait_seconds', 120)}s (polls every {cfg.get('poll_interval', 10)}s)")
    print(f"  Loops:    {cfg.get('max_loops', 3)} max")
    print()
    print("  ⚡ Next steps:")
    print("    1. Restart Cursor to load the MCP server")
    print("    2. Open a new chat")
    print("    3. Say 'telegram on' or type /telegram_on")
    print("    4. Check your Telegram Saved Messages!")
    print()
    print("  📱 In Cursor chat, you can say:")
    print("    • 'telegram on'     — activate the hook")
    print("    • 'telegram off'    — deactivate")
    print("    • 'telegram status' — check settings")
    print("    • 'telegram hebrew' — switch to Hebrew")
    print()
    print("  🔧 CLI shortcuts:")
    print("    python setup.py on/off/toggle/status")


if __name__ == "__main__":
    main()
