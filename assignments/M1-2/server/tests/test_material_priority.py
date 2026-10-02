"""T04.04 우선순위: 최종 중요도(사용자 값 → 쓸 수 있는 AI 제안) → 대응 필요 → 최신 접수 → ID.

정렬 함수 단위 시험과 `GET /api/materials/priority` API 시험을 함께 둔다.
"""

from __future__ import annotations

import itertools
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.analysis.schemas import content_hash
from app.features.materials import priority
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
_keys = itertools.count()


def doc(i, registered, user=None, ai=None, action=None, status="done", outdated=False, **extra):
    d = {"id": f"m{i}", "title": f"자료 {i}", "body": "본문", "registered_at": registered,
         "lifecycle": "active", "review_status": "unreviewed", "copy_status": "not_applicable",
         "user_importance": user, "analysis_status": status, "ai_importance": ai,
         "ai_needs_action": action, "ai_importance_reason": "AI 이유" if ai else None, **extra}
    if status == "done":
        d["ai_content_hash"] = "다른 내용" if outdated else content_hash(d)
    return d


def ids(items):
    return [m["id"] for m in items]


# ── 정렬 규칙 ─────────────────────────────────────────────────────

def test_user_value_wins_over_ai_and_source_is_reported():
    m = doc(1, "2026-10-01", user="low", ai="high")
    assert priority.final_importance(m) == ("low", "user")
    assert priority.final_importance(doc(2, "2026-10-01", ai="medium")) == ("medium", "ai")


@pytest.mark.parametrize("case", [
    dict(status="failed"), dict(status="analyzing"), dict(status="awaiting_start"),
    dict(outdated=True), dict(status="quota_waiting"),
])
def test_ai_suggestion_is_used_only_when_current_and_done(case):
    m = doc(1, "2026-10-01", ai="high", action=True, **case)
    assert priority.final_importance(m) == (None, None)
    assert priority.needs_action(m) is None


def test_order_is_importance_then_action_then_newest_then_id():
    docs = [
        doc(1, "2026-10-01", ai="medium", action=True),
        doc(2, "2026-10-03", user="high"),
        doc(3, "2026-10-02", ai="high", action=True),
        doc(4, "2026-10-05", ai="medium", action=False),
        doc(5, "2026-10-04", user="low"),
        doc(6, "2026-10-03", ai="high", action=True),  # 3번과 중요도·대응 같음 → 최신 먼저
        doc(7, "2026-10-03", ai="high", action=True),  # 6번과 접수 시각까지 같음 → ID 순
    ]
    graded, pending = priority.prioritize(docs)
    assert ids(graded) == ["m6", "m7", "m3", "m2", "m1", "m4", "m5"]
    assert pending == []


def test_pending_judgement_is_separate_and_newest_first():
    docs = [doc(1, "2026-10-01"), doc(2, "2026-10-02", status="failed", ai="high"), doc(3, "2026-10-03", ai="low")]
    graded, pending = priority.prioritize(docs)
    assert ids(graded) == ["m3"] and ids(pending) == ["m2", "m1"]


def test_reason_follows_the_source():
    user_with_reason = doc(1, "2026-10-01", user="high", ai="low", save_reason="내가 쓴 저장 이유")
    user_without = doc(2, "2026-10-01", user="high", ai="low")
    by_ai = doc(3, "2026-10-01", ai="medium")
    assert priority.reason(user_with_reason) == "내가 쓴 저장 이유"
    assert priority.reason(user_without) == "AI 이유"
    assert priority.reason(by_ai) == "AI 이유"


# ── API ──────────────────────────────────────────────────────────

def make_client(store=None):
    store = store or MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store)
    return TestClient(app), store


def h():
    return {"Authorization": "Bearer t", "X-Data-Mode": "personal", "Idempotency-Key": f"p{next(_keys)}"}


