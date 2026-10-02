"""T07.01 채팅 문맥: 질문 조건 추출·검증, 자료 검색과 자격 필터, 한도와 생략 표시, 과거 대화 재검사, 숫자 요약 주입.

Provider는 부르지 않는다. 만든 메시지(=보낼 요청)를 그대로 검사한다.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.chat import context as chat
from app.features.data import summary

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
SAMPLE = RequestContext(OWNER, "sample", None)
FIXTURES = Path(__file__).parent / "fixtures"
TODAY = datetime(2026, 10, 15, 3, 0, tzinfo=timezone.utc)  # 서울 2026-10-15(목)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(chat, "_now", lambda: TODAY)
    monkeypatch.setattr(summary, "_now", lambda: TODAY)


def seeded_sample_store():
    spec = importlib.util.spec_from_file_location("seed_sample", Path(__file__).parents[1] / "scripts" / "seed_sample.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store = MemoryStore()
    module.seed(store, OWNER)
    return store


def kept(store, ctx=ME, doc_id=None, **fields):
    data = {"source_type": "text", "title": "", "description": "", "body": "", "save_reason": "", "memo": "",
            "url": None, "review_status": "approved", "copy_status": "not_applicable", "lifecycle": "active",
            "ai_excluded": False, "registered_at": "2026-10-01T00:00:00+00:00",
            "storage_approved_at": "2026-10-01T00:00:00+00:00", **fields}
    return store.create(ctx, "materials", data, doc_id=doc_id)


def sent_text(result) -> str:
    return json.dumps(result.messages, ensure_ascii=False)


# ── 조건 추출 ─────────────────────────────────────────────────────

def test_manual_records_last_month_are_recognized():
    c = chat.extract_conditions("지난달 내가 입력한 보관 기록 알려줘", date(2026, 10, 15))
    assert (c.source, c.metric, c.start, c.end) == ("manual", "kept_count", "2026-09-01", "2026-09-30")
    assert c.explicit is True


@pytest.mark.parametrize("question, metric, start, end", [
    ("이번 달 접수 건수는?", "received_count", "2026-10-01", "2026-10-15"),
    ("최근 7일 보관 추세", "kept_count", "2026-10-09", "2026-10-15"),
    ("지난주 보관은 몇 건이야", "kept_count", "2026-10-05", "2026-10-11"),
])
def test_period_and_metric_phrases(question, metric, start, end):
    c = chat.extract_conditions(question, date(2026, 10, 15))
    assert (c.metric, c.start, c.end) == (metric, start, end)


def test_search_terms_drop_question_words_and_particles():
    c = chat.extract_conditions("정산 API는 언제 종료돼?", date(2026, 10, 15))
    assert {"정산", "api", "종료"} <= set(c.terms) and "언제" not in c.terms
    assert c.explicit is False


def test_question_too_long_is_rejected():
    with pytest.raises(chat.QuestionTooLong):
        chat.build_context(MemoryStore(), ME, "가" * (chat.MAX_QUESTION + 1))


# ── 자료 검색: 평가 세트 ───────────────────────────────────────────

CASES = json.loads((FIXTURES / "chat_cases.json").read_text(encoding="utf-8"))


def test_answerable_questions_find_expected_materials():
    store = seeded_sample_store()
    found = [set(c["expected_ids"]) <= set(chat.build_context(store, SAMPLE, c["question"]).source_ids)
             for c in CASES["answerable"]]
    assert sum(found) >= 8, found  # T07.04 기준: 10개 중 8개 이상
    assert all(found)  # 고정 표본에서는 10개 모두


@pytest.mark.parametrize("case", CASES["no_evidence"], ids=lambda c: c["id"])
def test_no_evidence_questions_get_no_materials(case):
    result = chat.build_context(seeded_sample_store(), SAMPLE, case["question"])
    assert result.source_ids == [] and result.omitted["no_materials"] is True


# ── 자격 필터와 Provider 요청 ──────────────────────────────────────

def test_ineligible_materials_never_reach_the_request():
    store = MemoryStore()
    kept(store, doc_id="ok", title="정산 일정 보관 자료", body="정산 마감 OKBODY")
    for name, change in {"unapproved": {"review_status": "unreviewed"}, "trashed": {"lifecycle": "trash"},
                         "deleting": {"lifecycle": "deleting"}, "excluded": {"ai_excluded": True}}.items():
        kept(store, doc_id=name, title=f"정산 일정 {name.upper()}TITLE", body=f"정산 마감 {name.upper()}BODY", **change)
    result = chat.build_context(store, ME, "정산 마감 일정 알려줘")
    text = sent_text(result)
    assert result.source_ids == ["ok"] and "OKBODY" in text
    for name in ("UNAPPROVED", "TRASHED", "DELETING", "EXCLUDED"):
        assert f"{name}TITLE" not in text and f"{name}BODY" not in text
    assert '"ok"' not in text  # 자료 ID는 보내지 않는다(근거 확인은 서버가 source_ids로)


def test_reference_data_goes_to_system_and_question_alone_to_user():
    store = MemoryStore()
    kept(store, doc_id="ok", title="정산 일정", body="정산 마감은 10월 말")
    question = "정산 마감 일정은?"
    result = chat.build_context(store, ME, question)
    system, user = result.messages[0], result.messages[-1]
    assert system["role"] == "system" and chat.REFERENCE_START in system["content"]
    assert "정산 마감은 10월 말" in system["content"]
    assert "현재 보관 자료 수" in system["content"]  # 기본 숫자 요약도 system에
    assert user == {"role": "user", "content": question}


# ── 한도 ─────────────────────────────────────────────────────────

def test_material_count_and_body_limits_are_reported():
    store = MemoryStore()
    for i in range(7):
        kept(store, doc_id=f"m{i}", title=f"정산 보고 {i}", body="정산 " + "가" * 6000,
             registered_at=f"2026-10-0{i + 1}T00:00:00+00:00")
    result = chat.build_context(store, ME, "정산 보고 정리")
    assert len(result.source_ids) == chat.MAX_MATERIALS == 5
    assert result.omitted["materials_over_limit"] == 2
    data = json.loads(result.messages[0]["content"].split(chat.REFERENCE_START)[1].split(chat.REFERENCE_END)[0])
    assert sum(len(m.get("body", "")) for m in data["materials"]) <= chat.MAX_BODY_CHARS
    assert result.omitted["body_truncated"] is True


# ── 과거 대화 재검사 ───────────────────────────────────────────────

def test_history_with_now_ineligible_sources_is_dropped():
    store = MemoryStore()
    kept(store, doc_id="ok", title="정산 일정", body="정산 마감")
    kept(store, doc_id="gone", title="옛 자료", body="OLDQUOTE", lifecycle="trash")
    history = [
        {"role": "user", "content": "옛 질문"}, {"role": "assistant", "content": "OLDQUOTE 인용 답변", "source_ids": ["gone"]},
        {"role": "user", "content": "정산 질문"}, {"role": "assistant", "content": "정산 마감 답변", "source_ids": ["ok"]},
    ]
    result = chat.build_context(store, ME, "정산 마감 다시 알려줘", history)
    text = sent_text(result)
    assert "OLDQUOTE" not in text and "옛 질문" not in text  # 답변과 그 질문을 함께 뺀다
    assert "정산 마감 답변" in text and result.omitted["history_dropped"] == 2


def test_only_last_six_valid_history_messages_are_sent():
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"메시지{i}"} for i in range(10)]
    result = chat.build_context(MemoryStore(), ME, "질문", history)
    roles = [m["role"] for m in result.messages]
    assert roles.count("user") + roles.count("assistant") == 6 + 1  # 이력 6개 + 이번 질문
    assert "메시지3" not in sent_text(result) and "메시지4" in sent_text(result)


def test_history_from_other_mode_is_not_trusted():
    store = MemoryStore()
    kept(store, ctx=SAMPLE, doc_id="sample-only", title="표본", body="SAMPLEQUOTE")
    history = [{"role": "user", "content": "q"},
               {"role": "assistant", "content": "SAMPLEQUOTE", "source_ids": ["sample-only"]}]
    result = chat.build_context(store, ME, "질문", history)
    assert "SAMPLEQUOTE" not in sent_text(result)


# ── 숫자 요약 ─────────────────────────────────────────────────────

def test_default_summary_per_mode():
    personal = chat.build_context(MemoryStore(), ME, "요즘 어때?")
    assert [(s["source"], s["metric_type"]) for s in personal.summaries] == [("actual", "kept_count")]
    sample = chat.build_context(seeded_sample_store(), SAMPLE, "요즘 어때?")
    assert [(s["source"], s["label"]) for s in sample.summaries] == [("sample", "가상 보관 기록")]


def test_manual_records_are_separate_and_never_summed_with_actual():
    store = MemoryStore()
    kept(store, title="실제 보관 자료")  # 실제 보관 1건(10월)
    store.create(ME, "data", {"date": "2026-09-10", "metric_type": "kept_count", "value": 7, "memo": "", "origin": "manual"})
    result = chat.build_context(store, ME, "지난달 내가 입력한 보관 기록 알려줘")
    by_source = {s["source"]: s for s in result.summaries}
    assert by_source["actual"]["total"] == 1 and by_source["actual"]["label"] == "현재 보관 자료 수"
    assert by_source["manual"]["total"] == 7
    assert by_source["manual"]["period"] == {"start": "2026-09-10", "end": "2026-09-30"}
    assert by_source["manual"]["label"] == "사용자 입력 보관 기록"


def test_actual_received_count_is_excluded_until_decided():
    result = chat.build_context(MemoryStore(), ME, "이번 달 실제 접수 건수는?")
    assert all(s["metric_type"] != "received_count" for s in result.summaries)
    assert result.omitted["received_actual_excluded"] is True


def test_sample_received_count_is_allowed():
    result = chat.build_context(seeded_sample_store(), SAMPLE, "가상 접수 기록 추세는?")
    assert any(s["metric_type"] == "received_count" and s["source"] == "sample" for s in result.summaries)


def test_joined_received_record_is_not_read_as_manual():
    # '접수기록'을 붙여 쓰면 안에 '수기'가 생기지만 수기 기록 요청이 아니다.
    c = chat.extract_conditions("가상 접수기록 추세는?", date(2026, 10, 15))
    assert (c.source, c.metric) == ("sample", "received_count")
    assert chat.extract_conditions("수기 보관 기록", date(2026, 10, 15)).source == "manual"
