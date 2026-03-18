#!/usr/bin/env python3
"""Start the Telegram Hook Dashboard."""
import uvicorn

if __name__ == "__main__":
    print("Dashboard running at http://localhost:8080")
    uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True, app_dir=__file__.rsplit("/", 1)[0])
