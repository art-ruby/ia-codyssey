"""AI 분석 결과의 계약(PRD §6.3, T04.01 결정).

Provider 응답(`ModelOutput`)은 형식이 맞아도 그대로 믿지 않는다. 인용 근거를 입력과
대조하고, 목록에 없는 프로젝트·종류는 비운 뒤 `AnalysisResult`로 돌려준다.
AI 제안값은 모두 `ai_` 접두어를 붙여 사용자 최종값(`user_importance` 등)과 섞이지 않게 한다.
확인 범위(`ai_checked_scope`)는 서버가 실제로 보낸 입력으로 계산한다.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Importance = Literal["high", "medium", "low"]
KINDS = ("article", "document", "note", "reference", "tool", "other")
# AI에 보내는 자료 필드. 사용자 최종값(중요도·프로젝트)은 판단을 끌고 갈 수 있어 보내지 않는다.
INPUT_FIELDS = ("title", "description", "body", "save_reason", "memo")
# 이 필드 중 하나라도 있어야 분석할 수 있다(자료 서비스의 `link_only` 판정과 같은 기준).
CONTENT_FIELDS = ("title", "description", "body")
MIN_EVIDENCE_CHARS = 8
AI_FIELDS = (
    "ai_title", "ai_summary", "ai_importance", "ai_importance_reason", "ai_primary_project_id",
    "ai_kind", "ai_keywords", "ai_uncertainties", "ai_recommended_action", "ai_evidence",
    "ai_checked_scope",
)
_SENTENCE_END = re.compile(r"(?<=[.!?。])\s+")


def normalize_space(text: str) -> str:
    return " ".join(text.split())


class ModelOutput(BaseModel):
    """Provider가 내야 하는 JSON. 정의 밖의 필드가 오면 거부한다."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=600)
    importance: Importance | None
    importance_reason: str = Field(min_length=1, max_length=300)
    primary_project_id: str | None
    kind: str | None
    keywords: list[str] = Field(max_length=8)
    uncertainties: list[str] = Field(max_length=3)
    recommended_action: str = Field(max_length=200)
    evidence: list[str] = Field(min_length=1, max_length=3)

    @field_validator("summary")
    @classmethod
    def at_most_three_sentences(cls, value: str) -> str:
        # 2~3문장을 요청하지만, 짧은 입력은 한 문장 요약이 자연스러워 하한은 두지 않는다.
        if len([s for s in _SENTENCE_END.split(value) if s.strip()]) > 3:
            raise ValueError("요약은 3문장 이하")
        return value

    @field_validator("keywords", "uncertainties", "evidence")
    @classmethod
    def clean_items(cls, items: list[str]) -> list[str]:
        if any(len(item) > 200 for item in items):
            raise ValueError("항목은 200자 이하")
        return list(dict.fromkeys(item.strip() for item in items if item.strip()))


class AnalysisResult(BaseModel):
    """검증을 마친 분석 결과. 저장(T04.02)은 `to_fields()`의 값을 그대로 쓴다."""

    ai_title: str
    ai_summary: str
    ai_importance: Importance | None
    ai_importance_reason: str
    ai_primary_project_id: str | None
    ai_kind: str | None
    ai_keywords: list[str]
    ai_uncertainties: list[str]
    ai_recommended_action: str | None
    ai_evidence: list[str]
    ai_checked_scope: dict
    model: str
    total_tokens: int | None

    def to_fields(self) -> dict:
        return self.model_dump(include=set(AI_FIELDS))
