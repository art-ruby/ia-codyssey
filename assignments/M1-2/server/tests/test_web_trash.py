"""T05.03 웹 자료 휴지통: 이동(승인 API action=trash)·목록·복원·영구 삭제(2단계·이어서 하기)와 흔적 정리.

영구 삭제 뒤 접수 기록·URL 예약·관련 자료 기록·중복 요청 기록·감사 기록에 자료 ID와 본문이 남지 않는지 본다.
"""

from __future__ import annotations

import itertools
import json
import time

from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
_keys = itertools.count()
SECRET = "삭제되어야 하는 비밀 본문"


def make_client(store=None):
    store = store or MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store)
    return TestClient(app), store


def h(key=None, mode="personal"):
    return {"Authorization": "Bearer t", "X-Data-Mode": mode, "Idempotency-Key": key or f"t{next(_keys)}"}


def new(c, key=None, **body):
    res = c.post("/api/materials", json=body or {"title": "제목", "body": SECRET}, headers=h(key))
    assert res.status_code == 201
    return res.json()


def approve(c, m):
    return c.post("/api/reviews/approve", json={"items": [{"material_id": m["id"], "expected_version": m["version"]}]},
                  headers=h()).json()["results"][0]["material"]


def trash(c, m):
    res = c.post("/api/reviews/approve", headers=h(),
                 json={"items": [{"material_id": m["id"], "expected_version": m["version"], "action": "trash"}]})
    assert res.status_code == 200
    return res.json()["results"][0]


def get(c, m):
    return c.get(f"/api/materials/{m['id']}", headers=h())


def search_ids(c, q=""):
    return [x["id"] for x in c.get("/api/materials/search", params={"q": q}, headers=h()).json()["items"]]


def trash_ids(c):
    res = c.get("/api/trash", headers=h())
    assert res.status_code == 200
    return [x["id"] for x in res.json()["items"]]


def restore(c, m, version=None):
    return c.post(f"/api/trash/{m['id']}/restore", json={"expected_version": version or m["version"]}, headers=h())


def delete(c, m, version=None, confirm="permanent", key=None):
    params = {"expected_version": version or m["version"]}
    if confirm:
        params["confirm"] = confirm
    return c.delete(f"/api/trash/{m['id']}", params=params, headers=h(key))


# ── 이동·목록·복원 ────────────────────────────────────────────────

def test_trash_keeps_review_state_and_hides_from_search():
    c, _ = make_client()
    m = approve(c, new(c))
    assert m["id"] in search_ids(c)

    r = trash(c, m)

    assert r["status"] == "trashed"
    t = r["material"]
    assert t["lifecycle"] == "trash" and t["trashed_at"]
    assert t["review_status"] == "approved" and t["storage_approved_at"] == m["storage_approved_at"]
    assert t["version"] == m["version"] + 1
    assert m["id"] not in search_ids(c) and trash_ids(c) == [m["id"]]


def test_restore_returns_to_search_with_original_approval():
    c, _ = make_client()
    m = approve(c, new(c))
    t = trash(c, m)["material"]
    res = restore(c, t)
    assert res.status_code == 200
    back = res.json()
    assert back["lifecycle"] == "active" and back["trashed_at"] is None
    assert back["review_status"] == "approved" and back["storage_approved_at"] == m["storage_approved_at"]
    assert m["id"] in search_ids(c) and trash_ids(c) == []


def test_restoring_unapproved_material_does_not_approve_it():
    c, _ = make_client()
    m = new(c)
    back = restore(c, trash(c, m)["material"]).json()
    assert back["review_status"] == "unreviewed" and back["storage_approved_at"] is None
    assert m["id"] not in search_ids(c)


def test_trash_of_trashed_material_and_stale_version():
    c, _ = make_client()
    m = new(c)
    t = trash(c, m)["material"]
    again = trash(c, t)
    assert again["status"] == "invalid" and again["reason"] == "trashed"
    assert trash(c, m)["status"] in ("conflict", "invalid")


