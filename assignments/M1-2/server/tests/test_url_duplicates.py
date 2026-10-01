import itertools

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.materials import service
from app.features.materials.url_keys import url_index_id, url_key
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
_keys = itertools.count()


def make_client(owner=OWNER, store=None):
    store = store or MemoryStore()
    app = create_app(load_settings({"OWNER_UID": owner}), verify_token=lambda t: {"uid": owner}, store=store)
    return TestClient(app), store


def h(mode="personal", key=None):
    return {"Authorization": "Bearer t", "X-Data-Mode": mode, "Idempotency-Key": key or f"d{next(_keys)}"}


def post(c, body, **kw):
    return c.post("/api/materials", json=body, headers=h(**kw))


def count(store, collection, ctx=ME):
    return len(store.list(ctx, collection, limit=100).items)


# ── 리뷰에서 재현한 T03.01 결함 ────────────────────────────────────

@pytest.mark.parametrize("url", ["https://example.com:abc/post", "https://example.com:99999/post",
                                 "https://example.com:-1/post"])
def test_invalid_port_is_422_not_500(url):
    c, _ = make_client()
    res = post(c, {"url": url})
    assert res.status_code == 422 and "포트" in res.json()["detail"]


def test_ipv6_key_keeps_brackets():
    assert url_key("https://[::1]/post") == "https://[::1]/post"
    assert url_key("http://[2001:DB8::1]:8080/a") == "http://[2001:db8::1]:8080/a"
    assert url_key("https://[::1]:443/post") == "https://[::1]/post"


def test_rejected_before_write_does_not_lock_the_key():
    c, store = make_client()
    key = "same-key"
    body = {"title": "t", "primary_project_id": "missing"}

    first = c.post("/api/materials", json=body, headers=h(key=key))
    again = c.post("/api/materials", json=body, headers=h(key=key))

    assert first.status_code == again.status_code == 422  # in_progress 409가 아니다
    assert count(store, "materials") == 0


def test_duplicate_409_does_not_lock_the_key():
    c, store = make_client()
    post(c, {"url": "https://a.test/x"})
    key = "dup-key"

    first = c.post("/api/materials", json={"url": "https://a.test/x"}, headers=h(key=key))
    again = c.post("/api/materials", json={"url": "https://a.test/x"}, headers=h(key=key))

    assert first.status_code == again.status_code == 409
    assert again.json()["reason"] == "duplicate_url"


# ── 같은 URL 확인(A18) ────────────────────────────────────────────

def test_same_url_is_reported_with_existing_material_and_nothing_is_created():
    c, store = make_client()
    original = post(c, {"url": "https://Example.com:443/post?id=1", "title": "원래 자료"}).json()

    res = post(c, {"url": "https://example.com/post?id=1"})

    assert res.status_code == 409
    body = res.json()
    assert body["reason"] == "duplicate_url"
    [existing] = body["existing"]
    assert existing["id"] == original["id"] and existing["display_title"] == "원래 자료"
    assert {"registered_at", "review_status", "lifecycle", "version"} <= set(existing)
    assert "body" not in existing and "memo" not in existing
    assert count(store, "materials") == 1 and count(store, "intake_records") == 1


def test_different_query_or_path_is_a_different_url():
    c, _ = make_client()
    post(c, {"url": "https://a.test/post?id=1"})
    assert post(c, {"url": "https://a.test/post?id=2"}).status_code == 201
    assert post(c, {"url": "https://a.test/post?id=1&utm_source=x"}).status_code == 201
    assert post(c, {"url": "https://a.test/Post?id=1"}).status_code == 201


def test_save_separately_creates_new_material_and_intake():
    c, store = make_client()
    post(c, {"url": "https://a.test/x"})

    res = post(c, {"url": "https://a.test/x", "title": "두 번째", "duplicate_action": "save_separately"})

    assert res.status_code == 201 and res.json()["duplicate_action"] == "save_separately"
    assert count(store, "materials") == 2 and count(store, "intake_records") == 2
    # 둘 다 있으면 다음 접수 때 둘 다 후보로 보인다.
    assert len(post(c, {"url": "https://a.test/x"}).json()["existing"]) == 2


def test_add_memo_appends_without_touching_body_and_without_intake():
    c, store = make_client()
    m = post(c, {"url": "https://a.test/x", "body": "원문", "memo": "처음 메모"}).json()

    res = post(c, {"url": "https://a.test/x", "memo": "다시 본 이유", "duplicate_action": "add_memo",
                   "target_id": m["id"], "target_version": m["version"]})

    assert res.status_code == 200
    updated = res.json()
    assert updated["id"] == m["id"] and updated["body"] == "원문" and updated["version"] == 2
    assert updated["memo"].startswith("처음 메모\n\n[") and updated["memo"].endswith("추가] 다시 본 이유")
    assert count(store, "materials") == 1 and count(store, "intake_records") == 1


