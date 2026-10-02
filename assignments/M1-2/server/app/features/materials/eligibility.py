"""검색·채팅에 전달할 자료의 공통 필터(T05.04, PRD §9.1·§11, A13, docs/decisions.md).

- `material_is_chat_eligible`: AI 문맥(채팅 근거·관련 후보 전달)에 보낼 수 있는가. 소유자·모드·보관 승인·보관 완료·
  활성·AI 분석 제외를 한곳에서 판정한다. 빠진 이유는 `exclusion_reason`으로 알 수 있다.
- `library_visible`: 보관함에 보일 수 있는가. AI 분석 제외 자료는 보관함에는 보이지만 AI 문맥에는 보내지 않는다.
  Open Decision 5가 정해지기 전까지는 제외 자료의 제목·날짜 같은 메타데이터도 보내지 않는다(엄격한 쪽).
- `refresh_and_filter`: 질문할 때마다 자료를 다시 읽어 거른다. 이전 대화에 있던 자료가 그사이 삭제·휴지통·
  미승인·제외 상태가 됐으면 다시 보내지 않는다(PRD §11). 새 질문과 과거 대화 문맥 모두 이 함수를 쓴다(T07).
- `ai_payload`: AI에 보낼 필드는 사용자가 쓴 내용과 접수일로 고정한다(날짜 질문에 답하려고 접수일을 포함).
  소유자·모드·자료 ID·AI 결과·내부 필드는 보내지 않는다.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from app.core.context import RequestContext
from app.core.firestore import NotFound, Store
from app.features.materials.service import COLLECTION, is_kept

AI_CONTEXT_FIELDS = ("title", "description", "body", "save_reason", "memo", "url", "registered_at")


@dataclass(frozen=True)
class Selection:
    allowed: list[dict]
    excluded: dict[str, int] = field(default_factory=dict)  # 이유별 건수(화면의 '근거에서 뺀 자료' 안내용)


def _owned(doc: dict | None, ctx: RequestContext) -> bool:
    return bool(doc) and doc.get("owner_id") == ctx.owner_id and doc.get("mode") == ctx.mode


def exclusion_reason(doc: dict | None, ctx: RequestContext) -> str | None:
    """AI 문맥에서 빠지는 이유. 보낼 수 있으면 None. 이유는 앞의 조건부터 하나만 고른다."""
    if not _owned(doc, ctx):
        return "not_found"  # 없거나 다른 소유자·모드: 존재 여부도 드러내지 않는다
    if doc.get("lifecycle") != "active":
        return "trashed"  # 휴지통·영구 삭제 진행 중
    if doc.get("review_status") != "approved":
        return "unapproved"  # 미검토·나중에 보기
    if not is_kept(doc):
        return "not_kept"  # 보관 완료가 아님(확장 단계의 사본 대기 등)
    if doc.get("ai_excluded"):
        return "ai_excluded"
    return None


def material_is_chat_eligible(doc: dict | None, ctx: RequestContext) -> bool:
    return exclusion_reason(doc, ctx) is None


def library_visible(doc: dict | None, ctx: RequestContext) -> bool:
    """보관함 목록·검색에 보일 수 있는가. AI 분석 제외 여부와 무관하다."""
    return _owned(doc, ctx) and is_kept(doc)


def select_ai_context(docs: list[dict], ctx: RequestContext) -> Selection:
    """이미 읽은 자료에서 AI 문맥에 보낼 것만 고른다. 순서를 지키고 같은 자료는 한 번만."""
    allowed, excluded, seen = [], Counter(), set()
    for doc in docs:
        key = doc.get("id")
        if key in seen:
            continue
        seen.add(key)
        reason = exclusion_reason(doc, ctx)
        if reason:
            excluded[reason] += 1
        else:
            allowed.append(doc)
    return Selection(allowed, dict(excluded))


def refresh_and_filter(store: Store, ctx: RequestContext, material_ids: list[str]) -> Selection:
    """자료 ID 목록을 최신 문서로 다시 읽어 거른다(질문 직전에 부른다)."""
    docs = []
    missing = 0
    for material_id in dict.fromkeys(material_ids):
        try:
            docs.append(store.get(ctx, COLLECTION, material_id))
        except NotFound:
            missing += 1
    picked = select_ai_context(docs, ctx)
    if missing:
        picked.excluded["not_found"] = picked.excluded.get("not_found", 0) + missing
    return picked


def ai_payload(doc: dict) -> dict:
    """AI에 보낼 자료 내용. 값이 있는 사용자 입력 필드와 접수일만."""
    return {name: doc[name] for name in AI_CONTEXT_FIELDS if doc.get(name)}
