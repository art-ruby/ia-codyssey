"""대화 API (PRD §13, T07.03). 현재 모드의 대화만 다룬다.

`POST /api/conversations`는 새 빈 대화(`title`) 또는 저장 실패한 답의 재저장(`pending_id`)이다.
요청 본문에 메시지·답변·출처를 넣을 수 없다(서버가 검증해 보관한 답만 대화가 된다).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.conversations import service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, max_length=100)
    pending_id: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def one_purpose(self):
        if self.title is not None and self.pending_id is not None:
            raise ValueError("새 대화(title)와 저장 재시도(pending_id) 중 하나만 보내세요")
        return self


@router.post("", status_code=201, responses={
    200: {"description": "pending_id: 서버가 보관한 답을 대화에 저장(AI 재호출 없음). moved_to_new면 새 대화로 저장"},
    404: {"description": "저장 대기 답변이 없음(이미 저장했거나 버림)"},
})
def create_conversation(body: ConversationCreate, ctx: RequestContext = Depends(get_context),
                        store: Store = Depends(get_store)):
    def handler() -> Result:
        if body.pending_id:
            return Result(200, service.save_pending(store, ctx, body.pending_id))
        return Result(201, service.create_conversation(store, ctx, body.title or ""))

    result = run_idempotent(store, ctx, "POST", "/api/conversations", body.model_dump(), handler)
    return JSONResponse(result.body, status_code=result.status_code)


@router.get("")
def list_conversations(limit: int = Query(20, ge=1, le=100), cursor: str | None = None,
                       ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    """대화 목록(최근 만든 순, 메시지 제외)과 저장 대기 답변."""
    return service.list_conversations(store, ctx, limit, cursor)


@router.delete("/pending/{pending_id}")
def discard_pending(pending_id: str, ctx: RequestContext = Depends(get_context),
                    store: Store = Depends(get_store)) -> dict:
    """저장하지 못한 답을 버린다."""
    return run_idempotent(store, ctx, "DELETE", f"/api/conversations/pending/{pending_id}", {},
                          lambda: Result(200, service.discard_pending(store, ctx, pending_id))).body


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, ctx: RequestContext = Depends(get_context),
                     store: Store = Depends(get_store)) -> dict:
    """전체 메시지. 답변 출처마다 지금 자료 상태(`current_status`)를 붙인다."""
    return service.get_conversation(store, ctx, conversation_id)


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, ctx: RequestContext = Depends(get_context),
                        store: Store = Depends(get_store)) -> dict:
    """대화와 하위 메시지·저장 대기 답변을 지운다."""
    return run_idempotent(store, ctx, "DELETE", f"/api/conversations/{conversation_id}", {},
                          lambda: Result(200, service.delete_conversation(store, ctx, conversation_id))).body
