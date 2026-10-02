"""T04.03 AI 사용량: 소유자 전체·서울 날짜 기준 일일 한도, 예약 시 차감·보내기 전 실패만 환불, 한도 대기.

실제 Provider 대신 가짜 Adapter를 쓴다. 날짜는 `usage._now`를 바꿔 흉내 낸다.
"""

from __future__ import annotations

import itertools
import threading
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import ConfigError, load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.analysis import usage
from app.features.analysis.provider import ProviderError
from app.main import create_app
from test_analysis_lifecycle import FakeAdapter  # 같은 폴더의 가짜 Adapter를 재사용한다

OWNER = "owner-1"
_keys = itertools.count()


def make_client(limit=2, store=None, adapter=None, factory=None):
    store = store or MemoryStore()
    adapter = adapter or FakeAdapter()
    settings = load_settings({"OWNER_UID": OWNER, "AI_DAILY_REQUEST_LIMIT": str(limit)})
    app = create_app(settings, verify_token=lambda t: {"uid": OWNER}, store=store,
                     analysis_adapter_factory=factory or (lambda: adapter))
    return TestClient(app), store, adapter


def h(mode="personal"):
    return {"Authorization": "Bearer t", "X-Data-Mode": mode, "Idempotency-Key": f"u{next(_keys)}"}


def new(c, mode="personal", **body):
    res = c.post("/api/materials", json=body or {"title": "제목", "body": f"본문 {next(_keys)}"}, headers=h(mode))
    assert res.status_code == 201
    return res.json()


def analyze(c, m, mode="personal"):
    return c.post(f"/api/materials/{m['id']}/analyze", json={"expected_version": m["version"]}, headers=h(mode))


def get(c, m, mode="personal"):
    return c.get(f"/api/materials/{m['id']}", headers=h(mode)).json()


def usage_now(c, mode="personal"):
    return c.get("/api/ai/usage", headers=h(mode)).json()


@pytest.fixture
def seoul_day(monkeypatch):
    """서울 날짜를 바꿀 수 있게 한다. 기본은 2026-10-02 정오(서울)."""
    clock = {"now": datetime(2026, 10, 2, 3, 0, tzinfo=timezone.utc)}
    monkeypatch.setattr(usage, "_now", lambda: clock["now"])
    return clock


def test_each_sent_request_is_counted_and_shown(seoul_day):
    c, _, _ = make_client(limit=5)
    analyze(c, new(c))
    u = usage_now(c)
    assert (u["date"], u["used"], u["limit"], u["remaining"]) == ("2026-10-02", 1, 5, 4)
    assert u["by_kind"] == {"analysis": 1, "chat": 0}
    assert u["total_tokens"] == 100 and u["failed_sent"] == 0
    assert u["max_output_tokens"] == 1500 and u["timeout_seconds"] == 120
    assert u["resets_at"] == "2026-10-02T15:00:00+00:00"  # 서울 자정


def test_limit_reached_leaves_material_waiting_without_call(seoul_day):
    c, _, adapter = make_client(limit=1)
    analyze(c, new(c))
    waiting = new(c)

    res = analyze(c, waiting)

    assert res.status_code == 200 and res.json()["status"] == "quota_waiting"
    assert get(c, waiting)["analysis_status"] == "quota_waiting"
    assert len(adapter.calls) == 1
    u = usage_now(c)
    assert u["used"] == 1 and u["remaining"] == 0 and u["pending_count"] == 1


def test_date_change_alone_does_not_call_and_user_resume_does(seoul_day):
    c, _, adapter = make_client(limit=1)
    analyze(c, new(c))
    waiting = new(c)
    analyze(c, waiting)

    seoul_day["now"] = datetime(2026, 10, 2, 15, 30, tzinfo=timezone.utc)  # 서울 10월 3일
    assert get(c, waiting)["analysis_status"] == "quota_waiting"
    assert usage_now(c)["used"] == 0 and len(adapter.calls) == 1

    assert analyze(c, get(c, waiting)).status_code == 202
    assert get(c, waiting)["analysis_status"] == "done" and len(adapter.calls) == 2
    assert usage_now(c)["used"] == 1


