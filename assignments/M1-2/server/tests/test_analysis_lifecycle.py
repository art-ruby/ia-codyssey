"""T04.02 사용자 시작 분석: 시작·상태 조회·재사용·실패 후 재시도·처리 중 수정·서버 재시작.

실제 Provider 대신 호출 수를 세는 가짜 Adapter를 쓴다. TestClient는 응답 직후 백그라운드 작업을 실행한다.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import ConfigError, load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.analysis import service as analysis
from app.features.analysis.provider import ProviderError
from app.features.analysis.schemas import AnalysisResult
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
_keys = itertools.count()


def result(title="AI 제목") -> AnalysisResult:
    return AnalysisResult(
        ai_title=title, ai_summary="요약이다.", ai_importance="high", ai_importance_reason="이유",
        ai_primary_project_id=None, ai_kind="note", ai_keywords=["k"], ai_uncertainties=[],
        ai_recommended_action=None, ai_needs_action=False, ai_evidence=["인용문 여덟 글자 이상"],
        ai_checked_scope={"fields": ["title"], "chars": 1, "url_fetched": False},
        ai_grounding={"fact_checked": False}, model="gpt-6-luna", total_tokens=100,
    )


class FakeAdapter:
    def __init__(self):
        self.calls = []
        self.outcomes = []  # 차례로 쓸 결과(AnalysisResult 또는 예외). 비면 기본 결과
        self.during = None  # 호출 중에 실행할 동작(처리 중 수정 재현)

    def analyze_material(self, material, projects):
        self.calls.append((dict(material), list(projects)))
        if self.during:
            action, self.during = self.during, None
            action()
        outcome = self.outcomes.pop(0) if self.outcomes else result()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make_client(store=None, adapter=None, factory=None):
    store = store or MemoryStore()
    adapter = adapter or FakeAdapter()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store,
                     analysis_adapter_factory=factory or (lambda: adapter))
    return TestClient(app), store, adapter


def h(key=None, mode="personal"):
    return {"Authorization": "Bearer t", "X-Data-Mode": mode, "Idempotency-Key": key or f"a{next(_keys)}"}


def new(c, **body):
    res = c.post("/api/materials", json=body or {"title": "제목", "body": "본문 내용"}, headers=h())
    assert res.status_code == 201
    return res.json()


def analyze(c, m, key=None, version=None, mode="personal"):
    return c.post(f"/api/materials/{m['id']}/analyze", json={"expected_version": version or m["version"]},
                  headers=h(key, mode))


def get(c, m):
    return c.get(f"/api/materials/{m['id']}", headers=h()).json()


def test_start_returns_202_and_saved_result_is_visible_by_get():
    c, _, adapter = make_client()
    m = new(c, title="내 제목", body="본문 내용", user_importance="low")

    res = analyze(c, m)

    assert res.status_code == 202 and res.json()["status"] == "accepted"
    assert res.json()["material"]["analysis_status"] == "analyzing"
    done = get(c, m)
    assert done["analysis_status"] == "done" and done["ai_title"] == "AI 제목"
    assert done["ai_importance"] == "high" and done["ai_grounding"] == {"fact_checked": False}
    # 사용자 값과 자료 버전·검토 상태는 그대로다.
    assert done["title"] == "내 제목" and done["user_importance"] == "low"
    assert done["version"] == m["version"] and done["review_status"] == "unreviewed"
    assert done["analysis_outdated"] is False and done["analysis_stale"] is False
    assert len(adapter.calls) == 1


def test_only_sent_fields_reach_adapter_with_active_projects():
    c, _, adapter = make_client()
    c.post("/api/projects", json={"name": "결제 개편", "description": ""}, headers=h())
    m = new(c, title="제목", body="본문 내용", user_importance="high")
    analyze(c, m)
    material, projects = adapter.calls[0]
    assert material["body"] == "본문 내용" and material["title"] == "제목"
    assert [p["name"] for p in projects] == ["결제 개편"]


def test_same_key_replays_without_new_call():
    c, _, adapter = make_client()
    m = new(c)
    first = analyze(c, m, key="same")
    again = analyze(c, m, key="same")
    assert again.status_code == 202 and again.json() == first.json()
    assert len(adapter.calls) == 1


def test_new_key_for_completed_same_input_reuses_result():
    c, _, adapter = make_client()
    m = new(c)
    analyze(c, m)
    res = analyze(c, m)
    assert res.status_code == 200 and res.json()["status"] == "reused"
    assert res.json()["material"]["ai_title"] == "AI 제목"
    assert len(adapter.calls) == 1


def test_project_list_change_makes_a_new_analysis_target():
    c, _, adapter = make_client()
    m = new(c)
    analyze(c, m)
    c.post("/api/projects", json={"name": "새 프로젝트", "description": ""}, headers=h())
    assert analyze(c, m).status_code == 202
    assert len(adapter.calls) == 2


def test_failure_is_saved_and_user_retry_calls_again():
    c, _, adapter = make_client()
    adapter.outcomes = [ProviderError("invalid_output"), result("두 번째")]
    m = new(c)

    analyze(c, m)
    failed = get(c, m)
    assert failed["analysis_status"] == "failed" and failed["analysis_error"] == "invalid_output"
    assert failed["ai_title"] is None

    assert analyze(c, m).status_code == 202
    assert get(c, m)["ai_title"] == "두 번째"
    assert len(adapter.calls) == 2


def test_failure_records_whether_request_was_sent():
    store = MemoryStore()

    def broken():
        raise ConfigError("ai 설정 누락: OPENAI_API_KEY")

    c, _, _ = make_client(store=store, factory=broken)
    m = new(c)
    analyze(c, m)
    doc = store.get(ME, "materials", m["id"])
    assert doc["analysis_error"] == "missing_ai_settings" and doc["analysis_request_sent"] is False

    c2, _, adapter = make_client(store=store)
    adapter.outcomes = [ProviderError("rate_limited", 429)]
    analyze(c2, get(c2, m))
    doc = store.get(ME, "materials", m["id"])
    assert doc["analysis_error"] == "rate_limited" and doc["analysis_request_sent"] is True


def test_edit_during_analysis_discards_result_and_keeps_edit():
    c, store, adapter = make_client()
    m = new(c, title="제목", body="처음 본문")
    adapter.during = lambda: store.update(ME, "materials", m["id"], m["version"], {"body": "고친 본문"})

    analyze(c, m)

    doc = get(c, m)
    assert doc["body"] == "고친 본문" and doc["version"] == m["version"] + 1
    assert doc["analysis_status"] == "awaiting_start" and doc["analysis_error"] == "input_changed"
    assert doc["ai_title"] is None


def test_turning_on_ai_exclusion_during_analysis_discards_result():
    # 리뷰 재현: 내용 지문에 ai_excluded가 없어, 분석 중 제외를 켜도 결과가 저장되던 문제.
    c, store, adapter = make_client()
    m = new(c, title="제목", body="본문 내용")
    adapter.during = lambda: store.update(ME, "materials", m["id"], m["version"], {"ai_excluded": True})

    analyze(c, m)

    doc = store.get(ME, "materials", m["id"])
    assert doc["ai_excluded"] is True and doc.get("ai_title") is None
    assert doc["analysis_status"] == "awaiting_start" and doc["analysis_error"] == "ai_excluded"
    assert doc["analysis_request_sent"] is True  # 이미 보낸 요청은 사용량에 남긴다
    assert get(c, m)["ai_title"] is None


def test_result_from_older_prompt_version_can_be_reanalyzed(monkeypatch):
    # 리뷰 재현: 프롬프트 버전만 바뀐 결과는 화면에서 다시 분석할 방법이 없었다. 자동 호출은 하지 않는다.
    c, store, adapter = make_client()
    m = new(c)
    analyze(c, m)
    current = get(c, m)
    assert current["analysis_prompt_outdated"] is False

    store.transform(ME, "materials", m["id"], lambda d: {"analysis_prompt_version": "2026-10-02.1"})
    old = get(c, m)
    assert old["analysis_status"] == "done" and old["analysis_prompt_outdated"] is True
    assert old["analysis_outdated"] is False and len(adapter.calls) == 1  # 표시만, 호출 없음

    assert analyze(c, old).status_code == 202
    assert get(c, m)["analysis_prompt_outdated"] is False and len(adapter.calls) == 2


def test_result_without_prompt_version_counts_as_older():
    c, store, _ = make_client()
    m = new(c)
    analyze(c, m)
    store.transform(ME, "materials", m["id"], lambda d: {"analysis_prompt_version": None})
    assert get(c, m)["analysis_prompt_outdated"] is True


def test_edit_after_completion_marks_result_outdated_and_allows_new_analysis():
    c, _, adapter = make_client()
    m = new(c)
    analyze(c, m)
    edited = c.put(f"/api/materials/{m['id']}", json={"expected_version": m["version"], "body": "새 본문"},
                   headers=h()).json()
    assert edited["analysis_status"] == "done" and edited["analysis_outdated"] is True
    assert edited["ai_title"] == "AI 제목"  # 이전 결과는 남기되 화면이 '다시 분석 필요'로 표시한다
    assert analyze(c, edited).status_code == 202
    assert get(c, m)["analysis_outdated"] is False and len(adapter.calls) == 2


def test_failed_material_returns_to_awaiting_start_when_content_changes():
    c, _, adapter = make_client()
    adapter.outcomes = [ProviderError("timeout")]
    m = new(c)
    analyze(c, m)
    edited = c.put(f"/api/materials/{m['id']}", json={"expected_version": m["version"], "body": "새 본문"},
                   headers=h()).json()
    assert edited["analysis_status"] == "awaiting_start" and edited["analysis_error"] is None


def test_stale_version_is_rejected_without_call():
    c, _, adapter = make_client()
    m = new(c)
    c.put(f"/api/materials/{m['id']}", json={"expected_version": m["version"], "body": "새 본문"}, headers=h())
    res = analyze(c, m)
    assert res.status_code == 409 and adapter.calls == []


def test_refusals_never_call_provider():
    c, store, adapter = make_client()
    excluded = new(c, title="제목", ai_excluded=True)
    link_only = new(c, url="https://example.com/a")
    trashed = new(c, title="휴지통")
    store.update(ME, "materials", trashed["id"], trashed["version"], {"lifecycle": "trash"})
    trashed = get(c, trashed)

    reasons = [analyze(c, m).json().get("reason") for m in (excluded, link_only, trashed)]

    assert reasons == ["ai_excluded", "no_content", "trashed"]
    assert adapter.calls == []


def test_running_analysis_blocks_a_second_start():
    c, store, adapter = make_client()
    m = new(c)
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    store.transform(ME, "materials", m["id"], lambda doc: {
        "analysis_status": "analyzing", "analysis_job_id": "j1", "analysis_deadline_at": future})
    res = analyze(c, m)
    assert res.status_code == 409 and res.json()["reason"] == "analysis_in_progress"
    assert adapter.calls == []


def test_unfinished_job_after_restart_is_stale_and_user_can_retry():
    store = MemoryStore()
    c, _, _ = make_client(store=store)
    m = new(c)
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    store.transform(ME, "materials", m["id"], lambda doc: {
        "analysis_status": "analyzing", "analysis_job_id": "lost", "analysis_deadline_at": past})

    c2, _, adapter = make_client(store=store)  # 같은 저장소로 서버를 다시 켠 상황
    seen = get(c2, m)
    assert seen["analysis_status"] == "analyzing" and seen["analysis_stale"] is True
    assert adapter.calls == []  # 재시작만으로 몰래 다시 호출하지 않는다

    assert analyze(c2, seen).status_code == 202
    assert get(c2, m)["analysis_status"] == "done" and len(adapter.calls) == 1


def test_late_finish_of_superseded_job_is_ignored():
    c, store, _ = make_client()
    m = new(c)
    analyze(c, m)
    before = store.get(ME, "materials", m["id"])
    old = analysis.Job(m["id"], "old-job", "fp", dict(before), [])
    analysis.run_job(store, ME, old, lambda: FakeAdapter())
    assert store.get(ME, "materials", m["id"]) == before


def test_other_mode_cannot_analyze():
    c, _, adapter = make_client()
    m = new(c)
    assert analyze(c, m, mode="sample").status_code == 404
    assert adapter.calls == []


def test_request_validation():
    c, _, _ = make_client()
    m = new(c)
    no_version = c.post(f"/api/materials/{m['id']}/analyze", json={}, headers=h())
    no_key = c.post(f"/api/materials/{m['id']}/analyze", json={"expected_version": 1},
                    headers={"Authorization": "Bearer t", "X-Data-Mode": "personal"})
    assert no_version.status_code == 422 and no_key.status_code == 422
