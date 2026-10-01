from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.auth import get_context
from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import InvalidCursor, MemoryStore, NotFound, VersionConflict
from app.core.requests import (IdempotencyConflict, IdempotencyKeyRequired, Result,
                               run_idempotent)
from app.main import create_app, get_store

OWNER, OTHER = "owner-1", "owner-2"
ME = RequestContext(OWNER, "personal", "key-1")
ME_SAMPLE = RequestContext(OWNER, "sample", "key-1")
STRANGER = RequestContext(OTHER, "personal", "key-1")


# ── 소유자·모드 격리와 버전 ─────────────────────────────────────────

def test_create_sets_system_fields_from_context_not_input():
    store = MemoryStore()

    doc = store.create(ME, "projects", {"name": "AI", "owner_id": OTHER, "mode": "sample", "version": 9})

    assert (doc["owner_id"], doc["mode"], doc["version"]) == (OWNER, "personal", 1)
    assert doc["created_at"].endswith("+00:00")  # UTC
    assert store.get(ME, "projects", doc["id"])["name"] == "AI"


@pytest.mark.parametrize("ctx", [STRANGER, ME_SAMPLE])
def test_other_owner_or_mode_cannot_see_or_change(ctx):
    store = MemoryStore()
    doc = store.create(ME, "materials", {"title": "x"})

    with pytest.raises(NotFound):
        store.get(ctx, "materials", doc["id"])
    with pytest.raises(NotFound):
        store.update(ctx, "materials", doc["id"], 1, {"title": "hacked"})
    with pytest.raises(NotFound):
        store.delete(ctx, "materials", doc["id"])
    assert store.list(ctx, "materials").items == []
    assert store.get(ME, "materials", doc["id"])["title"] == "x"


def test_update_requires_current_version():
    store = MemoryStore()
    doc = store.create(ME, "materials", {"title": "v1"})

    updated = store.update(ME, "materials", doc["id"], 1, {"title": "v2", "version": 99})
    assert updated["version"] == 2 and updated["title"] == "v2"

    with pytest.raises(VersionConflict) as err:
        store.update(ME, "materials", doc["id"], 1, {"title": "stale"})
    assert err.value.current_version == 2
    assert store.get(ME, "materials", doc["id"])["title"] == "v2"


def test_list_pages_with_cursor_and_isolation():
    store = MemoryStore()
    ids = [store.create(ME, "data", {"n": i})["id"] for i in range(5)]
    store.create(STRANGER, "data", {"n": 99})
    store.create(ME_SAMPLE, "data", {"n": 98})

    seen, cursor = [], None
    while True:
        page = store.list(ME, "data", limit=2, cursor=cursor)
        seen += [d["id"] for d in page.items]
        if not page.next_cursor:
            break
        cursor = page.next_cursor

    assert sorted(seen) == sorted(ids) and len(seen) == 5


@pytest.mark.parametrize("bad_id", ["", "a/b", "a/b/c", ".", "..", "__x__", "x" * 1501])
def test_malformed_doc_id_is_not_found(bad_id):
    store = MemoryStore()

    for call in (lambda: store.get(ME, "materials", bad_id),
                 lambda: store.update(ME, "materials", bad_id, 1, {}),
                 lambda: store.delete(ME, "materials", bad_id)):
        with pytest.raises(NotFound):
            call()
    with pytest.raises(ValueError):
        store.create(ME, "materials", {}, doc_id=bad_id)


def test_bad_cursor_is_rejected():
    with pytest.raises(InvalidCursor):
        MemoryStore().list(ME, "data", cursor="not-a-cursor!!")


# ── 중복 요청 처리 ─────────────────────────────────────────────────

def make_create(store, ctx, calls):
    def handler():
        calls.append(1)
        return Result(201, store.create(ctx, "materials", {"title": "t"}))
    return handler


def test_same_key_same_body_runs_once_and_replays():
    store, calls = MemoryStore(), []
    first = run_idempotent(store, ME, "POST", "/api/materials", {"title": "t"}, make_create(store, ME, calls))
    second = run_idempotent(store, ME, "POST", "/api/materials", {"title": "t"}, make_create(store, ME, calls))

    assert len(calls) == 1
    assert second.replayed and second.body == first.body and second.status_code == 201
    assert len(store.list(ME, "materials").items) == 1


def test_same_key_different_body_is_conflict():
    store, calls = MemoryStore(), []
    run_idempotent(store, ME, "POST", "/api/materials", {"title": "t"}, make_create(store, ME, calls))

    with pytest.raises(IdempotencyConflict) as err:
        run_idempotent(store, ME, "POST", "/api/materials", {"title": "other"}, make_create(store, ME, calls))
    assert err.value.reason == "different_request" and len(calls) == 1


def test_same_key_in_other_mode_counts_as_different_request():
    store, calls = MemoryStore(), []
    run_idempotent(store, ME, "POST", "/api/materials", {"title": "t"}, make_create(store, ME, calls))

    with pytest.raises(IdempotencyConflict):
        run_idempotent(store, ME_SAMPLE, "POST", "/api/materials", {"title": "t"},
                       make_create(store, ME_SAMPLE, calls))


def test_keys_are_scoped_per_owner():
    store, calls = MemoryStore(), []
    run_idempotent(store, ME, "POST", "/p", {}, make_create(store, ME, calls))
    run_idempotent(store, STRANGER, "POST", "/p", {}, make_create(store, STRANGER, calls))

    assert len(calls) == 2


