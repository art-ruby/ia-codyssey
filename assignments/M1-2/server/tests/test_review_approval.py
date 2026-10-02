import itertools

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.materials.service import is_kept
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
_keys = itertools.count()


def make_client(owner=OWNER, store=None, uid=None):
    store = store or MemoryStore()
    app = create_app(load_settings({"OWNER_UID": owner}), verify_token=lambda t: {"uid": uid or owner}, store=store)
    return TestClient(app), store


def h(mode="personal", key=None):
    return {"Authorization": "Bearer t", "X-Data-Mode": mode, "Idempotency-Key": key or f"r{next(_keys)}"}


def new(c, **body):
    res = c.post("/api/materials", json=body or {"title": "t"}, headers=h())
    assert res.status_code == 201
    return res.json()


def approve(c, items, key=None, mode="personal"):
    return c.post("/api/reviews/approve", json={"items": items}, headers=h(mode, key))


def keep(m, **changes):
    item = {"material_id": m["id"], "expected_version": m["version"], "action": "keep"}
    if changes:
        item["changes"] = changes
    return item


def ask_review(c, materials, requested=True, key=None):
    items = [{"material_id": m["id"], "expected_version": m["version"]} for m in materials]
    return c.post("/api/reviews/request", json={"items": items, "requested": requested}, headers=h(key=key))


def view(c, name, mode="personal"):
    res = c.get(f"/api/materials?view={name}", headers=h(mode))
    assert res.status_code == 200
    return [m["id"] for m in res.json()["items"]]


def by_id(res):
    return {r["material_id"]: r for r in res.json()["results"]}


def make_project(c, name="AI 비서"):
    res = c.post("/api/projects", json={"name": name}, headers=h())
    assert res.status_code == 201
    return res.json()


# ── 받은 자료와 승인 요청 목록 ─────────────────────────────────────

def test_new_material_has_review_fields():
    c, _ = make_client()
    m = new(c, url="https://a.test/x")
    assert m["review_status"] == "unreviewed" and m["review_requested"] is False
    assert m["review_requested_at"] is None and m["user_importance"] is None
    assert m["storage_approved_at"] is None


def test_inbox_and_review_lists_are_separate():
    c, _ = make_client()
    a, b, d = new(c, title="a"), new(c, title="b"), new(c, title="d")

    res = ask_review(c, [a, b])

    assert res.status_code == 200 and res.json()["updated_count"] == 2
    assert all(r["material"]["review_requested_at"] for r in res.json()["results"])
    assert view(c, "inbox") == [d["id"]]
    assert set(view(c, "review")) == {a["id"], b["id"]}
    assert len(view(c, "all")) == 3


def test_withdraw_returns_material_to_inbox():
    c, _ = make_client()
    a = new(c)
    moved = by_id(ask_review(c, [a]))[a["id"]]["material"]

    back = by_id(ask_review(c, [moved], requested=False))[a["id"]]

    assert back["status"] == "updated" and back["material"]["review_requested_at"] is None
    assert view(c, "inbox") == [a["id"]] and view(c, "review") == []


def test_request_again_with_new_key_is_unchanged():
    c, store = make_client()
    a = new(c)
    first = by_id(ask_review(c, [a]))[a["id"]]["material"]

    again = by_id(ask_review(c, [a]))[a["id"]]  # 예전 버전·새 키

    assert again["status"] == "unchanged" and again["current_version"] == first["version"]
    assert store.get(ME, "materials", a["id"])["review_requested_at"] == first["review_requested_at"]


def test_invalid_list_view_is_422():
    c, _ = make_client()
    assert c.get("/api/materials?view=kept", headers=h()).status_code == 422


