"""Telegram webhook route."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.core.deps import get_store
from app.core.firestore import Store
from app.features.telegram import service
from app.features.telegram.client import TelegramSendError

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.post("/webhook", include_in_schema=False)
def telegram_webhook(payload: dict, request: Request,
                     x_telegram_bot_api_secret_token: str | None = Header(default=None),
                     store: Store = Depends(get_store)) -> dict:
    settings = request.app.state.settings
    try:
        service.check_secret(settings, x_telegram_bot_api_secret_token)
        return service.handle_update(payload, settings=settings, store=store,
                                     adapter_factory=request.app.state.analysis_adapter_factory,
                                     send_message=getattr(request.app.state, "telegram_send_message", None))
    except service.TelegramForbidden:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "텔레그램 웹훅 비밀값이 맞지 않습니다") from None
    except service.TelegramConfigError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"텔레그램 설정 오류: {exc}") from None
    except TelegramSendError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "텔레그램으로 답장을 보내지 못했습니다") from None
