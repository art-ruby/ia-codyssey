"""T06.02 Summary: 실제(자료에서 계산)·수기·표본을 섞지 않는 일별 값·합계·평균·최소·최대·추세.

명세 예시(앞 7일 매일 2건, 뒤 7일 매일 3건 → 합계 35·평균 2.5·최소 2·최대 3·증가율 50%)는 독립 계산과 대조한다.
"""

from __future__ import annotations

import itertools
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.data import summary
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
SAMPLE = RequestContext(OWNER, "sample", None)
_keys = itertools.count()


@pytest.fixture
def today(monkeypatch):
    """서울 날짜 기준 '오늘'을 2026-10-14로 고정한다."""
    clock = {"now": datetime(2026, 10, 14, 3, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(summary, "_now", lambda: clock["now"])
    return clock


def add_data(store, ctx, day, value, metric="kept_count", origin=None):
    origin = origin or ("manual" if ctx.mode == "personal" else "sample")
    store.create(ctx, "data", {"date": day, "metric_type": metric, "value": value, "memo": "", "origin": origin})


def days(start, count):
    first = date.fromisoformat(start)
    return [(first + timedelta(days=i)).isoformat() for i in range(count)]


def run(store, ctx, source=None, metric="kept_count", start=None, end=None):
    return summary.summarize_data(store, ctx, source, metric, start, end)


# ── 계산 ─────────────────────────────────────────────────────────

def test_spec_example_matches_independent_calculation(today):
    store = MemoryStore()
    span = days("2026-10-01", 14)
    values = [2] * 7 + [3] * 7
    for day, value in zip(span, values):
        add_data(store, ME, day, value)

    s = run(store, ME, source="manual")

    expected_total = sum(values)
    assert (s["total"], s["days"]) == (expected_total, 14) == (35, 14)
    assert s["average"] == expected_total / 14 == 2.5
    assert (s["min"], s["max"]) == (min(values), max(values)) == (2, 3)
    assert s["period"] == {"start": "2026-10-01", "end": "2026-10-14"}
    assert [d["value"] for d in s["daily"]] == values
    trend = s["trend"]
    assert trend["status"] == "increase" and trend["change_rate"] == pytest.approx((3 - 2) / 2 * 100) == 50.0
    assert (trend["recent_average"], trend["previous_average"]) == (3.0, 2.0)
    assert trend["reference_date"] == "2026-10-14"


def test_empty_days_after_observation_start_count_as_zero(today):
    store = MemoryStore()
    add_data(store, ME, "2026-10-10", 4)
    add_data(store, ME, "2026-10-12", 2)
    add_data(store, ME, "2026-10-12", 1)  # 같은 날짜 기록은 합계
    s = run(store, ME, source="manual")
    assert [d["value"] for d in s["daily"]] == [4, 0, 3, 0, 0]
    assert (s["total"], s["days"], s["min"], s["max"]) == (7, 5, 0, 4)
    assert s["average"] == 1.4


def test_no_data_gives_zero_total_and_nulls(today):
    s = run(MemoryStore(), ME, source="manual")
    assert s["total"] == 0 and s["days"] == 0 and s["daily"] == []
    assert s["period"] is None and s["average"] is None and s["min"] is None and s["max"] is None
    assert s["trend"] is None


@pytest.mark.parametrize("previous, recent, status, rate", [
    (10, [11] * 7, "increase", 10.0),  # 정확히 +10%는 증가
    (10, [9] * 7, "decrease", -10.0),  # 정확히 -10%는 감소
    (10, [10, 10, 10, 11, 11, 11, 10], "flat", 4.3),  # 평균 73/7 → +4.3%
    (0, [2] * 7, "new", None),  # 이전 기간 0건: 백분율을 만들지 않는다
    (0, [0] * 7, "both_zero", None),
])
def test_trend_boundaries(today, previous, recent, status, rate):
    store = MemoryStore()
    for day, value in zip(days("2026-10-01", 14), [previous] * 7 + recent):
        add_data(store, ME, day, value)
    trend = run(store, ME, source="manual")["trend"]
    assert trend["status"] == status and trend["change_rate"] == rate


def test_less_than_14_days_is_insufficient(today):
    store = MemoryStore()
    for day in days("2026-10-02", 13):
        add_data(store, ME, day, 1)
    trend = run(store, ME, source="manual")["trend"]
    assert trend["status"] == "insufficient" and trend["change_rate"] is None


def test_requested_period_is_clamped_to_observation_start(today):
    store = MemoryStore()
    for day in days("2026-10-05", 10):
        add_data(store, ME, day, 1)
    s = run(store, ME, source="manual", start="2026-09-01", end="2026-10-08")
    assert s["period"] == {"start": "2026-10-05", "end": "2026-10-08"} and s["total"] == 4


# ── 출처·지표·모드를 섞지 않음 ────────────────────────────────────

def test_defaults_per_mode(today):
    store = MemoryStore()
    add_data(store, SAMPLE, "2026-09-30", 5)
    personal = run(store, ME)
    assert personal["source"] == "actual" and personal["metric_type"] == "kept_count"
    s = run(store, SAMPLE)
    assert s["source"] == "sample" and s["total"] == 5
    assert s["trend"]["reference_date"] == "2026-09-30"  # 표본 기준일 = 최신 표본 날짜


def test_metrics_sources_and_modes_are_not_mixed(today):
    store = MemoryStore()
    add_data(store, ME, "2026-10-10", 3, metric="kept_count")
    add_data(store, ME, "2026-10-10", 7, metric="received_count")
    add_data(store, SAMPLE, "2026-10-10", 100)
    assert run(store, ME, source="manual")["total"] == 3
    assert run(store, ME, source="manual", metric="received_count")["total"] == 7
    assert run(store, ME, source="actual")["total"] == 0  # 수기 기록은 실제 값이 아니다


def test_metric_all_returns_separate_results(today):
    store = MemoryStore()
    add_data(store, ME, "2026-10-10", 3, metric="kept_count")
    add_data(store, ME, "2026-10-10", 7, metric="received_count")
    out = run(store, ME, source="manual", metric="all")
    assert {r["metric_type"]: r["total"] for r in out["results"]} == {"received_count": 7, "kept_count": 3}


@pytest.mark.parametrize("ctx, source", [(ME, "sample"), (SAMPLE, "manual")])
def test_source_not_allowed_in_mode(today, ctx, source):
    with pytest.raises(summary.SourceNotAllowed):
        run(MemoryStore(), ctx, source=source)


# ── 실제 값: 자료 상태에서 계산 ────────────────────────────────────

def make_client(store):
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store)
    return TestClient(app)


def h(mode="personal"):
    return {"Authorization": "Bearer t", "X-Data-Mode": mode, "Idempotency-Key": f"s{next(_keys)}"}


def test_actual_counts_follow_trash_restore_and_permanent_delete(today):
    store = MemoryStore()
    c = make_client(store)
    m = c.post("/api/materials", json={"title": "실제 집계 시험"}, headers=h()).json()
    approved = c.post("/api/reviews/approve", json={"items": [{"material_id": m["id"], "expected_version": 1}]},
                      headers=h()).json()["results"][0]["material"]
    # 접수·승인 시각을 서울 날짜 경계로 옮긴다(UTC 15:30 = 서울 다음 날 00:30).
    store.transform(ME, "materials", m["id"], lambda d: {"registered_at": "2026-10-09T15:30:00+00:00",
                                                         "storage_approved_at": "2026-10-10T15:30:00+00:00"})
    store.transform(ME, "intake_records", m["id"], lambda d: {"received_at": "2026-10-09T15:30:00+00:00"})

    kept = run(store, ME, source="actual")
    received = run(store, ME, source="actual", metric="received_count")
    assert kept["daily"][0] == {"date": "2026-10-11", "value": 1} and kept["total"] == 1
    assert received["daily"][0] == {"date": "2026-10-10", "value": 1} and received["total"] == 1

    trashed = c.post("/api/reviews/approve", headers=h(), json={"items": [
        {"material_id": m["id"], "expected_version": approved["version"], "action": "trash"}]}).json()["results"][0]
    assert run(store, ME, source="actual")["total"] == 0  # 휴지통은 보관 수에서 빠진다
    assert run(store, ME, source="actual", metric="received_count")["total"] == 1  # 접수 이력은 유지

    restored = c.post(f"/api/trash/{m['id']}/restore", json={"expected_version": trashed["material"]["version"]},
                      headers=h()).json()
    assert run(store, ME, source="actual")["total"] == 1

    again = c.post("/api/reviews/approve", headers=h(), json={"items": [
        {"material_id": m["id"], "expected_version": restored["version"], "action": "trash"}]}).json()["results"][0]
    c.delete(f"/api/trash/{m['id']}", params={"expected_version": again["material"]["version"], "confirm": "permanent"},
             headers=h())
    assert run(store, ME, source="actual")["total"] == 0
    assert run(store, ME, source="actual", metric="received_count")["total"] == 0  # 영구 삭제는 접수도 다시 계산


# ── API ──────────────────────────────────────────────────────────

def test_api_summary_is_not_treated_as_record_id(today):
    store = MemoryStore()
    add_data(store, ME, "2026-10-10", 3)
    res = make_client(store).get("/api/data/summary", params={"source": "manual"}, headers=h())
    assert res.status_code == 200 and res.json()["total"] == 3 and res.json()["label"] == "사용자 입력 보관 기록"


@pytest.mark.parametrize("params", [{"source": "sample"}, {"metric_type": "file_size"},
                                    {"start_date": "2026-10-10", "end_date": "2026-10-01"}, {"start_date": "2026-13-01"}])
def test_api_rejects_bad_query(today, params):
    assert make_client(MemoryStore()).get("/api/data/summary", params=params, headers=h()).status_code == 422