def test_restore_rules():
    c, _ = make_client()
    m = new(c)
    assert restore(c, m).status_code == 409  # 휴지통에 없는 자료
    t = trash(c, m)["material"]
    assert restore(c, t, version=t["version"] + 5).status_code == 409  # 버전 충돌
    assert c.post("/api/trash/none/restore", json={"expected_version": 1}, headers=h()).status_code == 404


def test_trash_list_is_newest_trashed_first_and_mode_scoped():
    c, _ = make_client()
    first, second = new(c), new(c)
    trash(c, second)
    time.sleep(0.02)  # Windows 시계 해상도에서 휴지통에 넣은 시각이 같아지지 않게 한다
    trash(c, first)
    sample = c.post("/api/materials", json={"title": "표본"}, headers=h(mode="sample")).json()
    c.post("/api/reviews/approve", headers=h(mode="sample"),
           json={"items": [{"material_id": sample["id"], "expected_version": 1, "action": "trash"}]})
    assert trash_ids(c) == [first["id"], second["id"]]


# ── 영구 삭제 ─────────────────────────────────────────────────────

def test_permanent_delete_requires_confirmation_trash_and_version():
    c, _ = make_client()
    m = new(c)
    assert delete(c, m).status_code == 409  # 휴지통에 없음
    t = trash(c, m)["material"]
    assert delete(c, t, confirm=None).status_code == 422
    assert delete(c, t, confirm="yes").status_code == 422
    assert delete(c, t, version=t["version"] + 1).status_code == 409
    assert get(c, m).status_code == 200


def test_permanent_delete_removes_every_trace():
    c, store = make_client()
    create_key = "create-secret"
    m = new(c, key=create_key, url="https://example.com/secret", title="삭제 대상", body=SECRET)
    other = approve(c, new(c, title="정산 시스템 개편 회의", body="정산 API 전환과 OAuth 인증 범위"))
    m = approve(c, m)
    link = c.post("/api/reviews/approve", headers=h(), json={"items": [{
        "material_id": other["id"], "expected_version": other["version"], "action": "link",
        "link": {"target_id": m["id"], "target_version": m["version"], "decision": "unrelated"}}]})
    assert link.json()["results"][0]["status"] == "marked_unrelated"
    t = trash(c, m)["material"]

    res = delete(c, t)

    assert res.status_code == 200 and res.json()["status"] == "deleted"
    assert get(c, m).status_code == 404 and trash_ids(c) == []
    raw = store._docs
    assert m["id"] not in raw["intake_records"]
    assert not any(d.get("material_id") == m["id"] for d in raw["url_index"].values())
    assert not any(m["id"] in (d.get("a_id"), d.get("b_id")) for d in raw["material_links"].values())
    dump = json.dumps(raw["idempotency"], ensure_ascii=False, default=str)
    assert m["id"] not in dump and SECRET not in dump
    audit = list(raw["audit_events"].values())
    assert audit and audit[-1]["status"] == "done" and audit[-1]["action"] == "permanent_delete"
    assert m["id"] not in json.dumps(audit, ensure_ascii=False, default=str)
    # 같은 키로 접수를 다시 보내도 자료가 다시 생기지 않는다(기록은 비웠지만 남아 있다).
    replay = c.post("/api/materials", json={"url": "https://example.com/secret", "title": "삭제 대상", "body": SECRET},
                    headers=h(create_key))
    assert replay.json() == {"deleted": True} and get(c, m).status_code == 404
    # 다른 자료의 기록은 그대로다.
    assert other["id"] in raw["intake_records"] and get(c, other).status_code == 200
    # 같은 URL을 새로 접수하면 중복이 아니라 새 자료다.
    assert c.post("/api/materials", json={"url": "https://example.com/secret"}, headers=h()).status_code == 201