def test_list_view_paginates_inside_the_view():
    c, _ = make_client()
    ms = [new(c, title=str(i)) for i in range(5)]
    ask_review(c, ms[:3])
    seen, cursor = [], None
    while True:
        url = "/api/materials?view=review&limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = c.get(url, headers=h()).json()
        seen += [m["id"] for m in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert sorted(seen) == sorted(m["id"] for m in ms[:3])


# ── 보관 승인 ─────────────────────────────────────────────────────

def test_only_selected_items_are_approved_with_user_changes():
    c, store = make_client()
    p = make_project(c)
    a, b, excluded = new(c, url="https://a.test/1"), new(c, title="b"), new(c, title="제외")
    ask_review(c, [a, b, excluded])
    a, b = (store.get(ME, "materials", m["id"]) for m in (a, b))

    res = approve(c, [keep(a, title="고친 제목", user_importance="high", primary_project_id=p["id"]),
                      keep(b, user_importance="low")])

    assert res.status_code == 200 and res.json()["approved_count"] == 2
    got = c.get(f"/api/materials/{a['id']}", headers=h()).json()  # 새로 불러와도 유지
    assert got["title"] == "고친 제목" and got["user_importance"] == "high"
    assert got["primary_project_id"] == p["id"] and got["review_status"] == "approved"
    assert got["storage_approved_at"] and is_kept(got)
    assert got["analysis_status"] == "awaiting_start"  # 제목이 생겨 분석 대기
    assert store.get(ME, "materials", excluded["id"])["review_status"] == "unreviewed"
    assert view(c, "review") == [excluded["id"]] and view(c, "inbox") == []


def test_approve_without_changes_keeps_fields_and_can_clear_importance():
    c, _ = make_client()
    m = new(c, title="t", user_importance="medium")
    ok = by_id(approve(c, [keep(m)]))[m["id"]]
    assert ok["status"] == "approved" and ok["material"]["user_importance"] == "medium"

    m2 = new(c, title="t2", user_importance="high")
    cleared = by_id(approve(c, [keep(m2, user_importance=None)]))[m2["id"]]
    assert cleared["material"]["user_importance"] is None  # 판단 보류


def test_inbox_item_can_be_approved_directly():
    c, _ = make_client()
    m = new(c)
    assert by_id(approve(c, [keep(m)]))[m["id"]]["status"] == "approved"
    assert view(c, "inbox") == []


def test_partial_conflict_is_not_reported_as_success():
    c, store = make_client()
    a, b = new(c, title="a"), new(c, title="b")
    store.update(ME, "materials", b["id"], 1, {"memo": "다른 곳에서 수정"})

    res = approve(c, [keep(a), keep(b)])

    assert res.status_code == 200
    results = by_id(res)
    assert results[a["id"]]["status"] == "approved"
    assert results[b["id"]] == {"material_id": b["id"], "status": "conflict", "current_version": 2}
    assert res.json()["approved_count"] == 1
    assert store.get(ME, "materials", b["id"])["review_status"] == "unreviewed"


def test_same_request_replayed_does_not_change_approval_time():
    c, store = make_client()
    m = new(c)
    first = approve(c, [keep(m, user_importance="high")], key="approve-1")
    stamp = store.get(ME, "materials", m["id"])["storage_approved_at"]

    again = approve(c, [keep(m, user_importance="high")], key="approve-1")

    assert again.status_code == 200 and again.json() == first.json()
    doc = store.get(ME, "materials", m["id"])
    assert doc["storage_approved_at"] == stamp and doc["version"] == 2


def test_resent_with_new_key_reports_already_approved():
    c, store = make_client()
    m = new(c)
    approve(c, [keep(m)])
    stamp = store.get(ME, "materials", m["id"])["storage_approved_at"]

    # 처리 중 끊겨 같은 키가 막힌 뒤 새 키로 다시 보낸 경우: 예전 버전이지만 충돌이 아니다.
    res = by_id(approve(c, [keep(m)]))[m["id"]]

    assert res["status"] == "already_approved" and res["current_version"] == 2
    doc = store.get(ME, "materials", m["id"])
    assert doc["storage_approved_at"] == stamp and doc["user_importance"] is None and doc["version"] == 2


def test_new_approval_with_changes_after_another_approval_reports_conflict():
    c, store = make_client()
    m = new(c, title="original")
    approve(c, [keep(m)])
    stamp = store.get(ME, "materials", m["id"])["storage_approved_at"]

    result = by_id(approve(c, [keep(m, title="my unsaved edit")]))[m["id"]]

    assert result == {"material_id": m["id"], "status": "conflict", "current_version": 2}
    current = store.get(ME, "materials", m["id"])
    assert current["title"] == "original"
    assert current["storage_approved_at"] == stamp


def test_other_owner_and_other_mode_items_are_not_found_only():
    store = MemoryStore()
    c1, _ = make_client(OWNER, store)
    c2, _ = make_client("owner-2", store)
    mine, theirs = new(c1), new(c2)
    sample = c1.post("/api/materials", json={"title": "s"}, headers=h("sample")).json()

    res = by_id(approve(c1, [keep(mine), keep(theirs), keep(sample)]))

    assert res[mine["id"]]["status"] == "approved"
    assert res[theirs["id"]] == {"material_id": theirs["id"], "status": "not_found"}
    assert res[sample["id"]]["status"] == "not_found"
    other_ctx = RequestContext("owner-2", "personal", None)
    assert store.get(other_ctx, "materials", theirs["id"])["review_status"] == "unreviewed"
    assert by_id(ask_review(c1, [theirs]))[theirs["id"]]["status"] == "not_found"


def test_trashed_material_is_rejected():
    c, store = make_client()
    m = new(c)
    store.update(ME, "materials", m["id"], 1, {"lifecycle": "trash", "trashed_at": "2026-10-02T00:00:00+00:00"})
    stale = {**m, "version": 2}

    assert by_id(approve(c, [keep(stale)]))[m["id"]] == {"material_id": m["id"], "status": "invalid", "reason": "trashed"}
    assert by_id(ask_review(c, [stale]))[m["id"]]["reason"] == "trashed"
    assert m["id"] not in view(c, "inbox")


def test_invalid_project_or_empty_content_rejects_only_that_item():
    c, store = make_client()
    a, b, d = new(c, title="a"), new(c, title="b"), new(c, title="only title")
    res = by_id(approve(c, [keep(a, primary_project_id="missing"), keep(b), keep(d, title=None)]))
    assert res[a["id"]] == {"material_id": a["id"], "status": "invalid", "reason": "project"}
    assert res[b["id"]]["status"] == "approved"
    assert res[d["id"]]["reason"] == "no_content"
    assert store.get(ME, "materials", a["id"])["version"] == 1


def test_approved_material_cannot_move_back_to_review():
    c, _ = make_client()
    m = new(c)
    approved = by_id(approve(c, [keep(m)]))[m["id"]]["material"]
    assert by_id(ask_review(c, [approved]))[m["id"]] == {"material_id": m["id"], "status": "invalid", "reason": "approved"}


@pytest.mark.parametrize("items, words", [
    ([], "검토 항목"),
    ([{"material_id": f"m{i}", "expected_version": 1} for i in range(51)], "50"),
    ([{"material_id": "a", "expected_version": 1}, {"material_id": "a", "expected_version": 1}], "두 번"),
    ([{"material_id": "a", "expected_version": 1, "action": "link"}], "보관 승인(keep)만"),
    ([{"material_id": "a", "expected_version": 1, "action": "trash"}], "보관 승인(keep)만"),
    ([{"material_id": "a", "expected_version": 1, "action": "delete"}], "작업"),
    ([{"material_id": "a", "expected_version": 0}], "버전"),
    ([{"material_id": "a", "expected_version": 1, "changes": {"user_importance": "urgent"}}], "중요도"),
    ([{"material_id": "a", "expected_version": 1, "changes": {"body": "x"}}], "보낼 수 없는"),
    ([{"material_id": "a", "expected_version": 1, "changes": {"title": "가" * 201}}], "200자"),
])
def test_whole_request_rejected_with_422_and_key_is_released(items, words):
    c, store = make_client()
    res = approve(c, items, key="bad")
    assert res.status_code == 422 and words in res.json()["detail"], res.json()
    assert len(store.list(ME, "idempotency", limit=10).items) == 0


def test_approval_requires_idempotency_key_and_owner():
    c, _ = make_client()
    m = new(c)
    body = {"items": [keep(m)]}
    no_key = c.post("/api/reviews/approve", json=body,
                    headers={"Authorization": "Bearer t", "X-Data-Mode": "personal"})
    assert no_key.status_code == 422
    intruder, _ = make_client(uid="intruder")
    assert intruder.post("/api/reviews/approve", json=body, headers=h()).status_code == 403


def test_kept_rule():
    base = {"review_status": "approved", "copy_status": "not_applicable", "lifecycle": "active"}
    assert is_kept(base)
    assert not is_kept({**base, "review_status": "unreviewed"})
    assert not is_kept({**base, "lifecycle": "trash"})
    assert not is_kept({**base, "copy_status": "pending"})
