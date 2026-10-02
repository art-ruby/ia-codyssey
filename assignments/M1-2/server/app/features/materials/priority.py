"""오늘·AI 동향의 우선순위(PRD §5, T04.04, docs/decisions.md).

- 최종 중요도 = 사용자 값(`user_importance`). 없으면 지금 내용 기준으로 끝난 AI 제안(`ai_importance`).
  분석이 끝나지 않았거나(`done` 아님) 결과 뒤에 내용을 고쳤으면(`analysis_outdated`) AI 값을 쓰지 않는다.
- 정렬: 최종 중요도(높음→보통→낮음) → 대응 필요 우선 → 최신 접수 → ID. 최종 중요도가 없으면 판단 보류 묶음.
- 최종 중요도는 계산값이라 Firestore 정렬을 쓸 수 없다. 현재 모드의 자료를 **최신 접수부터** 최대 `MAX_SCAN`건 읽어
  Python에서 정렬한다. 한도를 넘으면 오래된 자료가 빠지고 `truncated`로 알린다.
- 사용자가 일부러 '판단 보류'로 둔 것과 아직 고르지 않은 것은 구분하지 못한다(둘 다 null, MVP 한계).
"""
from __future__ import annotations

from app.core.context import RequestContext
from app.core.firestore import Store
from app.features.materials.service import COLLECTION, analysis_outdated, is_kept, public

MAX_SCAN = 500
_RANK = {"high": 0, "medium": 1, "low": 2}


def _ai_usable(doc: dict) -> bool:
    return doc.get("analysis_status") == "done" and not analysis_outdated(doc)


def final_importance(doc: dict) -> tuple[str | None, str | None]:
    """(중요도, 출처 user|ai). 둘 다 없으면 (None, None) = 판단 보류."""
    if doc.get("user_importance") in _RANK:
        return doc["user_importance"], "user"
    if _ai_usable(doc) and doc.get("ai_importance") in _RANK:
        return doc["ai_importance"], "ai"
    return None, None


def needs_action(doc: dict) -> bool | None:
    """대응 필요 여부. 쓸 수 있는 AI 결과가 없거나 T04.04 이전 결과면 None(미확인)."""
    value = doc.get("ai_needs_action") if _ai_usable(doc) else None
    return value if isinstance(value, bool) else None


def reason(doc: dict) -> str | None:
    """화면에 붙일 이유. 사용자가 정했으면 사용자가 쓴 저장 이유를 먼저, 없으면 AI 중요 이유."""
    _, source = final_importance(doc)
    ai_reason = doc.get("ai_importance_reason") if _ai_usable(doc) else None
    if source == "user":
        return doc.get("save_reason") or ai_reason
    return ai_reason


def _newest_first(docs: list[dict]) -> list[dict]:
    ordered = sorted(docs, key=lambda d: d.get("id", ""))
    return sorted(ordered, key=lambda d: d.get("registered_at") or "", reverse=True)  # 안정 정렬로 ID 순을 유지


def prioritize(docs: list[dict]) -> tuple[list[dict], list[dict]]:
    """(중요도가 있는 자료의 정렬 결과, 판단 보류 자료의 최신순)."""
    graded = [d for d in docs if final_importance(d)[0]]
    pending = [d for d in docs if not final_importance(d)[0]]
    graded = sorted(_newest_first(graded), key=lambda d: 0 if needs_action(d) else 1)
    graded = sorted(graded, key=lambda d: _RANK[final_importance(d)[0]])
    return graded, _newest_first(pending)


def _annotated(doc: dict) -> dict:
    importance, source = final_importance(doc)
    return {**public(doc), "final_importance": importance, "importance_source": source,
            "needs_action": needs_action(doc), "reason": reason(doc)}


def priority_view(store: Store, ctx: RequestContext) -> dict:
    docs, cursor, truncated = [], None, False
    while True:
        # 최신순으로 읽어야 한도를 넘었을 때 최근 자료가 아니라 오래된 자료가 빠진다.
        page = store.list(ctx, COLLECTION, limit=100, cursor=cursor, descending=True)
        docs += page.items
        cursor = page.next_cursor
        if len(docs) >= MAX_SCAN:
            truncated = bool(cursor) or len(docs) > MAX_SCAN
            docs = docs[:MAX_SCAN]
            break
        if not cursor:
            break
    active = [d for d in docs if d.get("lifecycle") == "active"]
    graded, pending = prioritize(active)
    return {
        "items": [_annotated(d) for d in graded],
        "pending": [_annotated(d) for d in pending],
        "counts": {
            "unreviewed": sum(1 for d in active if d.get("review_status") == "unreviewed"),
            "kept": sum(1 for d in active if is_kept(d)),
        },
        "scanned": len(docs),
        "truncated": truncated,
    }
