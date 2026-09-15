"""후보 데이터 CRUD + Summary + 소스 import.

라우트 선언 순서 주의: /api/data/summary 를 /api/data/{id} 보다 **먼저**
선언해야 한다. 뒤에 두면 FastAPI 가 'summary' 를 id 로 읽어 404 가 난다.
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..adapters.sources import build_source
from ..config import Settings
from ..deps import config_dep, store_dep
from ..models.schemas import (
    Candidate,
    CandidateCreate,
    CandidateUpdate,
    Decision,
    DecisionResult,
    DecisionUpdate,
    LedgerWrite,
    Summary,
)
from ..repositories.store import Store
from ..services.decisions_ledger import DecisionsLedger
from ..services.summary import build_summary

router = APIRouter(prefix="/api/data", tags=["data"])


def _to_candidate(record: dict[str, Any]) -> Candidate:
    return Candidate.model_validate(record)


def _dump(model) -> dict[str, Any]:
    """Enum 을 값으로 펴서 저장한다. Firestore 는 Enum 을 그대로 못 받는다."""
    return model.model_dump(mode="json", exclude_none=False)


# ── Summary (반드시 {id} 보다 먼저) ─────────────────
@router.get("/summary", response_model=Summary, summary="AI 프롬프트 주입용 요약")
def get_summary(store: Store = Depends(store_dep)) -> Summary:
    return build_summary(store.list_candidates())


@router.post("/import", summary="어댑터에서 후보 일괄 적재 (sample 또는 radar)")
def import_candidates(
    source: Literal["sample", "radar"] = Query("sample"),
    replace: bool = Query(False, description="true 면 같은 소스의 기존 레코드를 지우고 넣는다"),
    store: Store = Depends(store_dep),
    settings: Settings = Depends(config_dep),
) -> dict[str, Any]:
    adapter = build_source(source, settings)
    records = adapter.load()
    if not records:
        return {
            "ok": False,
            "imported": 0,
            "source": adapter.describe(),
            "error": "해당 소스에서 읽을 후보가 없습니다. RADAR 는 계산된 점수가 있어야 합니다.",
        }

    removed = 0
    if replace:
        for existing in store.list_candidates():
            existing_source = getattr(existing.get("source"), "value", existing.get("source"))
            if existing_source == source:
                store.delete_candidate(existing["id"])
                removed += 1

    imported = store.bulk_create_candidates(records)
    return {"ok": True, "imported": imported, "removed": removed, "source": adapter.describe()}


@router.get("/sources", summary="사용 가능한 데이터 소스 상태")
def list_sources(settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    return {
        "sources": [
            build_source("sample", settings).describe(),
            build_source("radar", settings).describe(),
        ]
    }


# ── CRUD ───────────────────────────────────────────
@router.get("", response_model=list[Candidate], summary="후보 목록")
def list_candidates(
    channel: str | None = Query(None),
    decision: Decision | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    store: Store = Depends(store_dep),
) -> list[Candidate]:
    rows = store.list_candidates()

    if channel:
        rows = [r for r in rows if (r.get("channel") or "") == channel]
    if decision is not None:
        rows = [
            r for r in rows
            if getattr(r.get("decision"), "value", r.get("decision")) == decision.value
        ]
    if source:
        rows = [
            r for r in rows
            if getattr(r.get("source"), "value", r.get("source")) == source
        ]

    rows.sort(key=lambda r: str(r.get("date")), reverse=True)
    return [_to_candidate(r) for r in rows[:limit]]


@router.post("", response_model=Candidate, status_code=status.HTTP_201_CREATED, summary="후보 추가")
def create_candidate(
    payload: CandidateCreate, store: Store = Depends(store_dep)
) -> Candidate:
    return _to_candidate(store.create_candidate(_dump(payload)))


@router.get("/{candidate_id}", response_model=Candidate, summary="후보 단건 조회")
def get_candidate(candidate_id: str, store: Store = Depends(store_dep)) -> Candidate:
    found = store.get_candidate(candidate_id)
    if found is None:
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")
    return _to_candidate(found)


@router.put("/{candidate_id}", response_model=Candidate, summary="후보 수정")
def update_candidate(
    candidate_id: str, payload: CandidateUpdate, store: Store = Depends(store_dep)
) -> Candidate:
    patch = payload.model_dump(mode="json", exclude_unset=True, exclude_none=True)
    if not patch:
        raise HTTPException(status_code=400, detail="수정할 필드가 없습니다")
    updated = store.update_candidate(candidate_id, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")
    return _to_candidate(updated)


@router.post("/pool/refresh", summary="RADAR 후보 풀 새로고침 (analysis·fit·briefs·outbox → candidate_pool.json)")
def refresh_pool(top: int = Query(20, ge=0, le=200), settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    """RADAR 런타임에서 후보 풀을 다시 내보낸다. 그 뒤 import?source=radar 가 이 풀을 읽는다."""
    from ..services.radar_pool import refresh

    if not settings.radar_root:
        raise HTTPException(status_code=503, detail="RADAR_ROOT 가 없습니다.")
    res = refresh(settings.radar_root, python=settings.radar_python, top=top)
    if not res.get("ok"):
        raise HTTPException(status_code=502, detail="RADAR 풀 내보내기 실패: " + str(res.get("why")))
    return res


@router.patch("/{candidate_id}/decision", response_model=DecisionResult, summary="MAKE/WATCH/SKIP 변경")
def set_decision(
    candidate_id: str,
    payload: DecisionUpdate,
    store: Store = Depends(store_dep),
    settings: Settings = Depends(config_dep),
) -> DecisionResult:
    """판단만 바꾸는 전용 경로.

    전체 PUT 으로도 가능하지만, 화면의 결정 버튼이 다른 필드를 실수로
    덮어쓰지 않도록 좁은 입구를 따로 둔다.

    실측(radar) 후보의 결정은 RADAR `data/decisions.jsonl` 에도 append 한다 — 그 파일이
    결정의 단일 정본이고, RADAR 의 패키저와 성과 대조가 그것을 읽는다. 썼는지·왜 안 썼는지는
    `ledger` 로 그대로 돌려준다. 표본/수동 후보는 실측 원장을 더럽히지 않도록 쓰지 않는다.
    """
    updated = store.update_candidate(
        candidate_id, {"decision": payload.decision.value, "decision_reason": payload.reason}
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")

    ledger = DecisionsLedger(settings.radar_root, enabled=settings.radar_decisions_write)
    # 판정(assessment)이 있으면 요약을 결정 줄에 함께 남긴다 — 판단 근거 추적 + AutoMaker 전달.
    signals: dict[str, Any] = {}
    if updated.get("radar_id") and updated.get("channel"):
        from ..services.assessment import AssessmentStore, ledger_signals
        doc = AssessmentStore(settings.radar_root).load(str(updated["channel"]), str(updated["radar_id"]))
        if doc:
            signals = ledger_signals(doc)
            signals["user_decision_vs_suggested"] = {
                "suggested": (doc.get("decision") or {}).get("suggested"), "user": payload.decision.value,
            }
    try:
        written, reason, rec = ledger.append(updated, payload.decision.value, payload.reason, signals=signals)
    except OSError as exc:  # 잠금·권한 문제는 결정 자체를 막지 않되 사실대로 알린다
        written, reason, rec = False, f"RADAR 원장 쓰기 실패: {exc}", None
    result = LedgerWrite(
        written=written,
        reason=reason,
        decision_id=(rec or {}).get("decision_id"),
        revision=(rec or {}).get("revision"),
        path=str(ledger.path) if written else None,
    )
    return DecisionResult(**_to_candidate(updated).model_dump(), ledger=result)


@router.delete("/{candidate_id}", summary="후보 삭제")
def delete_candidate(candidate_id: str, store: Store = Depends(store_dep)) -> dict[str, Any]:
    if not store.delete_candidate(candidate_id):
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")
    return {"ok": True, "deleted": candidate_id}