def test_limit_is_shared_by_personal_and_sample_modes(seoul_day):
    c, _, _ = make_client(limit=1)
    analyze(c, new(c, mode="personal"))
    res = analyze(c, new(c, mode="sample"), mode="sample")
    assert res.json()["status"] == "quota_waiting"
    assert usage_now(c, mode="sample")["used"] == 1


def test_pre_send_failure_is_refunded(seoul_day):
    def broken():
        raise ConfigError("ai 설정 누락")

    c, _, _ = make_client(limit=1, factory=broken)
    analyze(c, new(c))
    assert usage_now(c)["used"] == 0


@pytest.mark.parametrize("error, status", [("invalid_output", "failed"), ("timeout", "failed"),
                                           ("rate_limited", "quota_waiting")])
def test_sent_failures_stay_counted(seoul_day, error, status):
    c, _, adapter = make_client(limit=3)
    adapter.outcomes = [ProviderError(error, 429 if error == "rate_limited" else None)]
    m = new(c)
    analyze(c, m)
    doc = get(c, m)
    assert doc["analysis_status"] == status and doc["analysis_error"] == error
    u = usage_now(c)
    assert u["used"] == 1 and u["failed_sent"] == 1


def test_tokens_of_a_reply_that_failed_validation_are_counted(seoul_day):
    # 리뷰 재현: 응답이 형식 검증에 실패하면 total_tokens가 버려지던 문제. 실제 Adapter + 가짜 응답으로 확인한다.
    from test_analysis_contract import FakeCompleter

    from app.features.analysis.provider import AnalysisAdapter

    c, _, _ = make_client(limit=3, factory=lambda: AnalysisAdapter(FakeCompleter("형식이 아닌 응답")))
    m = new(c)
    analyze(c, m)
    assert get(c, m)["analysis_error"] == "invalid_output"
    u = usage_now(c)
    assert (u["used"], u["failed_sent"], u["total_tokens"]) == (1, 1, 321)


def test_provider_429_waits_instead_of_failing_and_can_resume(seoul_day):
    c, _, adapter = make_client(limit=3)
    adapter.outcomes = [ProviderError("rate_limited", 429)]
    m = new(c)
    analyze(c, m)
    assert usage_now(c)["pending_count"] == 1
    assert analyze(c, get(c, m)).status_code == 202
    assert get(c, m)["analysis_status"] == "done" and usage_now(c)["used"] == 2


def test_reuse_refusal_and_in_progress_do_not_count(seoul_day):
    c, store, _ = make_client(limit=5)
    m = new(c)
    analyze(c, m)
    analyze(c, get(c, m))  # 같은 입력 재사용
    analyze(c, new(c, title="제외", ai_excluded=True))
    busy = new(c)
    store.transform(RequestContext(OWNER, "personal", None), "materials", busy["id"], lambda d: {
        "analysis_status": "analyzing", "analysis_deadline_at": "2999-01-01T00:00:00+00:00"})
    assert analyze(c, busy).status_code == 409
    assert usage_now(c)["used"] == 1


def test_concurrent_reservations_never_exceed_limit(seoul_day):
    store = MemoryStore()
    granted = []
    barrier = threading.Barrier(20)

    def worker():
        barrier.wait()
        granted.append(usage.reserve(store, OWNER, "analysis", limit=5))

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(1 for g in granted if g) == 5
    assert usage.summary(store, OWNER, limit=5)["used"] == 5


def test_refund_goes_to_the_reservation_day(seoul_day):
    store = MemoryStore()
    day = usage.reserve(store, OWNER, "analysis", limit=5)
    seoul_day["now"] = datetime(2026, 10, 3, 3, 0, tzinfo=timezone.utc)
    usage.refund(store, OWNER, day, "analysis")
    assert usage.summary(store, OWNER, limit=5)["used"] == 0
    seoul_day["now"] = datetime(2026, 10, 2, 3, 0, tzinfo=timezone.utc)
    assert usage.summary(store, OWNER, limit=5)["used"] == 0


def test_usage_records_are_per_owner(seoul_day):
    store = MemoryStore()
    usage.reserve(store, OWNER, "analysis", limit=1)
    assert usage.reserve(store, "someone-else", "analysis", limit=1)
    assert usage.summary(store, "someone-else", limit=1)["used"] == 1
