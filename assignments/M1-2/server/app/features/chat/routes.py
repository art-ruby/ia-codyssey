"""채팅 API (PRD §13: POST /api/chat, T07.02). 답변·검증된 출처·숫자 출처·저장된 대화/메시지 ID를 돌려준다."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.chat import service
from app.features.chat.schemas import ChatQuestion

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", responses={
    404: {"description": "대화가 없거나 다른 모드·소유자의 대화"},
    409: {"description": "대화 메시지 한도 도달 또는 같은 요청 처리 중"},
    429: {"description": "오늘 AI 요청 한도 도달(reason=quota_exceeded). Provider 호출 없음"},
    502: {"description": "AI 호출 실패(reason=provider_failed, kind=오류 종류). 대화는 저장하지 않음"},
    503: {"description": "자료 검색 실패(reason=search_failed, 사용량 없음 — '결과 없음'과 다름) 또는 "
                         "답을 받았지만 대화 저장 실패(reason=save_failed, 답 본문·pending_id 포함)"},
})
def chat(body: ChatQuestion, request: Request, ctx: RequestContext = Depends(get_context),
         store: Store = Depends(get_store)):
    settings = request.app.state.settings

    def handler() -> Result:
        return Result(*service.handle_chat(store, ctx, body.conversation_id, body.question,
                                           request.app.state.analysis_adapter_factory,
                                           settings.ai_daily_request_limit))

    result = run_idempotent(store, ctx, "POST", "/api/chat", body.model_dump(), handler)
    return JSONResponse(result.body, status_code=result.status_code)
