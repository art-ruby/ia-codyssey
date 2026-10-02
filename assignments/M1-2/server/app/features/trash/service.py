"""웹 자료 휴지통(T05.03, PRD §8·§9, docs/decisions.md).

- 휴지통 이동은 승인 API의 `action=trash`(reviews.service)가 한다. 여기서는 목록·복원·영구 삭제를 한다.
- 복원은 검토 상태·승인일을 그대로 둔다. 미승인 자료는 미승인으로 돌아온다. 자동 만료는 없다.
- 영구 삭제는 2단계다. ① 자료를 `deleting`으로 바꿔 모든 화면에서 숨기고 작업 ID를 남긴다.
  ② 접수 기록 → URL 예약 → 관련 자료 기록 → 중복 요청 기록(본문 비우기) 순서로 지우고, 마지막에 자료 문서 삭제와
  감사 완료 기록을 한 트랜잭션으로 한다.
  중간에 실패하면 `partial`로 알리고 자료는 `deleting`으로 남는다. 다시 부르면 남은 단계부터 이어서 한다.
- 감사 기록(`audit_events`)에는 작업 ID·상태·단계·시각만 남기고 자료 ID·본문은 남기지 않는다.
"""
from __future__ import annotations

import logging
import uuid

from app.core.context import RequestContext
from app.core.errors import NoChange
from app.core.firestore import NotFound, Store, VersionConflict, now_utc
from app.features.materials import related
from app.features.materials.service import COLLECTION, INTAKE, URL_INDEX, MaterialDeleting, public

log = logging.getLogger("ai_secretary.trash")
AUDIT = "audit_events"
MAX_LISTED = 500


class NotInTrash(NoChange):
    """휴지통에 없는 자료다(409)."""


def _row(doc: dict) -> dict:
    return {**public(doc), "deletion_failed_step": doc.get("deletion_failed_step")}


def list_trash(store: Store, ctx: RequestContext) -> dict:
    """휴지통 자료와 영구 삭제가 끝나지 않은 자료. 휴지통에 넣은 시각의 최신순."""
    docs = []
    for state in ("deleting", "trash"):
        cursor = None
        while len(docs) <= MAX_LISTED:
            page = store.list(ctx, COLLECTION, limit=100, cursor=cursor, descending=True, where={"lifecycle": state})
            docs += page.items
            cursor = page.next_cursor
            if not cursor:
                break
    truncated = len(docs) > MAX_LISTED
    docs.sort(key=lambda d: d.get("id", ""))  # 같은 시각이면 ID 순으로 결과를 고정한다
    docs.sort(key=lambda d: d.get("trashed_at") or "", reverse=True)
    return {"items": [_row(d) for d in docs[:MAX_LISTED]], "truncated": truncated}


def restore(store: Store, ctx: RequestContext, material_id: str, expected_version: int) -> dict:
    current = store.get(ctx, COLLECTION, material_id)
    if current.get("lifecycle") == "deleting":
        raise MaterialDeleting()
    if current.get("lifecycle") != "trash":
        raise NotInTrash()
    updated = store.update(ctx, COLLECTION, material_id, expected_version, {"lifecycle": "active", "trashed_at": None})
    return public(updated)


def _delete_quietly(store: Store, ctx: RequestContext, collection: str, doc_id: str) -> None:
    try:
        store.delete(ctx, collection, doc_id)
    except NotFound:
        pass  # 이전 시도에서 이미 지웠다


def _delete_matching(store: Store, ctx: RequestContext, collection: str, field: str, value: str) -> None:
    """field == value인 문서를 모두 지운다. find는 한 번에 100건까지라 더 없을 때까지 되풀이한다(T05.03 코드 리뷰)."""
    seen: set[str] = set()
    while True:
        found = store.find(ctx, collection, field, value, limit=100)
        if not found:
            return
        ids = {doc["id"] for doc in found}
        if ids <= seen:
            raise RuntimeError(f"{collection} 정리가 진행되지 않습니다")  # 지웠는데 다시 보이면 무한 반복하지 않는다
        seen |= ids
        for doc in found:
            store.delete(ctx, collection, doc["id"])


