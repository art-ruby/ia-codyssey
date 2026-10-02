"""T06.01 숫자 기록 CRUD: 추가·조회·수정·삭제, 입력 검증 422, 버전 충돌 409, 모드 분리, 중복 재전송.

`data`에는 수기(개인 모드)·표본(표본 모드) 기록만 둔다. 실제 집계값은 저장하지 않는다(PRD §11).
"""

from __future__ import annotations

import itertools

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.firestore import MemoryStore
from app.main import create_app

OWNER = "owner-1"
_keys = itertools.count()


def make_client():
    store = MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store)
    return TestClient(app), store


def h(key=None, mode="personal"):
    return {"Authorization": "Bearer t", "X-Data-Mode": mode, "Idempotency-Key": key or f"d{next(_keys)}"}


GOOD = {"date": "2026-10-01", "metric_type": "kept_count", "value": 3, "memo": "점심 전 보관"}


def add(c, body=None, mode="personal", key=None):
    return c.post("/api/data", json=body or GOOD, headers=h(key, mode))


# ── 추가·조회 ─────────────────────────────────────────────────────

def test_create_and_get_record_with_origin_from_mode():
    c, _ = make_client()
    res = add(c)
    assert res.status_code == 201
    rec = res.json()
    assert {k: rec[k] for k in ("date", "metric_type", "value", "memo")} == GOOD
    assert rec["origin"] == "manual" and rec["mode"] == "personal" and rec["version"] == 1
    assert c.get(f"/api/data/{rec['id']}", headers=h()).json() == rec

    sample = add(c, mode="sample").json()
    assert sample["origin"] == "sample" and sample["mode"] == "sample"


def test_origin_cannot_be_chosen_by_client():
    c, _ = make_client()
    assert add(c, {**GOOD, "origin": "actual"}).status_code == 422


@pytest.mark.parametrize("change", [
    {"value": -1}, {"value": 1.5}, {"value": 2.0}, {"value": "3"}, {"value": True}, {"value": 1_000_001},
    {"date": "2026-02-30"}, {"date": "2026/10/01"}, {"date": "1999-12-31"}, {"date": "26-10-01"},
    {"metric_type": "file_size"}, {"memo": "가" * 501},
])
def test_invalid_input_is_422(change):
    c, _ = make_client()
    assert add(c, {**GOOD, **change}).status_code == 422


def test_missing_fields_are_422_but_memo_is_optional():
    c, _ = make_client()
    for name in ("date", "metric_type", "value"):
        body = {k: v for k, v in GOOD.items() if k != name}
        assert add(c, body).status_code == 422
    assert add(c, {k: v for k, v in GOOD.items() if k != "memo"}).json()["memo"] == ""


def test_zero_is_a_valid_count():
    c, _ = make_client()
    assert add(c, {**GOOD, "value": 0}).json()["value"] == 0


def test_same_key_replays_and_does_not_duplicate():
    c, store = make_client()
    first = add(c, key="same")
    again = add(c, key="same")
    assert again.status_code == 201 and again.json() == first.json()
    assert len(store._docs["data"]) == 1
    assert add(c, {**GOOD, "value": 9}, key="same").status_code == 409  # 같은 키·다른 내용


def test_same_date_may_have_several_records():
    c, _ = make_client()
    add(c)
    assert add(c, {**GOOD, "value": 5}).status_code == 201


# ── 목록 ─────────────────────────────────────────────────────────

def test_list_is_newest_date_first_with_filters_and_pages():
    c, _ = make_client()
    for day in range(1, 26):
        add(c, {"date": f"2026-09-{day:02d}", "metric_type": "kept_count", "value": day})
        add(c, {"date": f"2026-09-{day:02d}", "metric_type": "received_count", "value": day + 1})
    page = c.get("/api/data", params={"metric_type": "kept_count", "limit": 10}, headers=h()).json()
    assert [r["date"] for r in page["items"]] == [f"2026-09-{d:02d}" for d in range(25, 15, -1)]
    assert page["total"] == 25 and page["next_cursor"]
    seen = [r["id"] for r in page["items"]]
    cursor = page["next_cursor"]
    while cursor:
        nxt = c.get("/api/data", params={"metric_type": "kept_count", "limit": 10, "cursor": cursor}, headers=h()).json()
        seen += [r["id"] for r in nxt["items"]]
        cursor = nxt["next_cursor"]
    assert len(seen) == len(set(seen)) == 25
    ranged = c.get("/api/data", params={"date_from": "2026-09-10", "date_to": "2026-09-12"}, headers=h()).json()
    assert ranged["total"] == 6 and {r["date"] for r in ranged["items"]} == {"2026-09-10", "2026-09-11", "2026-09-12"}


