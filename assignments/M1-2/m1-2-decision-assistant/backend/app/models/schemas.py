"""Pydantic 계약.

과제 필수 필드(date/value/memo)를 그대로 유지하면서 RADAR 후보에 필요한
필드를 확장으로 얹는다. 확장 필드는 모두 선택값이라, RADAR 없이 손으로
넣은 데이터도 같은 컬렉션에 들어간다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

KST_LABEL = "%Y-%m-%d"


class Decision(str, Enum):
    """제작 판단 상태. 명세 6절에 따라 세 개로 고정한다.

    '아직 판단하지 않음'은 새 상태를 만들지 않고 None 으로 둔다.
    RADAR 의 NOT_RECORDED 도 어댑터에서 None 으로 옮긴다 —
    '기록이 없다'와 'SKIP 하기로 했다'는 다른 사실이다.
    """

    MAKE = "MAKE"
    WATCH = "WATCH"
    SKIP = "SKIP"


class DataSource(str, Enum):
    """이 레코드가 어디서 왔는지. 화면과 API 에서 표본과 실데이터를 섞지 않기 위해 쓴다."""

    SAMPLE = "sample"
    RADAR = "radar"
    MANUAL = "manual"


class CandidateBase(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    # ── 과제 필수 3개 ─────────────────────────────
    date: datetime = Field(..., description="후보가 관측된 시점")
    value: float = Field(..., ge=0, le=100, description="대표 점수. MVP 에서는 RADAR video_score 를 그대로 쓴다")
    memo: str = Field("", max_length=500)

    # ── RADAR 확장 (모두 선택) ────────────────────
    radar_id: str | None = Field(None, max_length=100, description="RADAR opportunity_id (= video_id)")
    channel: str | None = Field(None, max_length=100, description="RADAR target_channel.id")
    topic: str | None = Field(None, max_length=200)
    title: str | None = Field(None, max_length=300)
    radar_score: float | None = Field(None, ge=0, le=100, description="RADAR 원본 점수. value 와 같을 수 있다")
    # 결정을 RADAR 원장에 쓸 때 «그때 본 숫자» 를 고정하는 근거. 패키지에서 그대로 옮긴다.
    radar_package_id: str | None = Field(None, max_length=120)
    radar_payload_hash: str | None = Field(None, max_length=120)
    radar_metrics: dict[str, Any] | None = Field(None, description="production_signals.demand 의 video_score·components")
    radar_stage: str | None = Field(None, description="scored | fit_judged | briefed | packaged — RADAR 깔때기의 어느 단계인가")
    decision: Decision | None = None
    decision_reason: str = Field("", max_length=1000)
    source: DataSource = DataSource.MANUAL

    @field_validator("date")
    @classmethod
    def _aware(cls, v: datetime) -> datetime:
        # naive datetime 을 그대로 두면 나중에 정렬·기간 계산에서 비교 예외가 난다.
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)

    @field_validator("memo", "decision_reason", "topic", "title", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    """PUT 은 부분 수정을 허용한다. 보내지 않은 필드는 건드리지 않는다."""

    model_config = ConfigDict(use_enum_values=False)

    date: datetime | None = None
    value: float | None = Field(None, ge=0, le=100)
    memo: str | None = Field(None, max_length=500)
    topic: str | None = Field(None, max_length=200)
    title: str | None = Field(None, max_length=300)
    channel: str | None = Field(None, max_length=100)
    decision: Decision | None = None
    decision_reason: str | None = Field(None, max_length=1000)

    @field_validator("date")
    @classmethod
    def _aware(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


class Candidate(CandidateBase):
    id: str
    created_at: datetime
    updated_at: datetime


class SummaryMetrics(BaseModel):
    average_score: float
    max_score: float
    min_score: float


class DecisionCounts(BaseModel):
    MAKE: int = 0
    WATCH: int = 0
    SKIP: int = 0
    PENDING: int = 0


class Summary(BaseModel):
    """AI System Prompt 에 주입되는 컨텍스트. 명세 4절의 최소 항목을 모두 담는다."""

    period: str
    count: int
    metrics: SummaryMetrics
    trend: str
    decisions: DecisionCounts
    top_topics: list[str]
    channels: dict[str, int] = Field(default_factory=dict)
    source_mix: dict[str, int] = Field(default_factory=dict, description="sample/radar/manual 구성비")
    generated_at: datetime


class CandidateRef(BaseModel):
    """답변 본문의 «#N» 이 가리키는 실제 후보.

    프롬프트에 넣은 번호 목록은 요청마다 새로 매겨진다. 그 대응표를 서버가
    버리면 화면은 «#1 終活 一人…» 을 글자로만 받아 표에서 다시 찾아야 한다.
    표본 168건 중 고유 제목이 91개뿐이라 제목으로는 찾을 수도 없다.
    그래서 번호 ↔ id 대응을 응답과 저장 메시지에 함께 싣는다.

    값(점수·판정·출처)은 답변 시점의 **저장소 값 그대로**다. AI 가 옮겨 적은
    수치와 대조하는 검증용이지, AI 의 해석이 아니다.
    """

    index: int = Field(..., ge=1, description="프롬프트 목록의 번호 (#N)")
    id: str
    title: str | None = None
    channel: str | None = None
    topic: str | None = None
    value: float
    date: str = Field(..., description="YYYY-MM-DD")
    decision: str = Field(..., description="MAKE | WATCH | SKIP | 미정")
    source: str = Field(..., description="sample | radar | manual")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., max_length=8000)
    refs: list[CandidateRef] | None = Field(
        None, description="assistant 메시지가 인용한 후보 대응표. 대화를 다시 열 때 링크를 복원한다."
    )


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = None


class AnswerSource(str, Enum):
    """답변이 무엇에서 나왔는지.

    화면이 모델명 문자열을 보고 추측하지 않도록 전용 필드로 못박는다.
    규칙 기반 결과를 GPT 응답처럼 보여주는 것이 가장 나쁜 표시 방식이다.
    """

    OPENAI = "openai"                      # 실제 GPT 응답
    RULE_BASED = "rule_based"              # 키가 없어 계산 결과로 대체
    ERROR_FALLBACK = "error_fallback"      # 호출 실패로 계산 결과로 대체
    MISSING_PACKAGE = "missing_package"    # 키는 있으나 openai 미설치


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    summary_used: Summary
    candidates_used: int = Field(..., description="프롬프트에 실제로 넣은 후보 수")
    model: str
    answer_source: AnswerSource = Field(
        ..., description="openai 만 실제 GPT 응답이다. 나머지는 대체 응답이다."
    )
    selection_basis: str = Field(
        "keyword", description="decision | keyword | top_score — 후보를 무엇으로 골랐는가"
    )
    candidate_refs: list[CandidateRef] = Field(
        default_factory=list,
        description="프롬프트에 넣은 번호 목록 그대로. reply 의 #N 은 이 목록의 index 다.",
    )


class ConversationCreate(BaseModel):
    title: str | None = Field(None, max_length=200)
    messages: list[ChatMessage] = Field(default_factory=list)


class Conversation(BaseModel):
    id: str
    title: str
    messages: list[ChatMessage]
    created_at: datetime
    updated_at: datetime


class ConversationSummary(BaseModel):
    """목록 조회용. messages 를 뺀 형태임을 타입으로 분명히 한다(과제 9절 A안)."""

    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class DecisionUpdate(BaseModel):
    decision: Decision
    reason: str = Field("", max_length=1000)


class LedgerWrite(BaseModel):
    """RADAR decisions.jsonl 에 썼는지. 안 썼으면 왜 안 썼는지 — 숨기지 않는다."""

    written: bool
    reason: str
    decision_id: str | None = None
    revision: int | None = None
    path: str | None = None


class DecisionResult(Candidate):
    ledger: LedgerWrite


class ErrorResponse(BaseModel):
    error_code: str
    error: str
