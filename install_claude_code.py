#!/usr/bin/env python3
"""
Installs (or removes) the Telegram Stop hook in ~/.claude/settings.json.

Usage:
  python install_claude_code.py install   — add the hook
  python install_claude_code.py uninstall — remove the hook
  python install_claude_code.py status    — show current hook state
"""

import json
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent
HOOK_SCRIPT = PLUGIN_DIR / "claude-hook.py"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
HOOK_COMMAND = f"python {HOOK_SCRIPT}"


def load_settings():
    if not SETTINGS_PATH.exists():
        return {}
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def save_settings(data):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def hook_entry():
    return {"hooks": [{"type": "command", "command": HOOK_COMMAND}]}


def is_installed(settings):
    for entry in settings.get("hooks", {}).get("Stop", []):
        for h in entry.get("hooks", []):
            if h.get("command", "").endswith("claude-hook.py"):
                return True
    return False


def install():
    settings = load_settings()
    if is_installed(settings):
        print(f"  ✓ Hook already installed in {SETTINGS_PATH}")
        return

    settings.setdefault("hooks", {}).setdefault("Stop", []).append(hook_entry())
    save_settings(settings)
    print(f"  ✓ Stop hook installed in {SETTINGS_PATH}")
    print(f"    Command: {HOOK_COMMAND}")


def uninstall():
    settings = load_settings()
    stop_hooks = settings.get("hooks", {}).get("Stop", [])
    new_stop = [
        entry for entry in stop_hooks
        if not any(h.get("command", "").endswith("claude-hook.py") for h in entry.get("hooks", []))
    ]
    if len(new_stop) == len(stop_hooks):
        print("  Hook not found — nothing to remove.")
        return

    settings["hooks"]["Stop"] = new_stop
    if not settings["hooks"]["Stop"]:
        del settings["hooks"]["Stop"]
    if not settings["hooks"]:
        del settings["hooks"]
    save_settings(settings)
    print(f"  ✓ Hook removed from {SETTINGS_PATH}")


def status():
    settings = load_settings()
    if is_installed(settings):
        print(f"  ✓ Hook is INSTALLED in {SETTINGS_PATH}")
        print(f"    Script: {HOOK_SCRIPT}")
    else:
        print(f"  ✗ Hook is NOT installed")
        print(f"    Run: python install_claude_code.py install")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "install"
    if cmd == "install":
        install()
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python install_claude_code.py [install|uninstall|status]")
        sys.exit(1)
