"""
Telegram Hook Dashboard — FastAPI backend.

Run via: python run.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Resolve plugin root regardless of CWD
PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR / "telegram_mcp"))

import registry  # noqa: E402

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
CONFIG_PATH = PLUGIN_DIR / "config.json"

app = FastAPI(title="Telegram Hook Dashboard")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

BOT_API = "https://api.telegram.org/bot{token}/{method}"


def _api(token: str, method: str, **params) -> dict[str, Any]:
    url = BOT_API.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return {"ok": False, "description": exc.read().decode(errors="replace")}
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {
            "enabled": False,
            "wait_seconds": 120,
            "poll_interval": 10,
            "max_loops": 3,
            "language": "en",
            "stop_words": ["stop", "exit", "quit", "עצור", "יציאה"],
        }
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _save_config(data: dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ── HTML ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ── Bot API ───────────────────────────────────────────────────────────────────

class AddBotRequest(BaseModel):
    token: str


class UpdateBotRequest(BaseModel):
    name: str | None = None
    assigned_project: str | None = None
    enabled: bool | None = None
    chat_id: int | None = None


@app.get("/api/bots")
async def api_list_bots():
    bots = registry.list_bots()
    # Mask token: show first 10 chars + ***
    safe = []
    for b in bots:
        b2 = dict(b)
        tok = b2.get("token", "")
        b2["token_masked"] = tok[:10] + "***" if len(tok) > 10 else "***"
        safe.append(b2)
    return JSONResponse(safe)


@app.post("/api/bots")
async def api_add_bot(req: AddBotRequest):
    token = req.token.strip()
    me = _api(token, "getMe")
    if not me.get("ok"):
        raise HTTPException(400, detail=f"Invalid token: {me.get('description', 'unknown error')}")
    name = me["result"].get("first_name") or me["result"].get("username") or "Bot"
    username = me["result"].get("username", "")
    bot = registry.add_bot(token, name)
    bot["username"] = username
    return JSONResponse(bot, status_code=201)


@app.delete("/api/bots/{bot_id}")
async def api_delete_bot(bot_id: str):
    if not registry.delete_bot(bot_id):
        raise HTTPException(404, detail="Bot not found")
    return JSONResponse({"deleted": True})


@app.patch("/api/bots/{bot_id}")
async def api_update_bot(bot_id: str, req: UpdateBotRequest):
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    bot = registry.update_bot(bot_id, **fields)
    if bot is None:
        raise HTTPException(404, detail="Bot not found")
    return JSONResponse(bot)


@app.post("/api/bots/{bot_id}/test")
async def api_test_bot(bot_id: str):
    bot = registry.get_bot(bot_id)
    if not bot:
        raise HTTPException(404, detail="Bot not found")
    if not bot.get("chat_id"):
        raise HTTPException(400, detail="No chat_id set. Send /start to this bot on Telegram first.")
    result = _api(bot["token"], "sendMessage",
                  chat_id=bot["chat_id"],
                  text="\U0001f916 *Test message* from Telegram Hook Dashboard \u2705",
                  parse_mode="Markdown")
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("description", "Failed to send"))
    registry.touch_bot(bot_id)
    return JSONResponse({"sent": True, "message_id": result["result"]["message_id"]})


@app.get("/api/bots/{bot_id}/chat_id")
async def api_fetch_chat_id(bot_id: str):
    """Poll getUpdates to auto-detect the chat_id from the most recent /start message."""
    bot = registry.get_bot(bot_id)
    if not bot:
        raise HTTPException(404, detail="Bot not found")

    updates = _api(bot["token"], "getUpdates", timeout=0, limit=50)
    if not updates.get("ok"):
        raise HTTPException(500, detail=updates.get("description", "getUpdates failed"))

    chat_id = None
    for update in reversed(updates.get("result", [])):
        msg = update.get("message")
        if msg and msg.get("text", "").startswith("/start"):
            chat_id = msg["chat"]["id"]
            break
        # Also accept any message
        if msg:
            chat_id = msg["chat"]["id"]

    if chat_id is None:
        return JSONResponse({"found": False, "chat_id": None})

    registry.update_bot(bot_id, chat_id=chat_id)
    return JSONResponse({"found": True, "chat_id": chat_id})


# ── Config API ────────────────────────────────────────────────────────────────

@app.get("/api/config")
async def api_get_config():
    return JSONResponse(_load_config())


@app.put("/api/config")
async def api_put_config(request: Request):
    body = await request.json()
    cfg = _load_config()
    allowed = {"enabled", "wait_seconds", "poll_interval", "max_loops", "language", "stop_words", "message_prefix"}
    for k, v in body.items():
        if k in allowed:
            cfg[k] = v
    _save_config(cfg)
    return JSONResponse(cfg)