def _remove_intake(store, ctx, material_id):
    _delete_quietly(store, ctx, INTAKE, material_id)
    _delete_matching(store, ctx, INTAKE, "material_id", material_id)


def _remove_url_index(store, ctx, material_id):
    _delete_matching(store, ctx, URL_INDEX, "material_id", material_id)


def _remove_links(store, ctx, material_id):
    for field in ("a_id", "b_id"):
        _delete_matching(store, ctx, related.LINKS, field, material_id)


def _redact_requests(store, ctx, material_id):
    store.redact_requests(ctx.owner_id, material_id)


# 자료 문서 삭제는 감사 완료 기록과 한 트랜잭션으로 하는 마지막 단계('material')다.
STEPS = (("intake", _remove_intake), ("url_index", _remove_url_index), ("links", _remove_links),
         ("requests", _redact_requests))


def _audit(store: Store, ctx: RequestContext, job_id: str, changes: dict) -> None:
    try:
        store.get(ctx, AUDIT, job_id)
    except NotFound:
        store.create(ctx, AUDIT, {"action": "permanent_delete", "job_id": job_id, "started_at": now_utc(), **changes},
                     doc_id=job_id)
        return
    store.transform(ctx, AUDIT, job_id, lambda _doc: changes)


def _finish(store: Store, ctx: RequestContext, material_id: str, job_id: str, done: list[str]) -> None:
    """자료 문서 삭제와 감사 완료 기록을 함께 한다. 한쪽만 되어 감사가 running에 남거나 재시도가 막히지 않게 한다."""
    finished = {"status": "done", "steps_done": [*done, "material"], "failed_step": None, "finished_at": now_utc()}

    def write(docs: dict):
        audit = finished if docs[(AUDIT, job_id)] else {"action": "permanent_delete", "job_id": job_id,
                                                         "started_at": now_utc(), **finished}
        writes = [(AUDIT, job_id, audit)]
        if docs[(COLLECTION, material_id)] is not None:
            writes.append((COLLECTION, material_id, None))
        return writes, None

    store.run_transaction(ctx, [(COLLECTION, material_id), (AUDIT, job_id)], write)


def permanent_delete(store: Store, ctx: RequestContext, material_id: str, expected_version: int) -> dict:
    current = store.get(ctx, COLLECTION, material_id)  # 남의 자료·없는 자료는 404
    if current.get("lifecycle") not in ("trash", "deleting"):
        raise NotInTrash()
    if current["version"] != expected_version:
        raise VersionConflict(current["version"])
    job_id = current.get("deletion_job_id") or uuid.uuid4().hex
    if current["lifecycle"] == "trash":
        # ① 먼저 숨긴다. 이후 단계가 실패해도 이 자료는 어디에도 보이지 않고 휴지통에서 '삭제 진행 중'으로만 보인다.
        current = store.update(ctx, COLLECTION, material_id, expected_version,
                               {"lifecycle": "deleting", "deletion_job_id": job_id, "deletion_failed_step": None})
    _audit(store, ctx, job_id, {"status": "running", "failed_step": None})

    done = []
    steps = [*STEPS, ("material", lambda s, c, m: _finish(s, c, m, job_id, done))]
    for name, step in steps:
        try:
            step(store, ctx, material_id)
        except Exception:  # noqa: BLE001 — 실패 단계만 알리고 원인 본문은 남기지 않는다
            log.exception("permanent delete job=%s step=%s failed", job_id, name)
            try:
                latest = store.get(ctx, COLLECTION, material_id)
                store.update(ctx, COLLECTION, material_id, latest["version"], {"deletion_failed_step": name})
            except Exception:  # noqa: BLE001 — 표시 실패는 다음 시도에서 다시 남는다
                log.exception("permanent delete job=%s could not mark failure", job_id)
            _audit(store, ctx, job_id, {"status": "partial", "steps_done": done, "failed_step": name,
                                        "finished_at": now_utc()})
            return {"status": "partial", "job_id": job_id, "failed_step": name, "steps_done": done}
        done.append(name)
    log.info("permanent delete job=%s done", job_id)
    return {"status": "deleted", "job_id": job_id}