@pytest.mark.parametrize("key", [None, "", "   ", "k" * 201])
def test_missing_or_invalid_key_is_rejected(key):
    with pytest.raises(IdempotencyKeyRequired):
        run_idempotent(MemoryStore(), RequestContext(OWNER, "personal", key), "POST", "/p", {},
                       lambda: Result(200, {}))


def test_failed_handler_releases_key_for_retry():
    store, calls = MemoryStore(), []

    def failing():
        calls.append(1)
        raise ValueError("validation failed")

    with pytest.raises(ValueError):
        run_idempotent(store, ME, "POST", "/p", {}, failing)
    result = run_idempotent(store, ME, "POST", "/p", {}, lambda: Result(201, {"ok": True}))

    assert result.status_code == 201 and not result.replayed and len(calls) == 1


def test_in_progress_request_is_conflict_not_rerun():
    store = MemoryStore()
    seen = []

    def outer():
        with pytest.raises(IdempotencyConflict) as err:
            run_idempotent(store, ME, "POST", "/p", {}, lambda: Result(200, {"inner": True}))
        seen.append(err.value.reason)
        return Result(201, {"outer": True})

    run_idempotent(store, ME, "POST", "/p", {}, outer)
    assert seen == ["in_progress"]


def test_record_survives_restart_and_expires():
    store, calls = MemoryStore(), []
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    run_idempotent(store, ME, "POST", "/p", {}, make_create(store, ME, calls), now=lambda: t0)

    # '재시작': 같은 저장소로 새 호출. 하루 안이면 다시 실행하지 않는다.
    later = run_idempotent(store, ME, "POST", "/p", {}, make_create(store, ME, calls),
                           now=lambda: t0 + timedelta(hours=23))
    assert later.replayed and len(calls) == 1

    expired = run_idempotent(store, ME, "POST", "/p", {}, make_create(store, ME, calls),
                             now=lambda: t0 + timedelta(days=1, seconds=1))
    assert not expired.replayed and len(calls) == 2


def test_expired_key_is_reclaimed_in_one_step():
    store = MemoryStore()
    old = {"fingerprint": "a", "state": "processing", "expire_at": "2026-10-01T00:00:00+00:00"}
    new = {"fingerprint": "b", "state": "processing", "expire_at": "2026-10-03T00:00:00+00:00"}
    store.claim_key("r", old, "2026-09-30T00:00:00+00:00")

    assert store.claim_key("r", new, "2026-09-30T12:00:00+00:00")["fingerprint"] == "a"  # 만료 전
    assert store.claim_key("r", new, "2026-10-02T00:00:00+00:00") is None                  # 만료 후 차지
    # 직후 같은 만료 키로 온 두 번째 요청은 새 기록을 보고, 덮어쓰지 못한다.
    assert store.claim_key("r", old, "2026-10-02T00:00:00+00:00")["fingerprint"] == "b"


# ── HTTP 응답 코드 연결 ────────────────────────────────────────────

def http_client():
    store = MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}),
                     verify_token=lambda token: {"uid": OWNER}, store=store)

    # 시험용 라우트: 실제 자료 API(T02.04~)가 같은 방식으로 저장소를 쓴다.
    @app.post("/test/items", status_code=201)
    def create_item(body: dict, ctx: RequestContext = Depends(get_context), s=Depends(get_store)):
        return run_idempotent(s, ctx, "POST", "/test/items", body,
                              lambda: Result(201, s.create(ctx, "materials", body))).body

    @app.get("/test/items/{item_id}")
    def read_item(item_id: str, ctx: RequestContext = Depends(get_context), s=Depends(get_store)):
        return s.get(ctx, "materials", item_id)

    @app.put("/test/items/{item_id}")
    def update_item(item_id: str, body: dict, ctx: RequestContext = Depends(get_context), s=Depends(get_store)):
        return s.update(ctx, "materials", item_id, body.pop("expected_version"), body)

    return TestClient(app), store


def headers(mode="personal", key=None):
    h = {"Authorization": "Bearer t", "X-Data-Mode": mode}
    if key:
        h["Idempotency-Key"] = key
    return h


def test_http_codes_for_storage_rules():
    client, store = http_client()

    created = client.post("/test/items", json={"title": "a"}, headers=headers(key="k1"))
    again = client.post("/test/items", json={"title": "a"}, headers=headers(key="k1"))
    assert created.status_code == 201 and again.json()["id"] == created.json()["id"]
    assert len(store.list(ME, "materials").items) == 1

    assert client.post("/test/items", json={"title": "b"}, headers=headers(key="k1")).status_code == 409
    assert client.post("/test/items", json={"title": "a"}, headers=headers()).status_code == 422

    item = created.json()["id"]
    assert client.get(f"/test/items/{item}", headers=headers(mode="sample")).status_code == 404
    assert client.get("/test/items/missing", headers=headers()).status_code == 404
    assert client.get("/test/items/__x__", headers=headers()).status_code == 404

    ok = client.put(f"/test/items/{item}", json={"expected_version": 1, "title": "a2"}, headers=headers())
    stale = client.put(f"/test/items/{item}", json={"expected_version": 1, "title": "a3"}, headers=headers())
    assert ok.status_code == 200 and ok.json()["version"] == 2
    assert stale.status_code == 409 and stale.json()["current_version"] == 2
    assert "X-Request-ID" in ok.headers
