"""Telegram Bot API client boundary.

The webhook route receives Telegram updates, but outbound replies go through this tiny
client so tests can replace it without touching the network. It never logs tokens or
message bodies.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class TelegramSendError(RuntimeError):
    """Telegram did not accept the outbound message."""


@dataclass(frozen=True)
class TelegramClient:
    token: str
    timeout: int = 10

    def send_message(self, chat_id: int | str, text: str) -> None:
        payload = json.dumps({
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }).encode("utf-8")
        request = Request(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise TelegramSendError(type(exc).__name__) from None
        if not isinstance(data, dict) or data.get("ok") is not True:
            raise TelegramSendError("telegram_rejected")
