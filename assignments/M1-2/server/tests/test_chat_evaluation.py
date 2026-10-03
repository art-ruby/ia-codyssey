"""T07.04 채팅 검색 품질 평가와 숫자 흐름(A14·A24).

- 고정 표본과 평가 세트를 실제 검색·채팅 경로로 채점한다(Provider만 가짜, scripts/evaluate_chat.py).
- 표본 CRUD → Summary → 같은 질문의 답(숫자 출처) 변화, 개인 자료 보관/휴지통 → 실제 보관 수 변화.
- 기본 요약과 질문 조건 요약이 출처·기간·지표·역할로 구분된다.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.features.chat import context as chat_context
from app.main import create_app
from test_chat_answers import ME, FakeAdapter, ask, fixed_now, h, make_client  # noqa: F401

SCRIPTS = Path(__file__).parents[1] / "scripts"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


evaluate_chat = _load("evaluate_chat")


# ── 검색 품질 ─────────────────────────────────────────────────────

def test_fixed_sample_evaluation_meets_a14():
    result = evaluate_chat.evaluate()
    assert result["answerable_total"] == 10 and result["no_evidence_total"] == 3
    assert result["answerable_found"] >= 8, evaluate_chat.markdown(result)
    assert result["no_evidence_ok"] == 3, evaluate_chat.markdown(result)
    assert result["invented_sources"] == 0
    # 가짜 Provider가 댄 없는 번호는 모든 질문에서 거부됐다.
    assert all(evaluate_chat.FAKE_NUMBER in r["rejected"] for r in result["rows"])
    assert all(r["status"] == 200 for r in result["rows"])


def test_report_lists_expected_actual_and_reason_per_question():
    report = evaluate_chat.markdown(evaluate_chat.evaluate())
    for case_id in ("q01", "q10", "n01", "n03"):
        assert f"| {case_id} " in report
    assert "정답 질문" in report and "존재하지 않는 출처 0건" in report


# ── 숫자 흐름 ─────────────────────────────────────────────────────

def _system_reference(adapter):
    content = adapter.calls[-1][0]["content"]
    return json.loads(content.split(chat_context.REFERENCE_START)[1].split(chat_context.REFERENCE_END)[0])


def _sample_client():
    """seed한 표본이 있는 저장소에 seed 소유자로 붙는 클라이언트."""
    store = evaluate_chat.seeded_store()
    adapter = FakeAdapter()
    owner = evaluate_chat.OWNER
    app = create_app(load_settings({"OWNER_UID": owner, "AI_DAILY_REQUEST_LIMIT": "50"}),
                     verify_token=lambda t: {"uid": owner}, store=store, analysis_adapter_factory=lambda: adapter)
    return TestClient(app), adapter


def test_sample_record_crud_changes_answer_numbers():
    c, adapter = _sample_client()
    question = "가상 보관 기록 추세는?"
    before = ask(c, question, mode="sample").json()["numbers"][0]
    assert before["label"] == "가상 보관 기록" and before["virtual"] is True

    created = c.post("/api/data", json={"date": before["period"]["end"], "metric_type": "kept_count", "value": 7},
                     headers=h("sample"))
    assert created.status_code == 201
    after = ask(c, question, mode="sample").json()["numbers"][0]
    assert after["total"] == before["total"] + 7
    assert _system_reference(adapter)["숫자 요약"][0]["total"] == after["total"]  # 모델에도 바뀐 값이 갔다

    record = created.json()
    deleted = c.delete(f"/api/data/{record['id']}", params={"expected_version": record["version"]}, headers=h("sample"))
    assert deleted.status_code == 200
    assert ask(c, question, mode="sample").json()["numbers"][0]["total"] == before["total"]


def test_personal_keep_and_trash_change_actual_kept_count():
    c, _ = make_client(FakeAdapter())
    question = "요즘 어때?"
    assert ask(c, question).json()["numbers"][0]["total"] == 0

    m = c.post("/api/materials", json={"title": "보관할 자료", "body": "본문"}, headers=h()).json()
    approved = c.post("/api/reviews/approve", headers=h(),
                      json={"items": [{"material_id": m["id"], "expected_version": m["version"]}]}).json()
    material = approved["results"][0]["material"]
    kept = ask(c, question).json()["numbers"][0]
    assert (kept["label"], kept["total"], kept["virtual"]) == ("현재 보관 자료 수", 1, False)

    moved = c.post("/api/reviews/approve", headers=h(), json={"items": [
        {"material_id": material["id"], "expected_version": material["version"], "action": "trash"}]})
    assert moved.status_code == 200
    assert ask(c, question).json()["numbers"][0]["total"] == 0


def test_default_and_question_summaries_are_distinguished():
    c, store = make_client(FakeAdapter())
    store.create(ME, "data", {"date": "2026-09-10", "metric_type": "kept_count", "value": 4, "memo": "",
                              "origin": "manual"})
    default, asked = ask(c, "지난달 내가 입력한 보관 기록 알려줘").json()["numbers"]
    assert (default["role"], default["source"], default["label"]) == ("default", "actual", "현재 보관 자료 수")
    assert (asked["role"], asked["source"], asked["label"]) == ("question", "manual", "사용자 입력 보관 기록")
    assert asked["period"] == {"start": "2026-09-10", "end": "2026-09-30"} and asked["total"] == 4
    assert default["total"] == 0  # 수기 기록을 실제 값에 더하지 않는다
