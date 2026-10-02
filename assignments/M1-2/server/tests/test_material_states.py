import itertools
from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.materials.service import (ai_allowed, chat_eligible, is_kept, public, revisit_due,
                                            today_seoul)
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
_keys = itertools.count()


def make_client():
    store = MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store)
    return TestClient(app), store


def h(key=None):
    return {"Authorization": "Bearer t", "X-Data-Mode": "personal", "Idempotency-Key": key or f"s{next(_keys)}"}


def new(c, **body):
    res = c.post("/api/materials", json=body or {"title": "t"}, headers=h())
    assert res.status_code == 201
    return res.json()


def ids(items):
    return [{"material_id": m["id"], "expected_version": m["version"]} for m in items]


def later(c, items, revisit_on=None, on=True, key=None):
    body = {"items": ids(items), "later": on}
    if revisit_on is not None:
        body["revisit_on"] = revisit_on
    return c.post("/api/reviews/later", json=body, headers=h(key))


def view(c, name):
    return [m["id"] for m in c.get(f"/api/materials?view={name}", headers=h()).json()["items"]]


def result(res, m):
    return {r["material_id"]: r for r in res.json()["results"]}[m["id"]]


def day(offset):
    return (date.fromisoformat(today_seoul()) + timedelta(days=offset)).isoformat()


# ── 네 상태 축은 별도 필드 ─────────────────────────────────────────

def test_web_material_has_separate_state_fields():
    c, _ = make_client()
    for m in (new(c, url="https://a.test/x"), new(c, title="t")):
        assert m["review_status"] == "unreviewed" and m["copy_status"] == "not_applicable"
        assert m["lifecycle"] == "active" and m["ai_excluded"] is False and m["revisit_on"] is None
        assert m["analysis_status"] in ("link_only", "awaiting_start")


# ── 나중에 보기 ───────────────────────────────────────────────────

def test_later_moves_out_of_inbox_and_review_into_later_view():
    c, store = make_client()
    a, b, d = new(c, title="a"), new(c, title="b"), new(c, title="d")
    c.post("/api/reviews/request", json={"items": ids([b]), "requested": True}, headers=h())
    b = store.get(ME, "materials", b["id"])

    res = later(c, [a, b], revisit_on=day(3))

    assert res.status_code == 200 and res.json()["updated_count"] == 2
    moved = result(res, b)["material"]
    assert moved["review_status"] == "later" and moved["revisit_on"] == day(3)
    assert moved["review_requested"] is False and moved["revisit_due"] is False
    assert set(view(c, "later")) == {a["id"], b["id"]}
    assert view(c, "inbox") == [d["id"]] and view(c, "review") == []


def test_later_without_date_is_allowed_and_never_due():
    c, _ = make_client()
    a = new(c)
    m = result(later(c, [a]), a)["material"]
    assert m["review_status"] == "later" and m["revisit_on"] is None and m["revisit_due"] is False


def test_due_is_computed_on_read_and_changes_nothing():
    c, store = make_client()
    a = new(c)
    m = result(later(c, [a], revisit_on=day(1)), a)["material"]
    assert m["revisit_due"] is False

    doc = store.get(ME, "materials", a["id"])
    # 날짜가 지난 경우를 비교 기준일로 재현한다.
    assert revisit_due(doc, today=day(1)) and revisit_due(doc, today=day(5))
    assert not revisit_due(doc, today=day(0))

    store.update(ME, "materials", a["id"], doc["version"], {"revisit_on": "2020-01-01"})  # 이미 지난 날짜
    got = c.get(f"/api/materials/{a['id']}", headers=h()).json()
    assert got["revisit_due"] is True
    # 날짜가 지나도 승인·삭제·상태 변경이 없다.
    assert got["review_status"] == "later" and got["lifecycle"] == "active" and got["storage_approved_at"] is None
    assert not is_kept(got) and view(c, "later") == [a["id"]]


