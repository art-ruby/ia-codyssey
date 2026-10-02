"""채팅 요청 형식(T07.01). 질문은 2,000자까지(PRD §11 권장 문맥 한도)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

MAX_QUESTION = 2000


class ChatQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=MAX_QUESTION)
    conversation_id: str | None = None  # 대화 저장(T07.03)에서 쓴다