@pytest.mark.parametrize("params", [{"date_from": "2026-09-12", "date_to": "2026-09-10"}, {"limit": 101},
                                    {"metric_type": "x"}, {"cursor": "망가진커서"}, {"date_from": "2026-13-01"}])
def test_list_rejects_bad_query(params):
    c, _ = make_client()
    assert c.get("/api/data", params=params, headers=h()).status_code == 422


def test_cursor_from_other_filter_is_rejected():
    c, _ = make_client()
    for day in range(1, 5):
        add(c, {**GOOD, "date": f"2026-09-0{day}"})
    cursor = c.get("/api/data", params={"limit": 2}, headers=h()).json()["next_cursor"]
    assert c.get("/api/data", params={"limit": 2, "cursor": cursor, "metric_type": "received_count"},
                 headers=h()).status_code == 422


# ── 수정·삭제 ─────────────────────────────────────────────────────

def test_update_changes_sent_fields_and_bumps_version():
    c, _ = make_client()
    rec = add(c).json()
    res = c.put(f"/api/data/{rec['id']}", json={"expected_version": 1, "value": 7, "date": "2026-10-02"}, headers=h())
    assert res.status_code == 200
    up = res.json()
    assert (up["value"], up["date"], up["memo"], up["version"], up["origin"]) == (7, "2026-10-02", GOOD["memo"], 2, "manual")


@pytest.mark.parametrize("body", [{"expected_version": 1, "value": -3}, {"expected_version": 1, "origin": "sample"},
                                  {"expected_version": 1, "date": "2026-02-29"}, {"value": 4}])
def test_update_validation(body):
    c, _ = make_client()
    rec = add(c).json()
    assert c.put(f"/api/data/{rec['id']}", json=body, headers=h()).status_code == 422


def test_update_without_changes_is_422_and_keeps_version():
    c, _ = make_client()
    rec = add(c).json()
    assert c.put(f"/api/data/{rec['id']}", json={"expected_version": 1}, headers=h()).status_code == 422
    after = c.get(f"/api/data/{rec['id']}", headers=h()).json()
    assert (after["version"], after["updated_at"]) == (1, rec["updated_at"])


def test_version_conflict_is_409():
    c, _ = make_client()
    rec = add(c).json()
    c.put(f"/api/data/{rec['id']}", json={"expected_version": 1, "value": 8}, headers=h())
    stale = c.put(f"/api/data/{rec['id']}", json={"expected_version": 1, "value": 9}, headers=h())
    assert stale.status_code == 409 and stale.json()["current_version"] == 2
    assert c.delete(f"/api/data/{rec['id']}", params={"expected_version": 1}, headers=h()).status_code == 409


def test_delete_requires_current_version_and_removes():
    c, _ = make_client()
    rec = add(c).json()
    assert c.delete(f"/api/data/{rec['id']}", headers=h()).status_code == 422
    res = c.delete(f"/api/data/{rec['id']}", params={"expected_version": 1}, headers=h())
    assert res.status_code == 200 and res.json() == {"deleted": True, "id": rec["id"]}
    assert c.get(f"/api/data/{rec['id']}", headers=h()).status_code == 404


# ── 모드·소유자 ───────────────────────────────────────────────────

def test_other_mode_cannot_read_change_or_delete():
    c, _ = make_client()
    rec = add(c).json()
    assert c.get(f"/api/data/{rec['id']}", headers=h(mode="sample")).status_code == 404
    assert c.put(f"/api/data/{rec['id']}", json={"expected_version": 1, "value": 1},
                 headers=h(mode="sample")).status_code == 404
    assert c.delete(f"/api/data/{rec['id']}", params={"expected_version": 1}, headers=h(mode="sample")).status_code == 404
    assert c.get("/api/data", headers=h(mode="sample")).json()["total"] == 0