def test_today_counts_as_due():
    doc = {"review_status": "later", "revisit_on": "2026-10-02"}
    assert revisit_due(doc, today="2026-10-02")
    assert not revisit_due(doc, today="2026-10-01")
    assert not revisit_due({**doc, "review_status": "unreviewed"}, today="2026-10-05")


def test_back_to_inbox_and_change_date():
    c, _ = make_client()
    a = new(c)
    m = result(later(c, [a], revisit_on=day(2)), a)["material"]
    changed = result(later(c, [m], revisit_on=day(7)), a)
    assert changed["status"] == "updated" and changed["material"]["revisit_on"] == day(7)

    back = result(later(c, [changed["material"]], on=False), a)
    assert back["status"] == "updated" and back["material"]["review_status"] == "unreviewed"
    assert back["material"]["revisit_on"] is None and view(c, "inbox") == [a["id"]]
    assert result(later(c, [back["material"]], on=False), a)["status"] == "unchanged"


def test_same_later_resent_with_new_key_is_unchanged():
    c, store = make_client()
    a = new(c)
    first = result(later(c, [a], revisit_on=day(2)), a)["material"]
    again = result(later(c, [a], revisit_on=day(2)), a)  # 예전 버전·새 키
    assert again["status"] == "unchanged" and store.get(ME, "materials", a["id"])["version"] == first["version"]


def test_later_item_can_be_moved_to_review_or_approved():
    c, _ = make_client()
    a, b = new(c, title="a"), new(c, title="b")
    a2, b2 = (r["material"] for r in later(c, [a, b], revisit_on=day(1)).json()["results"])

    moved = c.post("/api/reviews/request", json={"items": ids([a2]), "requested": True}, headers=h()).json()
    m = moved["results"][0]["material"]
    assert m["review_status"] == "unreviewed" and m["review_requested"] and m["revisit_on"] is None
    assert view(c, "review") == [a["id"]]

    approved = c.post("/api/reviews/approve", json={"items": [{**ids([b2])[0], "action": "keep"}]}, headers=h())
    got = approved.json()["results"][0]
    assert got["status"] == "approved" and got["material"]["revisit_on"] is None and is_kept(got["material"])
    assert view(c, "later") == []


def test_later_rules_for_approved_trashed_conflict_and_other_owner():
    c, store = make_client()
    approved, trashed, stale = new(c, title="a"), new(c, title="t"), new(c, title="s")
    c.post("/api/reviews/approve", json={"items": [{**ids([approved])[0], "action": "keep"}]}, headers=h())
    store.update(ME, "materials", trashed["id"], 1, {"lifecycle": "trash"})
    store.update(ME, "materials", stale["id"], 1, {"memo": "다른 곳"})
    other = store.create(RequestContext("owner-2", "personal", None), "materials", {"title": "x"})

    res = later(c, [approved, {**trashed, "version": 2}, stale, other], revisit_on=day(1))

    assert res.status_code == 200 and res.json()["updated_count"] == 0
    assert result(res, approved) == {"material_id": approved["id"], "status": "invalid", "reason": "approved"}
    assert result(res, trashed)["reason"] == "trashed"
    assert result(res, stale) == {"material_id": stale["id"], "status": "conflict", "current_version": 2}
    assert result(res, other) == {"material_id": other["id"], "status": "not_found"}


@pytest.mark.parametrize("body, words", [
    ({"items": [], "later": True}, "검토 항목"),
    ({"items": [{"material_id": "a", "expected_version": 1}], "revisit_on": "2020-01-01"}, "오늘"),
    ({"items": [{"material_id": "a", "expected_version": 1}], "revisit_on": "10/05"}, "다시 볼 날짜"),
    ({"items": [{"material_id": "a", "expected_version": 1}], "later": False, "revisit_on": "2099-01-01"}, "되돌릴 때"),
])
def test_later_whole_request_422(body, words):
    c, store = make_client()
    res = c.post("/api/reviews/later", json=body, headers=h("bad"))
    assert res.status_code == 422 and words in res.json()["detail"], res.json()
    assert store.list(ME, "idempotency", limit=5).items == []


