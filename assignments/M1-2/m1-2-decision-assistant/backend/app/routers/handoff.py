"""MAKE 확정 후보 → AutoMaker 인계. RADAR 의 automaker_intake 를 부른다.

v1 은 자기 handoff/ 디렉터리에 JSON 을 남기는 것까지였다. 그 파일을 읽는 쪽은
어디에도 없었고(2026-09-11 감사 §G-9), RADAR→AutoMaker 에는 이미 hash·revision·
provenance 를 갖춘 계약이 있었다. 그래서 파일을 남기는 대신 **그 계약을 부른다.**

여기서 AutoMaker 에 직접 쓰지 않는다. RADAR `package()` 가 저널(outbox.sqlite3)에
남기고 `send()` 가 루프백 HTTP 로 넘긴다. 받을지 말지는 AutoMaker 가 정한다.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..config import Settings
from ..deps import config_dep, store_dep
from ..repositories.store import Store
from ..services.persona import generate_draft
from ..services.radar_bridge import RadarBridge

router = APIRouter(prefix="/api/handoff", tags=["handoff"])


def _bridge(settings: Settings) -> RadarBridge:
    return RadarBridge(settings.radar_root, automaker_url=settings.automaker_url, python=settings.radar_python)


@router.get("", summary="DA 결정이 실려 AutoMaker 로 간 패키지 목록 (RADAR outbox 저널에서)")
def get_handoffs(settings: Settings = Depends(config_dep)) -> dict[str, Any]:
    bridge = _bridge(settings)
    records = bridge.sent_by_assistant()
    return {
        "count": len(records),
        "source": "radar outbox.sqlite3 (producer=decision-assistant)",
        "automaker_url": bridge.automaker_url,
        "bridge_available": bridge.available,
        "records": records,
    }


@router.post("/{candidate_id}", summary="MAKE 후보를 RADAR 패키지로 만들어 AutoMaker 에 보낸다")
def create_handoff(
    candidate_id: str,
    store: Store = Depends(store_dep),
    settings: Settings = Depends(config_dep),
) -> dict[str, Any]:
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")

    source = getattr(candidate.get("source"), "value", candidate.get("source"))
    if source != "radar":
        # 표본/수동 후보는 RADAR 에 브리프·근거 파일이 없다. 가짜 패키지를 만들지 않는다.
        raise HTTPException(
            status_code=409,
            detail=f"[{source}] 후보는 RADAR 실측이 아니라 AutoMaker 로 보낼 수 없습니다. "
                   "실측(radar) 후보만 RADAR 패키지가 됩니다.",
        )
    decision = getattr(candidate.get("decision"), "value", candidate.get("decision"))
    if decision != "MAKE":
        # 상태를 대신 바꿔주지 않는다 — 확정은 사용자의 행위여야 한다(명세 6절).
        raise HTTPException(status_code=409, detail="MAKE 로 확정된 후보만 인계할 수 있습니다.")
    video_id = str(candidate.get("radar_id") or "")
    channel_id = str(candidate.get("channel") or "")
    if not video_id or not channel_id:
        raise HTTPException(status_code=409, detail="radar_id 또는 channel 이 없어 RADAR 패키지를 만들 수 없습니다.")

    bridge = _bridge(settings)
    if not bridge.available:
        raise HTTPException(status_code=503, detail="RADAR_ROOT 가 없거나 automaker_intake 를 찾을 수 없습니다.")
    result = bridge.package_and_send(video_id, channel_id)
    if not result.get("ok"):
        # 관문 거부(원장이 MAKE 아님)·AutoMaker 거부·RADAR 예외 — 문구를 그대로 낸다.
        raise HTTPException(status_code=409 if result.get("gate") else 502, detail=result.get("error", "인계 실패"))

    # 받기만 하고 끝나면 AutoMaker 의 project 는 예전 revision 을 본다. 이미 연결된 프로젝트면
    # 이번 revision 을 반영(불변 보관)까지 한다. 처음 받는 패키지는 사람이 채널을 골라야 하므로 두고, 링크만 준다.
    result["link_result"] = bridge.link_revision(result["package_id"], int(result["revision"]))
    return {"ok": True, "candidate_id": candidate_id, **result}


@router.post("/{candidate_id}/link", summary="AutoMaker 에 이미 연결된 프로젝트에 최신 revision 반영")
def link_latest(
    candidate_id: str,
    store: Store = Depends(store_dep),
    settings: Settings = Depends(config_dep),
) -> dict[str, Any]:
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")
    bridge = _bridge(settings)
    pkg = next((r for r in bridge.sent_by_assistant() if r.get("radar_id") == candidate.get("radar_id")), None)
    if not pkg:
        raise HTTPException(status_code=409, detail="이 후보로 보낸 RADAR 패키지가 없습니다. 먼저 인계하세요.")
    res = bridge.link_revision(pkg["package_id"], int(pkg["revision"]))
    if not res.get("ok"):
        raise HTTPException(status_code=409 if res.get("needs_human") else 502, detail=res.get("error"))
    return {"ok": True, "package_id": pkg["package_id"], "revision": pkg["revision"], **res}


def _package_for(candidate: dict[str, Any], bridge: RadarBridge) -> dict[str, Any]:
    pkg = next((r for r in bridge.sent_by_assistant() if r.get("radar_id") == candidate.get("radar_id")), None)
    if not pkg:
        raise HTTPException(status_code=409, detail="이 후보로 보낸 RADAR 패키지가 없습니다. 먼저 인계하세요.")
    return pkg


@router.get("/{candidate_id}/persona", summary="AutoMaker 채널 페르소나 상태(초안·승인)")
def persona_state(
    candidate_id: str, store: Store = Depends(store_dep), settings: Settings = Depends(config_dep)
) -> dict[str, Any]:
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")
    bridge = _bridge(settings)
    pkg = _package_for(candidate, bridge)
    return {"package_id": pkg["package_id"], **bridge.persona_state(pkg["package_id"])}


@router.post("/{candidate_id}/persona-draft", summary="AutoMaker 프롬프트를 DA 모델로 돌려 페르소나 초안을 AutoMaker 에 저장")
def persona_draft(
    candidate_id: str, store: Store = Depends(store_dep), settings: Settings = Depends(config_dep)
) -> dict[str, Any]:
    """키는 DA 에만 있다. AutoMaker 의 프롬프트를 받아(draft-input) 여기서 생성하고 돌려준다(save-draft).
    승인은 하지 않는다 — 그것은 사람의 행위다."""
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")
    bridge = _bridge(settings)
    pkg = _package_for(candidate, bridge)
    src = bridge.persona_draft_input(pkg["package_id"])
    if not src.get("ok"):
        raise HTTPException(status_code=409, detail="AutoMaker 초안 입력 거부: " + str(src.get("error")))
    try:
        draft, model = generate_draft(src["prompt"], settings)
    except Exception as exc:  # noqa: BLE001 — 모델·파싱 실패를 그대로 보여준다
        raise HTTPException(status_code=502, detail=f"페르소나 초안 생성 실패: {exc}") from exc
    saved = bridge.persona_save_draft(pkg["package_id"], int(src["revision"]), draft)
    if not saved.get("ok"):
        raise HTTPException(status_code=409, detail="AutoMaker 초안 저장 거부: " + str(saved.get("error")))
    state = bridge.persona_state(pkg["package_id"])
    return {"ok": True, "package_id": pkg["package_id"], "revision": src["revision"], "model": model,
            "draft": saved.get("draft"), "draft_hash": state.get("draft_hash"),
            "link": bridge.intake_link(pkg["package_id"])}


@router.post("/{candidate_id}/persona-approve", summary="페르소나 초안 승인 (사람의 확정)")
def persona_approve(
    candidate_id: str, payload: dict[str, Any], store: Store = Depends(store_dep), settings: Settings = Depends(config_dep)
) -> dict[str, Any]:
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="후보를 찾을 수 없습니다")
    draft_hash = str(payload.get("draft_hash") or "")
    if not draft_hash:
        raise HTTPException(status_code=422, detail="draft_hash 가 필요합니다 — 검토한 초안 그대로인지 AutoMaker 가 확인합니다.")
    bridge = _bridge(settings)
    pkg = _package_for(candidate, bridge)
    res = bridge.persona_approve(pkg["package_id"], draft_hash)
    if not res.get("ok"):
        raise HTTPException(status_code=409, detail="AutoMaker 승인 거부: " + str(res.get("error")))
    genre = ((res.get("project") or {}).get("genre") or {})
    return {"ok": True, "package_id": pkg["package_id"], "persona_status": genre.get("persona_status"),
            "channel_persona": genre.get("channelPersona"), "radar_draft": genre.get("radar_draft")}
