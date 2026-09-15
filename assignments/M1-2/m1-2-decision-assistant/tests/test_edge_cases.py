"""예외·경계 상황 테스트 (명세 8절).

정상 흐름은 test_units.py 와 smoke_test.py 가 본다. 여기서는 «틀린 입력이
들어왔을 때 조용히 그럴듯한 답을 내지 않는가»를 본다. 조용한 실패가
가장 위험하다.

    python -m pytest tests/test_edge_cases.py -q
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import Settings  # noqa: E402
from app.models.schemas import CandidateCreate, Decision  # noqa: E402
from app.repositories.store import InMemoryStore  # noqa: E402
from app.services.chat import (  # noqa: E402
    build_context_block,
    generate_reply,
    select_candidates,
)
from app.services.summary import build_summary  # noqa: E402

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)


def row(days_ago: float, value: float, **extra):
    return {"date": NOW - timedelta(days=days_ago), "value": value, **extra}


# ── 빈 데이터 ─────────────────────────────────────
class TestEmptyData:
    def test_summary_on_empty_store(self):
        summary = build_summary([], now=NOW)
        assert summary.count == 0
        assert summary.metrics.average_score == 0.0
        assert summary.decisions.MAKE == 0

    def test_context_block_with_no_candidates_says_none(self):
        block = build_context_block(build_summary([], now=NOW), [], "top_score")
        assert "- (없음)" in block

    def test_reply_with_no_candidates_does_not_invent(self):
        settings = Settings()
        settings.openai_api_key = ""  # 키 없이 규칙 기반 경로
        reply, model, source = generate_reply(
            question="뭐 만들까?", summary=build_summary([], now=NOW),
            candidates=[], history=[], settings=settings, basis="top_score",
        )
        assert "없는 소재를 만들어 답하지 않습니다" in reply
        assert model.startswith("rule-based")
        assert source == "rule_based"


# ── null / 누락 필드 ──────────────────────────────
class TestMissingFields:
    def test_summary_skips_rows_missing_date_or_value(self):
        rows = [row(1, 50.0), {"value": 10}, {"date": NOW}, {"date": None, "value": None}]
        assert build_summary(rows, now=NOW).count == 1

    def test_candidate_without_optional_fields_is_valid(self):
        model = CandidateCreate(date=NOW, value=50.0)
        assert model.memo == ""
        assert model.channel is None
        assert model.decision is None

    def test_context_block_tolerates_null_title_and_channel(self):
        rows = [row(1, 50.0, title=None, channel=None, topic=None)]
        block = build_context_block(build_summary(rows, now=NOW), rows, "keyword")
        assert "(제목 없음)" in block

    def test_naive_datetime_gets_timezone(self):
        model = CandidateCreate(date=datetime(2026, 9, 1, 0, 0), value=10.0)
        assert model.date.tzinfo is not None


# ── 잘못된 decision 값 ────────────────────────────
class TestInvalidDecision:
    def test_pydantic_rejects_unknown_decision(self):
        with pytest.raises(Exception):
            CandidateCreate(date=NOW, value=50.0, decision="MAYBE")

    def test_summary_counts_garbage_decision_as_pending(self):
        summary = build_summary([row(1, 50.0, decision="MAYBE")], now=NOW)
        assert summary.decisions.PENDING == 1
        assert summary.decisions.MAKE == 0

    def test_valid_decisions_are_exactly_three(self):
        assert {d.value for d in Decision} == {"MAKE", "WATCH", "SKIP"}


# ── 선별 근거 ─────────────────────────────────────
class TestSelectionBasis:
    def _pool(self):
        return [
            row(1, 90.0, channel="loss_defense", topic="年金 損", title="A", decision="MAKE"),
            row(2, 60.0, channel="solo_pride", topic="定年後 孤独", title="B", decision="WATCH"),
            row(3, 20.0, channel="solo_pride", topic="熟年離婚", title="C",
                memo="채널 적합성은 높으나 경쟁 과열"),
        ]

    def test_decision_query_filters_by_state(self):
        picked, basis = select_candidates("MAKE 후보만 보여줘", self._pool())
        assert basis == "decision"
        assert len(picked) == 1 and picked[0]["title"] == "A"

    def test_keyword_query_matches_channel(self):
        picked, basis = select_candidates("loss_defense 채널 후보", self._pool())
        assert basis == "keyword"
        assert picked[0]["channel"] == "loss_defense"

    def test_absent_entity_falls_back_and_says_so(self):
        """없는 채널을 물으면 '일치했다'고 말하면 안 된다."""
        picked, basis = select_candidates("money_retirement 채널 후보가 있다면 알려줘", self._pool())
        assert basis == "top_score"
        block = build_context_block(build_summary(self._pool(), now=NOW), picked, basis)
        assert "일치한 후보가 없어" in block

    def test_generic_word_in_memo_does_not_count_as_match(self):
        """'채널'이 memo 에 있다고 일치로 세면 없는 채널도 있다고 답하게 된다."""
        _, basis = select_candidates("없는채널xyz 채널 후보 알려줘", self._pool())
        assert basis == "top_score"

    def test_empty_state_query_falls_back_instead_of_empty_list(self):
        pool = [row(1, 50.0, decision="SKIP", title="only skip")]
        picked, basis = select_candidates("MAKE 후보만 보여줘", pool)
        # MAKE 가 0건이면 빈 목록 대신 점수 상위로 떨어지되 근거를 밝힌다.
        assert basis == "top_score"
        assert picked


# ── 외부 의존성 실패 ──────────────────────────────
class TestDependencyFailures:
    def test_openai_error_falls_back_and_reports(self, monkeypatch):
        """모델 호출이 실패해도 500 을 던지지 않고, 실패 사실을 답변에 밝힌다."""
        pytest.importorskip("openai", reason="openai 미설치 — 아래 패키지 부재 테스트가 그 경우를 본다")
        settings = Settings()
        settings.openai_api_key = "sk-invalid-for-test"

        class Boom:
            def __init__(self, *a, **k):
                raise RuntimeError("connection refused")

        monkeypatch.setattr("openai.OpenAI", Boom)
        reply, model, source = generate_reply(
            question="추천해줘", summary=build_summary([row(1, 50.0)], now=NOW),
            candidates=[row(1, 50.0)], history=[], settings=settings, basis="top_score",
        )
        assert "OpenAI 호출 실패" in reply
        assert model == "error-fallback"
        assert source == "error_fallback"

    def test_missing_openai_package_is_explained_not_crashed(self, monkeypatch):
        """키만 있고 패키지가 없을 때 500 대신 할 일을 알려준다.

        실제로 이 환경이 그랬다. 키를 넣는 순간 ImportError 로 죽었을 것이다.
        """
        settings = Settings()
        settings.openai_api_key = "sk-test"

        import builtins

        real_import = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == "openai":
                raise ImportError("No module named 'openai'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", blocked)
        reply, model, source = generate_reply(
            question="추천해줘", summary=build_summary([row(1, 50.0)], now=NOW),
            candidates=[row(1, 50.0)], history=[], settings=settings, basis="top_score",
        )
        assert "openai 패키지가 설치되어 있지 않습니다" in reply
        assert "pip install" in reply
        assert model == "error-missing-package"
        assert source == "missing_package"

    def test_firestore_unconfigured_falls_back_to_memory(self):
        settings = Settings()
        settings.firebase_service_account_json = ""
        assert settings.firestore_enabled is False
        assert settings.mode_banner().find("in-memory") > 0

    def test_memory_store_reports_missing_ids(self):
        store = InMemoryStore()
        assert store.get_candidate("nope") is None
        assert store.update_candidate("nope", {"memo": "x"}) is None
        assert store.delete_candidate("nope") is False
        assert store.get_conversation("nope") is None
        assert store.delete_conversation("nope") is False


# ── 전체 표본 규모 ────────────────────────────────
class TestFullDataset:
    def test_summary_over_full_sample_file(self):
        import json

        path = Path(__file__).resolve().parents[1] / "sample_data" / "candidates.json"
        rows = json.loads(path.read_text(encoding="utf-8"))["candidates"]
        assert len(rows) >= 100, "과제 요건: 100건 이상"

        summary = build_summary(rows)
        assert summary.count == len(rows)
        total = (summary.decisions.MAKE + summary.decisions.WATCH
                 + summary.decisions.SKIP + summary.decisions.PENDING)
        assert total == len(rows), "결정 분포 합계가 전체와 같아야 한다"
        assert 0 <= summary.metrics.min_score <= summary.metrics.average_score <= summary.metrics.max_score <= 100


# ── Context Injection 증명 ────────────────────────
class TestContextInjection:
    """Summary·후보가 실제로 system context 에 들어가는지 테스트로 증명한다.

    운영 API 를 열지 않고 증명한다. 답변 문장으로는 증명되지 않는다 —
    모델이 우연히 맞게 말할 수도 있기 때문이다. 여기서는 모델에 보내기 직전의
    문자열을 직접 조사한다.
    """

    def _pool(self):
        return [
            row(1, 91.5, channel="loss_defense", topic="年金 損", title="가", decision="MAKE"),
            row(2, 33.0, channel="solo_pride", topic="熟年離婚", title="나", decision="SKIP"),
        ]

    def test_summary_numbers_appear_in_prompt(self):
        pool = self._pool()
        summary = build_summary(pool, now=NOW)
        block = build_context_block(summary, pool, "keyword")

        assert summary.period in block
        assert f"{summary.count}건" in block
        assert str(summary.metrics.average_score) in block
        assert str(summary.metrics.max_score) in block
        assert summary.trend in block
        assert f"MAKE {summary.decisions.MAKE}" in block

    def test_每_candidate_appears_with_number_and_fields(self):
        pool = self._pool()
        block = build_context_block(build_summary(pool, now=NOW), pool, "keyword")
        for index, item in enumerate(pool, start=1):
            assert f"#{index}" in block
            assert item["title"] in block
            assert item["channel"] in block
            assert str(item["value"]) in block

    def test_sample_and_real_are_labelled_differently(self):
        rows = [row(1, 50.0, title="표본", source="sample"),
                row(1, 60.0, title="실측", source="radar")]
        block = build_context_block(build_summary(rows, now=NOW), rows, "keyword")
        assert "[표본]" in block and "[실측]" in block

    def test_prompt_sent_to_model_contains_context(self, monkeypatch):
        """generate_reply 가 실제로 그 블록을 system 메시지로 보내는지 확인한다."""
        pytest.importorskip("openai")
        captured = {}

        class FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)

                class Msg:
                    content = "ok"

                class Choice:
                    message = Msg()

                class Result:
                    choices = [Choice()]

                return Result()

        class FakeClient:
            def __init__(self, *a, **k):
                self.chat = type("C", (), {"completions": FakeCompletions()})()

        monkeypatch.setattr("openai.OpenAI", FakeClient)
        settings = Settings()
        settings.openai_api_key = "sk-test"

        pool = self._pool()
        summary = build_summary(pool, now=NOW)
        reply, model, source = generate_reply(
            question="MAKE 후보 알려줘", summary=summary, candidates=pool,
            history=[], settings=settings, basis="decision",
        )

        assert source == "openai", "정상 호출이면 출처가 openai 여야 한다"
        system = captured["messages"][0]
        assert system["role"] == "system"
        # 요약 수치와 후보가 실제로 system 메시지 안에 있다
        assert f"{summary.count}건" in system["content"]
        assert str(summary.metrics.average_score) in system["content"]
        assert "#1" in system["content"] and pool[0]["title"] in system["content"]
        # 마지막 메시지는 사용자 질문
        assert captured["messages"][-1] == {"role": "user", "content": "MAKE 후보 알려줘"}
        # 과금 통제
        assert captured["max_tokens"] == settings.openai_max_tokens


# ── DEBUG 게이트 ──────────────────────────────────
class TestDebugGate:
    """system prompt 를 돌려주는 진단 경로가 운영에서 닫혀 있어야 한다."""

    def test_debug_defaults_to_off(self, monkeypatch):
        monkeypatch.delenv("DEBUG", raising=False)
        assert Settings().debug is False

    @pytest.mark.parametrize("value,expected", [
        ("true", True), ("1", True), ("on", True), ("yes", True),
        ("false", False), ("0", False), ("", False), ("maybe", False),
    ])
    def test_debug_parsing(self, monkeypatch, value, expected):
        monkeypatch.setenv("DEBUG", value)
        assert Settings().debug is expected


# ── OpenAI 호환 프록시 ────────────────────────────
class TestCompatibleProxy:
    """과정에서 제공하는 게이트웨이처럼 OpenAI 호환 프록시를 쓸 수 있어야 한다.

    base_url 을 지정하지 않으면 SDK 가 api.openai.com 으로 보내므로,
    프록시용 virtual-key 는 401 이 난다. 설정이 실제로 클라이언트까지
    전달되는지 확인한다.
    """

    def test_base_url_defaults_to_empty(self, monkeypatch):
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
        assert Settings().openai_base_url == ""

    def test_default_model_is_gateway_model(self, monkeypatch):
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        assert Settings().openai_model == "gpt-5-mini"

    def test_base_url_reaches_the_client(self, monkeypatch):
        pytest.importorskip("openai")
        captured = {}

        class FakeClient:
            def __init__(self, **kwargs):
                captured.update(kwargs)

                class Completions:
                    def create(self, **kw):
                        class Msg:
                            content = "ok"

                        class Choice:
                            message = Msg()

                        class Result:
                            choices = [Choice()]

                        return Result()

                self.chat = type("C", (), {"completions": Completions()})()

        monkeypatch.setattr("openai.OpenAI", FakeClient)
        settings = Settings()
        settings.openai_api_key = "virtual-key-test"
        settings.openai_base_url = "https://copa.codyssey.kr/v1"

        generate_reply(
            question="q", summary=build_summary([row(1, 50.0)], now=NOW),
            candidates=[row(1, 50.0)], history=[], settings=settings, basis="top_score",
        )
        assert captured["base_url"] == "https://copa.codyssey.kr/v1"
        assert captured["api_key"] == "virtual-key-test"

    def test_no_base_url_means_no_kwarg(self, monkeypatch):
        """비어 있으면 base_url 인자를 아예 넘기지 않아야 SDK 기본값이 산다."""
        pytest.importorskip("openai")
        captured = {}

        class FakeClient:
            def __init__(self, **kwargs):
                captured.update(kwargs)

                class Completions:
                    def create(self, **kw):
                        class Msg:
                            content = "ok"

                        class Choice:
                            message = Msg()

                        class Result:
                            choices = [Choice()]

                        return Result()

                self.chat = type("C", (), {"completions": Completions()})()

        monkeypatch.setattr("openai.OpenAI", FakeClient)
        settings = Settings()
        settings.openai_api_key = "sk-real"
        settings.openai_base_url = ""

        generate_reply(
            question="q", summary=build_summary([row(1, 50.0)], now=NOW),
            candidates=[row(1, 50.0)], history=[], settings=settings, basis="top_score",
        )
        assert "base_url" not in captured
