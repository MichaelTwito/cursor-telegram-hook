"""
Installs (or removes) the Telegram MCP server entry in ~/.claude/settings.json.

Usage:
  python install.py install    — add mcpServers entry
  python install.py uninstall  — remove it
  python install.py status     — show current state
"""

import json
import sys
from pathlib import Path

SERVER_NAME = "telegram"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
SERVER_PY = Path(__file__).parent / "server.py"
PROJECT_DIR = Path(__file__).parent


def _entry() -> dict:
    return {
        "command": "uv",
        "args": ["run", "--project", str(PROJECT_DIR), "python", str(SERVER_PY)],
    }


def _load() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def _save(data: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _is_installed(settings: dict) -> bool:
    return SERVER_NAME in settings.get("mcpServers", {})


def install() -> None:
    settings = _load()
    if _is_installed(settings):
        print(f"  ✓ '{SERVER_NAME}' MCP server already installed in {SETTINGS_PATH}")
        return

    settings.setdefault("mcpServers", {})[SERVER_NAME] = _entry()
    _save(settings)
    print(f"  ✓ '{SERVER_NAME}' MCP server installed in {SETTINGS_PATH}")
    print(f"    Command: uv run --project {PROJECT_DIR} python server.py")
    print()
    print("  Restart Claude Code (or reload the MCP server list) to activate.")


def uninstall() -> None:
    settings = _load()
    mcp_servers = settings.get("mcpServers", {})
    if SERVER_NAME not in mcp_servers:
        print(f"  '{SERVER_NAME}' not found — nothing to remove.")
        return

    del mcp_servers[SERVER_NAME]
    if not mcp_servers:
        settings.pop("mcpServers", None)
    _save(settings)
    print(f"  ✓ '{SERVER_NAME}' MCP server removed from {SETTINGS_PATH}")


def status() -> None:
    settings = _load()
    if _is_installed(settings):
        entry = settings["mcpServers"][SERVER_NAME]
        print(f"  ✓ '{SERVER_NAME}' MCP server is INSTALLED")
        print(f"    {SETTINGS_PATH}")
        print(f"    {json.dumps(entry)}")
    else:
        print(f"  ✗ '{SERVER_NAME}' MCP server is NOT installed")
        print(f"    Run: python {Path(__file__).name} install")


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
        print("Usage: python install.py [install|uninstall|status]")
        sys.exit(1)