def test_later_same_key_replays_after_midnight_but_new_key_rejects_past_date():
    c, store = make_client()
    material = new(c)
    payload = {"items": ids([material]), "later": True, "revisit_on": "2026-10-02"}

    class BeforeMidnight:
        @staticmethod
        def now(tz):
            return datetime(2026, 10, 2, 23, 59, tzinfo=tz)

    class AfterMidnight:
        @staticmethod
        def now(tz):
            return datetime(2026, 10, 3, 0, 1, tzinfo=tz)

    with patch("app.features.reviews.service.datetime", BeforeMidnight):
        first = c.post("/api/reviews/later", json=payload, headers=h("cross-midnight"))
    assert first.status_code == 200

    with patch("app.features.reviews.service.datetime", AfterMidnight):
        replay = c.post("/api/reviews/later", json=payload, headers=h("cross-midnight"))
        new_request = c.post("/api/reviews/later", json=payload, headers=h("after-midnight"))

    assert replay.status_code == 200 and replay.json() == first.json()
    assert new_request.status_code == 422 and "오늘" in new_request.json()["detail"]
    assert store.get(ME, "materials", material["id"])["version"] == 2


# ── AI 분석 제외 ──────────────────────────────────────────────────

def test_ai_exclusion_persists_and_keeps_analysis_status():
    c, _ = make_client()
    m = new(c, url="https://a.test/x")
    on = c.put(f"/api/materials/{m['id']}", json={"expected_version": 1, "ai_excluded": True}, headers=h())
    assert on.status_code == 200 and on.json()["ai_excluded"] is True
    got = c.get(f"/api/materials/{m['id']}", headers=h()).json()  # 새로 불러와도 유지
    assert got["ai_excluded"] is True and got["analysis_status"] == "link_only"
    assert got["review_status"] == "unreviewed"  # 검토 상태와 묶이지 않는다

    off = c.put(f"/api/materials/{m['id']}", json={"expected_version": 2, "ai_excluded": False}, headers=h())
    assert off.json()["ai_excluded"] is False and off.json()["analysis_status"] == "link_only"


def test_ai_exclusion_null_means_no_change_and_can_be_set_at_intake():
    c, _ = make_client()
    m = new(c, title="t", ai_excluded=True)
    assert m["ai_excluded"] is True
    res = c.put(f"/api/materials/{m['id']}", json={"expected_version": 1, "ai_excluded": None, "memo": "x"}, headers=h())
    assert res.status_code == 200 and res.json()["ai_excluded"] is True


def test_approval_does_not_change_ai_exclusion():
    c, _ = make_client()
    excluded, normal = new(c, title="e", ai_excluded=True), new(c, title="n")
    res = c.post("/api/reviews/approve", json={"items": [{**i, "action": "keep"} for i in ids([excluded, normal])]},
                 headers=h()).json()["results"]
    assert res[0]["material"]["ai_excluded"] is True and res[1]["material"]["ai_excluded"] is False


# ── 보관함·채팅 대상 공통 조건(A13 준비) ──────────────────────────

@pytest.mark.parametrize("changes, kept, chat", [
    ({}, True, True),
    ({"ai_excluded": True}, True, False),
    ({"review_status": "unreviewed"}, False, False),
    ({"review_status": "later"}, False, False),
    ({"lifecycle": "trash"}, False, False),
    ({"lifecycle": "deleting"}, False, False),
    ({"copy_status": "uploading"}, False, False),
])
def test_kept_and_chat_conditions(changes, kept, chat):
    doc = {"review_status": "approved", "copy_status": "not_applicable", "lifecycle": "active",
           "ai_excluded": False, **changes}
    assert is_kept(doc) is kept and chat_eligible(doc) is chat
    assert ai_allowed(doc) is (not doc["ai_excluded"])


def test_public_reports_missing_exclusion_as_false():
    assert public({"id": "x", "title": "t"})["ai_excluded"] is False
