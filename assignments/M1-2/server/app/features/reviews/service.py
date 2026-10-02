"""검토 요청·보관 승인(T03.03, PRD §8·§13). docs/api-contract.md의 '검토·승인' 절이 계약이다.

- 자료 한 건은 버전 확인을 포함한 쓰기 한 번(`store.update`)으로 처리한다. 묶음 전체를 한 번에
  성공·실패시키지 않고 항목별 결과를 돌려준다. 일부가 충돌해도 응답은 200이다.
- 이미 승인된 자료는 수정값이 없는 새 요청일 때 `already_approved`로 돌려주고 다시 쓰지 않는다.
  수정값이 있는 새 요청은 `conflict`로 알려 입력을 버리지 않는다. 같은 키의 재전송은 처음 응답을
  그대로 받는다(requests.py).
- 웹 자료(URL·텍스트)는 보관 승인과 동시에 보관 완료다(materials.service.is_kept).
"""
from __future__ import annotations

from typing import Any

from app.core.context import RequestContext
from app.core.firestore import NotFound, Store, VersionConflict, now_utc
from app.features.materials import service as materials
from app.features.materials.service import COLLECTION, InvalidProjectReference, NoContent, public


def _result(material_id: str, status: str, **extra) -> dict:
    return {"material_id": material_id, "status": status, **extra}


def _load(store: Store, ctx: RequestContext, material_id: str) -> dict | None:
    try:
        return store.get(ctx, COLLECTION, material_id)  # 다른 소유자·모드의 자료도 없는 것과 같다
    except NotFound:
        return None


def _write(store: Store, ctx: RequestContext, item: dict, changes: dict, status: str) -> dict:
    material_id = item["material_id"]
    try:
        updated = store.update(ctx, COLLECTION, material_id, item["expected_version"], changes)
    except VersionConflict as exc:
        return _result(material_id, "conflict", current_version=exc.current_version)
    except NotFound:
        return _result(material_id, "not_found")
    return _result(material_id, status, material=public(updated))


def _approve_one(store: Store, ctx: RequestContext, item: dict) -> dict:
    material_id = item["material_id"]
    current = _load(store, ctx, material_id)
    if current is None:
        return _result(material_id, "not_found")
    if current.get("review_status") == "approved":
        # 같은 키의 재전송은 run_idempotent가 처리한다. 새 요청에 수정값이 있으면
        # 승인된 자료를 다시 쓰지 않으므로 충돌을 알려 사용자 입력을 보존하게 한다.
        if item.get("changes"):
            return _result(material_id, "conflict", current_version=current["version"])
        return _result(material_id, "already_approved", current_version=current["version"],
                       material=public(current))
    if current.get("lifecycle") != "active":
        return _result(material_id, "invalid", reason="trashed")
    if current["version"] != item["expected_version"]:
        return _result(material_id, "conflict", current_version=current["version"])
    try:
        changes = materials.prepare_changes(store, ctx, current, item.get("changes") or {})
    except InvalidProjectReference:
        return _result(material_id, "invalid", reason="project")
    except NoContent:
        return _result(material_id, "invalid", reason="no_content")
    changes.update({"review_status": "approved", "storage_approved_at": now_utc()})
    return _write(store, ctx, item, changes, "approved")


def approve(store: Store, ctx: RequestContext, items: list[dict[str, Any]]) -> dict:
    """항목 순서대로 처리한 결과. 지금은 action=keep만 온다(schemas.py가 거른다)."""
    results = [_approve_one(store, ctx, item) for item in items]
    return {"results": results, "approved_count": sum(r["status"] == "approved" for r in results)}


def _request_one(store: Store, ctx: RequestContext, item: dict, requested: bool) -> dict:
    material_id = item["material_id"]
    current = _load(store, ctx, material_id)
    if current is None:
        return _result(material_id, "not_found")
    if current.get("lifecycle") != "active":
        return _result(material_id, "invalid", reason="trashed")
    if current.get("review_status") == "approved":
        return _result(material_id, "invalid", reason="approved")
    if bool(current.get("review_requested")) == requested:
        # 이미 원하는 상태다. 새 키로 다시 보내도 요청 시각을 바꾸지 않는다.
        return _result(material_id, "unchanged", current_version=current["version"], material=public(current))
    if current["version"] != item["expected_version"]:
        return _result(material_id, "conflict", current_version=current["version"])
    changes = {"review_requested": requested, "review_requested_at": now_utc() if requested else None}
    return _write(store, ctx, item, changes, "updated")


def request_review(store: Store, ctx: RequestContext, items: list[dict[str, Any]], requested: bool) -> dict:
    """받은 자료를 승인 요청 목록으로 옮기거나(requested=True) 되돌린다."""
    results = [_request_one(store, ctx, item, requested) for item in items]
    return {"results": results, "updated_count": sum(r["status"] == "updated" for r in results)}