def test_partial_failure_is_not_complete_and_retry_finishes(monkeypatch):
    c, store = make_client()
    m = approve(c, new(c, url="https://example.com/partial", body=SECRET))
    t = trash(c, m)["material"]
    real_delete = store.delete

    def failing(ctx, collection, doc_id):
        if collection == "url_index":
            raise RuntimeError("일시적 저장소 오류")
        return real_delete(ctx, collection, doc_id)

    monkeypatch.setattr(store, "delete", failing)
    res = delete(c, t)
    body = res.json()
    assert res.status_code == 200 and body["status"] == "partial" and body["failed_step"] == "url_index"
    stuck = store.get(ME, "materials", m["id"])
    assert stuck["lifecycle"] == "deleting"
    listed = c.get("/api/trash", headers=h()).json()["items"]
    assert listed[0]["id"] == m["id"] and listed[0]["lifecycle"] == "deleting"
    assert list(store._docs["audit_events"].values())[-1]["status"] == "partial"

    # 삭제 중인 자료는 고치거나 복원하거나 분석할 수 없다.
    assert c.put(f"/api/materials/{m['id']}", json={"expected_version": stuck["version"], "memo": "x"},
                 headers=h()).status_code == 409
    assert restore(c, stuck).status_code == 409
    assert c.post(f"/api/materials/{m['id']}/analyze", json={"expected_version": stuck["version"]},
                  headers=h()).json()["reason"] == "trashed"

    monkeypatch.setattr(store, "delete", real_delete)
    again = delete(c, stuck)
    assert again.json()["status"] == "deleted" and get(c, m).status_code == 404


def test_other_mode_cannot_touch_trash():
    c, _ = make_client()
    t = trash(c, new(c))["material"]
    assert c.post(f"/api/trash/{t['id']}/restore", json={"expected_version": t["version"]},
                  headers=h(mode="sample")).status_code == 404
    assert c.delete(f"/api/trash/{t['id']}", params={"expected_version": t["version"], "confirm": "permanent"},
                    headers=h(mode="sample")).status_code == 404


def test_more_than_100_link_records_are_all_removed():
    # 리뷰 재현: 관계 기록을 방향별 100건까지만 조회해 그 이상은 삭제된 자료 ID가 남았다.
    c, store = make_client()
    t = trash(c, new(c))["material"]
    for i in range(130):
        # 한 방향(a_id)만 120건으로 100건 조회 한도를 넘긴다. 나머지 10건은 반대 방향.
        side = {"a_id": t["id"], "b_id": f"z{i:03d}"} if i < 120 else {"a_id": f"a{i:03d}", "b_id": t["id"]}
        store.create(ME, "material_links", {**side, "state": "unrelated"}, doc_id=f"link{i:03d}")
    assert delete(c, t).json()["status"] == "deleted"
    assert not any(t["id"] in (d.get("a_id"), d.get("b_id")) for d in store._docs["material_links"].values())


def test_failure_when_finishing_deletion_keeps_material_and_audit_consistent(monkeypatch):
    # 리뷰 재현: 자료를 지운 뒤 감사 완료 기록에 실패하면 감사가 running에 남고 재시도는 404였다.
    # 이제 자료 삭제와 감사 완료를 한 트랜잭션으로 해서, 실패하면 자료도 남고 재시도로 끝낼 수 있다.
    c, store = make_client()
    m = approve(c, new(c))
    t = trash(c, m)["material"]
    real = store.run_transaction

    def failing(*_args, **_kwargs):
        raise RuntimeError("마지막 쓰기 실패")

    monkeypatch.setattr(store, "run_transaction", failing)
    res = delete(c, t)
    assert res.json()["status"] == "partial" and res.json()["failed_step"] == "material"
    stuck = store.get(ME, "materials", m["id"])
    assert stuck["lifecycle"] == "deleting"
    assert list(store._docs["audit_events"].values())[-1]["status"] == "partial"

    monkeypatch.setattr(store, "run_transaction", real)
    assert delete(c, stuck).json()["status"] == "deleted"
    assert get(c, m).status_code == 404
    audits = list(store._docs["audit_events"].values())
    assert len(audits) == 1 and audits[0]["status"] == "done" and audits[0]["failed_step"] is None
