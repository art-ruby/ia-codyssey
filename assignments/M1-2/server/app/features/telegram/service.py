"""Telegram webhook service.

MVP scope: Telegram acts as another question channel for the existing AI Secretary chat.
It does not read/write Telegram-specific state. The server remains the hub: Telegram →
AI Secretary → Hermes → Telegram.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.core.config import Settings
from app.core.context import RequestContext
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.chat import service as chat_service
from app.features.chat.service import ChatFailed
from app.features.conversations.service import ConversationFull
from app.features.telegram.client import TelegramClient, TelegramSendError

MAX_TELEGRAM_TEXT = 3900


class TelegramConfigError(RuntimeError):
    """Telegram integration is not configured safely."""


class TelegramForbidden(RuntimeError):
    """The webhook secret is missing or wrong."""


@dataclass(frozen=True)
class TelegramMessage:
    update_id: int
    chat_id: int
    text: str


CHAT_FAILURE_TEXT = {
    "search_failed": "자료를 찾는 중 문제가 생겼습니다. 잠시 뒤 다시 시도하세요.",
    "quota_exceeded": "오늘 AI 요청 한도에 도달했습니다. 서울 시간 자정 이후 다시 질문하세요.",
    "provider_failed": "AI 답변을 받지 못했습니다. 잠시 뒤 다시 시도하세요.",
}


def configured(settings: Settings) -> bool:
    return bool(settings.get("TELEGRAM_BOT_TOKEN") and settings.get("TELEGRAM_WEBHOOK_SECRET"))


def check_secret(settings: Settings, received: str | None) -> None:
    expected = settings.get("TELEGRAM_WEBHOOK_SECRET")
    if not expected or received != expected:
        raise TelegramForbidden()


def parse_update(payload: dict[str, Any]) -> TelegramMessage | None:
    update_id = payload.get("update_id")
    message = payload.get("message") or payload.get("edited_message")
    if not isinstance(update_id, int) or not isinstance(message, dict):
        return None
    chat = message.get("chat")
    text = message.get("text")
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    if not isinstance(chat_id, int) or not isinstance(text, str) or not text.strip():
        return None
    return TelegramMessage(update_id=update_id, chat_id=chat_id, text=text.strip())


def _allowed_chat(settings: Settings) -> int | None:
    raw = settings.get("TELEGRAM_ALLOWED_CHAT_ID")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise TelegramConfigError("TELEGRAM_ALLOWED_CHAT_ID는 숫자여야 합니다") from exc


def _owner(settings: Settings) -> str:
    owner = settings.get("OWNER_UID")
    if not owner:
        raise TelegramConfigError("OWNER_UID 누락")
    return owner


def _format_answer(body: dict[str, Any]) -> str:
    answer = body.get("answer") if isinstance(body, dict) else None
    if not isinstance(answer, dict):
        return "답변을 만들지 못했습니다. 잠시 뒤 다시 시도하세요."
    parts = [answer.get("from_materials") or "", answer.get("interpretation") or ""]
    notes = [n for n in answer.get("limitations") or [] if isinstance(n, str)]
    if notes:
        parts.append("참고: " + " / ".join(notes[:2]))
    text = "\n\n".join(p.strip() for p in parts if p and p.strip())
    return (text or "답변할 내용을 찾지 못했습니다.")[:MAX_TELEGRAM_TEXT]


def _start_text(chat_id: int, allowed: int | None) -> str:
    if allowed is None:
        return ("AI Secretary Telegram 연결 준비가 필요합니다. Render 환경변수 "
                f"TELEGRAM_ALLOWED_CHAT_ID에 이 값을 넣으세요: {chat_id}")
    return "AI Secretary와 연결되었습니다. 이제 질문을 보내면 비서가 답합니다."


def handle_update(payload: dict[str, Any], *, settings: Settings, store: Store,
                  adapter_factory: Callable, send_message: Callable[[int, str], None] | None = None) -> dict[str, Any]:
    if not configured(settings):
        raise TelegramConfigError("TELEGRAM_BOT_TOKEN 또는 TELEGRAM_WEBHOOK_SECRET 누락")
    update = parse_update(payload)
    if update is None:
        return {"ok": True, "ignored": True}

    allowed = _allowed_chat(settings)
    sender = send_message or TelegramClient(settings.get("TELEGRAM_BOT_TOKEN")).send_message
    if update.text.startswith("/start"):
        sender(update.chat_id, _start_text(update.chat_id, allowed))
        return {"ok": True, "sent": True, "kind": "start"}
    if allowed is None:
        sender(update.chat_id, "아직 연결 설정이 끝나지 않았습니다. /start를 보내 chat_id를 확인하세요.")
        return {"ok": True, "sent": True, "kind": "not_configured"}
    if update.chat_id != allowed:
        return {"ok": True, "ignored": True, "reason": "chat_not_allowed"}

    ctx = RequestContext(owner_id=_owner(settings), mode="personal", request_id=f"telegram-{update.update_id}")

    def run() -> Result:
        try:
            status, body = chat_service.handle_chat(
                store, ctx, None, update.text, adapter_factory, settings.ai_daily_request_limit,
            )
            text = _format_answer(body) if status == 200 else "답변은 받았지만 저장 상태를 확인하지 못했습니다. 웹에서 확인해 주세요."
        except ChatFailed as exc:
            text = CHAT_FAILURE_TEXT.get(exc.reason, "질문을 처리하지 못했습니다. 잠시 뒤 다시 시도하세요.")
            status = 200
            body = {"reason": exc.reason, "kind": exc.kind}
        except ConversationFull:
            text = "대화 한도에 도달했습니다. 웹에서 새 대화를 시작해 주세요."
            status = 200
            body = {"reason": "conversation_full"}
        sender(update.chat_id, text)
        return Result(200, {"ok": True, "sent": True, "chat_status": status, "chat": body})

    try:
        result = run_idempotent(store, ctx, "POST", "/api/telegram/webhook", {"update_id": update.update_id}, run)
    except TelegramSendError:
        raise
    return {**result.body, "replayed": result.replayed}
