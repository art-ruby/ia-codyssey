"""대화 기록 저장·조회·불러오기·삭제.

과제 9절의 (A) 안을 택했다 — 목록은 messages 를 빼고 주고, 단건 조회에서
전체 messages 를 준다. 목록에 본문을 다 실으면 대화가 쌓일수록 첫 화면이
느려지고, '불러오기'라는 동작이 화면에서 의미를 잃는다.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import store_dep
from ..models.schemas import Conversation, ConversationCreate, ConversationSummary
from ..repositories.store import Store

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _title_of(record: dict[str, Any]) -> str:
    return record.get("title") or "제목 없음"


@router.get("", response_model=list[ConversationSummary], summary="대화 목록 (본문 제외)")
def list_conversations(store: Store = Depends(store_dep)) -> list[ConversationSummary]:
    rows = store.list_conversations()
    rows.sort(key=lambda r: str(r.get("updated_at")), reverse=True)
    return [
        ConversationSummary(
            id=row["id"],
            title=_title_of(row),
            message_count=len(row.get("messages") or []),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.post("", response_model=Conversation, status_code=status.HTTP_201_CREATED, summary="대화 저장")
def create_conversation(
    payload: ConversationCreate, store: Store = Depends(store_dep)
) -> Conversation:
    record = store.create_conversation(
        {
            "title": payload.title or "제목 없음",
            "messages": [m.model_dump(mode="json") for m in payload.messages],
        }
    )
    return Conversation.model_validate(record)


@router.get("/{conversation_id}", response_model=Conversation, summary="대화 불러오기 (전체 messages)")
def get_conversation(conversation_id: str, store: Store = Depends(store_dep)) -> Conversation:
    found = store.get_conversation(conversation_id)
    if found is None:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다")
    return Conversation.model_validate(found)


@router.delete("/{conversation_id}", summary="대화 삭제")
def delete_conversation(conversation_id: str, store: Store = Depends(store_dep)) -> dict[str, Any]:
    if not store.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다")
    return {"ok": True, "deleted": conversation_id}
