"""Run the local Hermes relay on loopback for Tailscale Funnel."""

from __future__ import annotations

import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import uvicorn

from app.core.config import load_settings
from app.hermes_relay import create_relay_app

RELAY_HOST = "127.0.0.1"
RELAY_PORT = 8766


def main() -> None:
    app = create_relay_app(load_settings())
    uvicorn.run(app, host=RELAY_HOST, port=RELAY_PORT, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