def new(c, store, title, **ai):
    m = c.post("/api/materials", json={"title": title, "body": f"{title} 본문"}, headers=h()).json()
    if ai:
        store.transform(ME, "materials", m["id"], lambda d: {
            "analysis_status": "done", "ai_importance": ai.get("ai"), "ai_needs_action": ai.get("action"),
            "ai_importance_reason": "AI 이유", "ai_content_hash": content_hash(d)})
    return m


def view(c):
    res = c.get("/api/materials/priority", headers=h())
    assert res.status_code == 200
    return res.json()


def test_empty_view():
    c, _ = make_client()
    v = view(c)
    assert v["items"] == [] and v["pending"] == [] and v["counts"] == {"unreviewed": 0, "kept": 0}
    assert v["truncated"] is False


def test_single_material_and_annotations():
    c, store = make_client()
    new(c, store, "하나", ai="high", action=True)
    item = view(c)["items"][0]
    assert item["final_importance"] == "high" and item["importance_source"] == "ai"
    assert item["needs_action"] is True and item["reason"] == "AI 이유"
    assert item["review_status"] == "unreviewed"


def test_many_materials_sorted_and_counts():
    c, store = make_client()
    for i, (imp, act) in enumerate([("low", False), ("high", False), ("medium", True), ("high", True), ("medium", False)]):
        new(c, store, f"자료{i}", ai=imp, action=act)
    pending = new(c, store, "분석 전")
    v = view(c)
    assert [m["title"] for m in v["items"]] == ["자료3", "자료1", "자료2", "자료4", "자료0"]
    assert [m["id"] for m in v["pending"]] == [pending["id"]]
    assert v["counts"] == {"unreviewed": 6, "kept": 0}


def test_user_change_reorders_immediately():
    c, store = make_client()
    a = new(c, store, "A", ai="high")
    b = new(c, store, "B", ai="medium")
    assert [m["title"] for m in view(c)["items"]] == ["A", "B"]
    c.put(f"/api/materials/{b['id']}", json={"expected_version": b["version"], "user_importance": "high"}, headers=h())
    c.put(f"/api/materials/{a['id']}", json={"expected_version": a["version"], "user_importance": "low"}, headers=h())
    items = view(c)["items"]
    assert [m["title"] for m in items] == ["B", "A"]
    assert [m["importance_source"] for m in items] == ["user", "user"]


def test_ai_failure_goes_to_pending_and_trash_is_excluded():
    c, store = make_client()
    failed = new(c, store, "실패")
    store.transform(ME, "materials", failed["id"], lambda d: {"analysis_status": "failed", "analysis_error": "timeout"})
    trashed = new(c, store, "휴지통", ai="high")
    store.update(ME, "materials", trashed["id"], trashed["version"], {"lifecycle": "trash"})
    v = view(c)
    assert v["items"] == [] and [m["title"] for m in v["pending"]] == ["실패"]


def test_kept_count_uses_shared_rule():
    c, store = make_client()
    m = new(c, store, "보관", ai="medium")
    c.post("/api/reviews/approve", json={"items": [{"material_id": m["id"], "expected_version": m["version"]}]},
           headers=h())
    assert view(c)["counts"] == {"unreviewed": 0, "kept": 1}


def test_scan_limit_keeps_newest_materials(monkeypatch):
    # 리뷰 재현: 오래된 순으로 읽으면 한도를 넘긴 뒤 들어온 최신 자료가 비교에서 빠진다.
    monkeypatch.setattr(priority, "MAX_SCAN", 3)
    c, store = make_client()
    for i in range(4):
        new(c, store, f"오래된{i}", ai="low")
        time.sleep(0.02)  # Windows 시계 해상도에서 접수 시각이 같아지지 않게 한다
    new(c, store, "최신", ai="high")
    v = view(c)
    assert v["items"][0]["title"] == "최신"
    assert [m["title"] for m in v["items"]] == ["최신", "오래된3", "오래된2"]


def test_scan_limit_reports_truncation(monkeypatch):
    monkeypatch.setattr(priority, "MAX_SCAN", 3)
    c, store = make_client()
    for i in range(5):
        new(c, store, f"자료{i}", ai="low")
    v = view(c)
    assert v["truncated"] is True and v["scanned"] == 3
