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
    "ai_checked_scope", "ai_grounding",
)
# 문장부호 뒤 공백이 없어도 문장을 나눈다("One.Two."). 소수점(1.5)·도메인(example.com)처럼
# 뒤에 숫자·영문 소문자가 바로 붙으면 나누지 않는다.
_SENTENCE_END = re.compile(r"[.!?。]+(?=\s|$|[^a-z0-9/_\-.!?。\s])")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
# 요약 문장이 입력과 공유해야 하는 글자쌍 비율. 2026-10-02 측정: 실제 요약 문장 0.44~0.96,
# 입력과 무관한 주장 0~0.12, 입력 단어로 뜻을 뒤집은 문장 0.29. 뒤집힌 뜻은 이 방법으로 못 잡는다.
MIN_SUMMARY_OVERLAP = 0.35
# 요약에 있어야 하는 최소 글자 수(문장부호·공백 제외). "X."·"??" 같은 빈 요약을 막는다.
MIN_SUMMARY_CHARS = 10
# 겹침 검사를 하지 않는 필드(추론·조언이라 입력에 없는 표현이 자연스럽다). 숫자 검사는 받는다.
UNVERIFIED_FIELDS = ("title", "importance_reason", "recommended_action", "keywords", "uncertainties")


def normalize_space(text: str) -> str:
    return " ".join(text.split())


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def word_chars(text: str) -> str:
    """문장부호·공백을 뺀 글자. 길이 기준은 이 값으로 센다("--------"는 0자)."""
    return re.sub(r"[\W_]+", "", text)


def _bigrams(text: str) -> set[str]:
    t = word_chars(text.lower())
    return {t[i:i + 2] for i in range(len(t) - 1)}


def overlap_ratio(sentence: str, source: str) -> float:
    # 글자쌍이 없는 문장(한 글자·문장부호뿐)은 근거를 확인할 수 없으므로 겹침 0으로 본다.
    grams = _bigrams(sentence)
    return len(grams & _bigrams(source)) / len(grams) if grams else 0.0


def numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


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

    @field_validator("title", "importance_reason")
    @classmethod
    def has_words(cls, value: str) -> str:
        if not word_chars(value):
            raise ValueError("글자가 없습니다")
        return value

    @field_validator("summary")
    @classmethod
    def at_most_three_sentences(cls, value: str) -> str:
        if len(word_chars(value)) < MIN_SUMMARY_CHARS:
            raise ValueError(f"요약은 글자 {MIN_SUMMARY_CHARS}자 이상")
        # 2~3문장을 요청하지만, 짧은 입력은 한 문장 요약이 자연스러워 하한은 두지 않는다.
        if len(sentences(value)) > 3:
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
    # 무엇을 어떻게 대조했는지. 화면은 이 값으로 'AI 제안 · 사실 확인 안 됨'을 표시한다.
    ai_grounding: dict
    model: str
    total_tokens: int | None

    def to_fields(self) -> dict:
        return self.model_dump(include=set(AI_FIELDS))
