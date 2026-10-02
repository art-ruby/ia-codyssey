"""검토 요청·보관 승인(T03.03, PRD §8·§13). docs/api-contract.md의 '검토·승인' 절이 계약이다.

- 자료 한 건은 버전 확인을 포함한 쓰기 한 번(`store.update`)으로 처리한다. 묶음 전체를 한 번에
  성공·실패시키지 않고 항목별 결과를 돌려준다. 일부가 충돌해도 응답은 200이다.
- 이미 승인된 자료는 수정값이 없는 새 요청일 때 `already_approved`로 돌려주고 다시 쓰지 않는다.
  수정값이 있는 새 요청은 `conflict`로 알려 입력을 버리지 않는다. 같은 키의 재전송은 처음 응답을
  그대로 받는다(requests.py).
- 웹 자료(URL·텍스트)는 보관 승인과 동시에 보관 완료다(materials.service.is_kept).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.core.context import RequestContext
from app.core.errors import NoChange
from app.core.firestore import NotFound, Store, VersionConflict, now_utc
from app.features.materials import related
from app.features.materials import service as materials
from app.features.materials.service import COLLECTION, SEOUL, InvalidProjectReference, NoContent, public


class PastRevisitDate(NoChange):
    """새 나중에 보기 요청에 과거 날짜를 지정했다(422)."""


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
    # 나중에 보기 자료도 바로 승인할 수 있다. 승인하면 다시 볼 날짜는 의미가 없어 비운다.
    changes.update({"review_status": "approved", "storage_approved_at": now_utc(), "revisit_on": None})
    return _write(store, ctx, item, changes, "approved")


_LINK_STATUS = {"link": ("linked", "linked"), "unrelated": ("unrelated", "marked_unrelated"),
                "unlink": ("unlinked", "unlinked")}


def _link_one(store: Store, ctx: RequestContext, item: dict) -> dict:
    """관련 자료 판단(T05.02). 두 자료의 상태·버전 확인과 짝 기록 쓰기를 한 트랜잭션에서 한다.

    확인과 저장 사이에 자료가 고쳐지거나 휴지통으로 가면 오래된 버전으로 저장하지 않는다(T05.02 코드 리뷰).
    자료 자체의 버전은 바꾸지 않는다.
    """
    material_id, choice = item["material_id"], item["link"]
    target_id, decision = choice["target_id"], choice["decision"]
    link_id = related.link_id(material_id, target_id)
    names = related.project_names(store, ctx)  # 근거 표시용 이름. 판단의 정합성과 무관하므로 트랜잭션 밖에서 읽는다
    decided_at = now_utc()
    keys = {"source": (COLLECTION, material_id), "target": (COLLECTION, target_id), "link": (related.LINKS, link_id)}

    def check(docs: dict):
        source, target, existing = (docs[keys[k]] for k in ("source", "target", "link"))
        if source is None or target is None:
            return [], _result(material_id, "not_found", side="source" if source is None else "target")
        if source.get("lifecycle") != "active":
            return [], _result(material_id, "invalid", reason="trashed")
        if source["version"] != item["expected_version"]:
            return [], _result(material_id, "conflict", side="source", current_version=source["version"])
        if decision == "unlink":
            # 해제는 상대가 휴지통에 갔어도 할 수 있어야 하므로 상대 상태·버전을 묻지 않는다.
            if not existing or existing.get("state") != "linked":
                return [], _result(material_id, "invalid", reason="not_linked")
        else:
            if not materials.is_kept(target):
                return [], _result(material_id, "invalid", reason="target_unavailable")
            if related.same_url(source, target):
                return [], _result(material_id, "invalid", reason="same_url")  # 같은 URL은 중복 처리(T03.02)에서
            if target["version"] != choice["target_version"]:
                return [], _result(material_id, "conflict", side="target", current_version=target["version"])
        evidence, _, _ = related.evidence_for(source, target, names)
        low, high = sorted([material_id, target_id])
        record = {"a_id": low, "b_id": high, "source_id": material_id, "target_id": target_id,
                  "source_version": source["version"], "target_version": target["version"],
                  "state": _LINK_STATUS[decision][0], "evidence": evidence, "decided_at": decided_at}
        return [(*keys["link"], record)], None

    failure, saved = store.run_transaction(ctx, list(keys.values()), check)
    if failure:
        return failure
    link = saved[keys["link"]]
    fields = ("a_id", "b_id", "source_id", "target_id", "source_version", "target_version", "state", "evidence",
              "decided_at", "version")
    return _result(material_id, _LINK_STATUS[decision][1], link={k: link[k] for k in fields})


def approve(store: Store, ctx: RequestContext, items: list[dict[str, Any]]) -> dict:
    """항목 순서대로 처리한 결과. action: keep(보관 승인) | link(관련 자료 판단). trash는 schemas.py가 거른다."""
    results = [_link_one(store, ctx, item) if item.get("action") == "link" else _approve_one(store, ctx, item)
               for item in items]
    return {"results": results, "approved_count": sum(r["status"] == "approved" for r in results),
            "linked_count": sum(r["status"] in ("linked", "marked_unrelated", "unlinked") for r in results)}


def _request_one(store: Store, ctx: RequestContext, item: dict, requested: bool) -> dict:
    material_id = item["material_id"]
    current = _load(store, ctx, material_id)
    if current is None:
        return _result(material_id, "not_found")
    if current.get("lifecycle") != "active":
        return _result(material_id, "invalid", reason="trashed")
    if current.get("review_status") == "approved":
        return _result(material_id, "invalid", reason="approved")
    if requested and current.get("review_status") == "later":
        # 나중에 보기 자료를 검토로 옮기면 미검토로 되돌린다(두 목록이 겹치지 않게).
        if current["version"] != item["expected_version"]:
            return _result(material_id, "conflict", current_version=current["version"])
        return _write(store, ctx, item, {"review_status": "unreviewed", "revisit_on": None,
                                         "review_requested": True, "review_requested_at": now_utc()}, "updated")
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


def _later_one(store: Store, ctx: RequestContext, item: dict, later: bool, revisit_on: str | None) -> dict:
    material_id = item["material_id"]
    current = _load(store, ctx, material_id)
    if current is None:
        return _result(material_id, "not_found")
    if current.get("lifecycle") != "active":
        return _result(material_id, "invalid", reason="trashed")
    if current.get("review_status") == "approved":
        return _result(material_id, "invalid", reason="approved")
    is_later = current.get("review_status") == "later"
    if is_later == later and (not later or current.get("revisit_on") == revisit_on):
        return _result(material_id, "unchanged", current_version=current["version"], material=public(current))
    if current["version"] != item["expected_version"]:
        return _result(material_id, "conflict", current_version=current["version"])
    if later:
        changes = {"review_status": "later", "revisit_on": revisit_on,
                   "review_requested": False, "review_requested_at": None}
    else:
        changes = {"review_status": "unreviewed", "revisit_on": None}
    return _write(store, ctx, item, changes, "updated")


def set_later(store: Store, ctx: RequestContext, items: list[dict[str, Any]], later: bool,
              revisit_on: str | None) -> dict:
    """나중에 보기로 남기거나(다시 볼 날짜 선택) 미검토로 되돌린다. 날짜가 지나도 자동으로 바꾸지 않는다."""
    # 중복 요청의 완료 결과를 먼저 재생할 수 있도록 날짜 검사는 run_idempotent의 handler 안에서 한다.
    if later and revisit_on and date.fromisoformat(revisit_on) < datetime.now(SEOUL).date():
        raise PastRevisitDate()
    results = [_later_one(store, ctx, item, later, revisit_on) for item in items]
    return {"results": results, "updated_count": sum(r["status"] == "updated" for r in results)}