def test_add_memo_replay_returns_same_200():
    c, _ = make_client()
    m = post(c, {"url": "https://a.test/x"}).json()
    body = {"url": "https://a.test/x", "memo": "m", "duplicate_action": "add_memo",
            "target_id": m["id"], "target_version": 1}
    first = c.post("/api/materials", json=body, headers=h(key="memo-key"))
    again = c.post("/api/materials", json=body, headers=h(key="memo-key"))
    assert first.status_code == again.status_code == 200 and first.json() == again.json()
    assert again.json()["memo"].count("추가] m") == 1  # 두 번 덧붙지 않는다


def test_add_memo_rules():
    c, store = make_client()
    m = post(c, {"url": "https://a.test/x"}).json()
    other = post(c, {"url": "https://b.test/y"}).json()
    base = {"url": "https://a.test/x", "memo": "m", "duplicate_action": "add_memo"}

    assert post(c, {**base, "target_id": other["id"], "target_version": 1}).status_code == 422  # 다른 URL
    assert post(c, {**base, "target_id": "missing", "target_version": 1}).status_code == 422
    assert post(c, {**base, "memo": "", "target_id": m["id"], "target_version": 1}).status_code == 422
    assert post(c, {"title": "t", "duplicate_action": "save_separately"}).status_code == 422  # URL 없음
    stale = post(c, {**base, "target_id": m["id"], "target_version": 5})
    assert stale.status_code == 409 and stale.json()["current_version"] == 1

    store.update(ME, "materials", m["id"], 1, {"memo": "가" * 1995})
    too_long = post(c, {**base, "memo": "나" * 10, "target_id": m["id"], "target_version": 2})
    assert too_long.status_code == 422 and "2000자" in too_long.json()["detail"]


def test_trashed_existing_is_listed_but_memo_is_blocked():
    c, store = make_client()
    m = post(c, {"url": "https://a.test/x"}).json()
    store.update(ME, "materials", m["id"], 1, {"lifecycle": "trash", "trashed_at": "2026-10-02T00:00:00+00:00"})

    dup = post(c, {"url": "https://a.test/x"})
    assert dup.status_code == 409 and dup.json()["existing"][0]["lifecycle"] == "trash"
    memo = post(c, {"url": "https://a.test/x", "memo": "m", "duplicate_action": "add_memo",
                    "target_id": m["id"], "target_version": 2})
    assert memo.status_code == 409 and memo.json()["reason"] == "trashed"
    assert post(c, {"url": "https://a.test/x", "duplicate_action": "save_separately"}).status_code == 201


def test_other_owner_and_other_mode_are_not_candidates():
    store = MemoryStore()
    c1, _ = make_client(OWNER, store)
    c2, _ = make_client("owner-2", store)
    post(c1, {"url": "https://a.test/x"})

    assert post(c2, {"url": "https://a.test/x"}).status_code == 201
    assert post(c1, {"url": "https://a.test/x"}, mode="sample").status_code == 201
    assert post(c1, {"url": "https://a.test/x"}).status_code == 409


# ── 동시 등록과 예약 ──────────────────────────────────────────────

def test_concurrent_first_registration_creates_only_one(monkeypatch):
    store = MemoryStore()
    data = {"url": "https://a.test/x"}
    # 다른 요청이 먼저 저장했지만, 이 요청의 첫 검색에는 아직 보이지 않았던 상황을 재현한다.
    service.create_material(store, ME, data)
    real_find = store.find
    calls = {"n": 0}

    def find_misses_first_time(ctx, collection, field, value, limit=10):
        calls["n"] += 1
        return [] if calls["n"] == 1 else real_find(ctx, collection, field, value, limit)

    monkeypatch.setattr(store, "find", find_misses_first_time)
    with pytest.raises(service.DuplicateUrl):
        service.create_material(store, ME, data)
    assert count(store, "materials") == 1 and count(store, "intake_records") == 1


def test_stale_reservation_is_cleared_after_material_is_gone():
    store = MemoryStore()
    key = url_key("https://a.test/x")
    store.create(ME, "url_index", {"url_key": key, "material_id": "deleted"},
                 doc_id=url_index_id(OWNER, "personal", key))

    status, created = service.create_material(store, ME, {"url": "https://a.test/x"})

    assert status == 201
    reservation = store.get(ME, "url_index", url_index_id(OWNER, "personal", key))
    assert reservation["material_id"] == created["id"]


def test_first_registration_reserves_url_but_save_separately_does_not():
    store = MemoryStore()
    service.create_material(store, ME, {"url": "https://a.test/x"})
    service.create_material(store, ME, {"url": "https://a.test/x", "duplicate_action": "save_separately"})
    assert count(store, "url_index") == 1
