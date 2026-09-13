"""채널 운영 판단 — Channel Identity · Episode Assessment · Fit 재판정.

  GET  /api/identity/{channel}            현재 Identity(제안/승인)
  POST /api/identity/{channel}/propose    AI 제안 (프로필+DNA+MAKE 이력+성과)
  POST /api/identity/{channel}/approve    사람 승인 (수정본 동봉 가능) → identity_version +1
  GET  /api/assessment/{candidate_id}     저장된 판정
  POST /api/assessment/{candidate_id}     판정 실행 (force 로 AI 해석 재호출)
  POST /api/fit/{candidate_id}/reevaluate RADAR channel_fit.judge(force) 호출 — DA 가 계산하지 않는다
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..config import Settings
from ..deps import config_dep, store_dep
from ..repositories.store import Store
from ..services import assessment as assess
from ..services import identity as ident
from ..services.decisions_ledger import DecisionsLedger
from ..services.fit_state import evaluate as evaluate_fit
from ..services.fit_state import reevaluate_in_radar
from ..services.radar_data import RadarData

router = APIRouter(tags=["judgment"])


def _radar(settings: Settings) -> RadarData:
    data = RadarData(settings.radar_root)
    if not data.available:
        raise HTTPException(status_code=503, detail="RADAR_ROOT 가 없어 채널 운영 판단을 할 수 없습니다.")
    return data


def _candidate(candidate_id: str, store: Store) -> dict[str, Any]:
    c = store.get_candidate(candidate_id)
    if c is None:
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")
    if getattr(c.get("source"), "value", c.get("source")) != "radar":
        raise HTTPException(status_code=409, detail="실측(radar) 후보만 채널 운영 판단 대상입니다.")
    return c


# ── Identity ────────────────────────────────────────────────────────────────
@router.get("/api/identity/{channel_id}", summary="Channel Identity 조회")
def get_identity(channel_id: str, settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    data = _radar(settings)
    doc = ident.IdentityStore(settings.radar_root).load(channel_id)
    profile = data.profile(channel_id)
    return {"channel_id": channel_id, "profile": profile, "identity": doc,
            "path": str(ident.IdentityStore(settings.radar_root).path(channel_id))}


@router.post("/api/identity/{channel_id}/propose", summary="Channel Identity AI 제안")
def propose_identity(channel_id: str, settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    data = _radar(settings)
    try:
        doc = ident.propose(channel_id, settings, data, DecisionsLedger(settings.radar_root, enabled=False),
                            ident.IdentityStore(settings.radar_root))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — 모델·파싱 실패를 그대로
        raise HTTPException(status_code=502, detail=f"Identity 제안 실패: {exc}") from exc
    return {"ok": True, "identity": doc}


@router.post("/api/identity/{channel_id}/approve", summary="Channel Identity 승인 (사람)")
def approve_identity(channel_id: str, payload: dict[str, Any] | None = None,
                     settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    _radar(settings)
    try:
        doc = ident.approve(channel_id, ident.IdentityStore(settings.radar_root), edits=(payload or {}).get("edits"))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "identity": doc}


# ── Assessment ──────────────────────────────────────────────────────────────
@router.get("/api/assessment/{candidate_id}", summary="저장된 Episode 판정")
def get_assessment(candidate_id: str, store: Store = Depends(store_dep),
                   settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    _radar(settings)
    c = _candidate(candidate_id, store)
    doc = assess.AssessmentStore(settings.radar_root).load(str(c["channel"]), str(c["radar_id"]))
    fit = evaluate_fit(RadarData(settings.radar_root), str(c["radar_id"]), str(c["channel"]))
    return {"candidate_id": candidate_id, "assessment": doc, "fit_now": fit}


@router.post("/api/assessment/{candidate_id}", summary="Episode 판정 실행")
def run_assessment(candidate_id: str, payload: dict[str, Any] | None = None, store: Store = Depends(store_dep),
                   settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    data = _radar(settings)
    c = _candidate(candidate_id, store)
    try:
        doc = assess.run(c, settings=settings, data=data, ledger=DecisionsLedger(settings.radar_root, enabled=False),
                         identity_store=ident.IdentityStore(settings.radar_root),
                         store=assess.AssessmentStore(settings.radar_root), force=bool((payload or {}).get("force")))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"판정 실패: {exc}") from exc
    return {"ok": True, "assessment": doc}


# ── Fit 재판정 (RADAR 호출) ─────────────────────────────────────────────────
@router.post("/api/fit/{candidate_id}/reevaluate", summary="RADAR channel_fit 재판정 (현재 프로필 기준)")
def reevaluate(candidate_id: str, store: Store = Depends(store_dep),
               settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    data = _radar(settings)
    c = _candidate(candidate_id, store)
    before = evaluate_fit(data, str(c["radar_id"]), str(c["channel"]))
    if before["state"] == "VALID":
        return {"ok": True, "skipped": True, "reason": "이미 현재 프로필 기준 판정이 있다 — RADAR 를 다시 부르지 않는다.", "fit": before}
    res = reevaluate_in_radar(settings.radar_root, str(c["radar_id"]), str(c["channel"]), python=settings.radar_python)
    if not res.get("ok"):
        raise HTTPException(status_code=502, detail="RADAR 재판정 실패: " + str(res.get("why")))
    after = evaluate_fit(data, str(c["radar_id"]), str(c["channel"]))
    return {"ok": True, "skipped": False, "before": before["state"], "fit": after, "radar": res}


@router.post("/api/identity/{channel_id}/persona", summary="Identity 에서 파생한 채널 수준 페르소나 (AutoMaker 채널 설정용)")
def channel_persona(channel_id: str, settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    data = _radar(settings)
    try:
        doc = ident.channel_persona(channel_id, settings, data, ident.IdentityStore(settings.radar_root))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"채널 페르소나 생성 실패: {exc}") from exc
    return {"ok": True, "persona": doc}


@router.post("/api/brief/{candidate_id}", summary="RADAR 제작 브리프 생성 (comments → analyze → production_brief.build)")
def make_brief(candidate_id: str, payload: dict[str, Any] | None = None, store: Store = Depends(store_dep),
               settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    """브리프는 RADAR 가 만든다. DA 는 순서를 지켜 부르고, 끝나면 판정을 다시 돌려 production 게이트를 갱신한다."""
    from ..services.radar_brief import build_in_radar

    data = _radar(settings)
    c = _candidate(candidate_id, store)
    vid, cid = str(c["radar_id"]), str(c["channel"])
    fit = evaluate_fit(data, vid, cid)
    if fit["state"] != "VALID":
        raise HTTPException(status_code=409, detail=f"적합성이 {fit['state']} — 먼저 RADAR 재판정을 하세요. 브리프는 판정 위에 조립됩니다.")
    if fit.get("channel_relevance") == "LOW":
        raise HTTPException(status_code=409, detail="채널 관련성 LOW — 브리프를 만들지 않습니다(RADAR 규칙).")
    res = build_in_radar(settings.radar_root, vid, cid, python=settings.radar_python,
                         with_comments=bool((payload or {}).get("with_comments", True)))
    if not res.get("ok"):
        raise HTTPException(status_code=409 if res.get("gate") else 502, detail="RADAR 브리프 실패: " + str(res.get("why")) + f" · steps={res.get('steps')}")
    # 브리프가 생겼으니 판정을 다시 — production 게이트가 열린다. 저장소 후보의 단계도 briefed 로.
    store.update_candidate(candidate_id, {"radar_stage": "briefed"})
    doc = assess.run(store.get_candidate(candidate_id), settings=settings, data=data,
                     ledger=DecisionsLedger(settings.radar_root, enabled=False),
                     identity_store=ident.IdentityStore(settings.radar_root), store=assess.AssessmentStore(settings.radar_root))
    return {"ok": True, "brief": {k: res.get(k) for k in ("path", "chars", "fit", "steps")}, "assessment": doc}
