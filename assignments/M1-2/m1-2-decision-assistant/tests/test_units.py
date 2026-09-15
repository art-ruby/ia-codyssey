"""순수 로직 단위 테스트.

smoke_test.py 가 '실제로 뜨는가'를 보고, 이 파일은 '계산이 맞는가'를 본다.
둘 다 필요하다 — 서버가 떠도 요약이 틀릴 수 있고, 계산이 맞아도 서버가
안 뜰 수 있다.

    python -m pytest tests/test_units.py -q
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.adapters.sources import RadarSource, SampleSource, _clamp_score, _parse_dt  # noqa: E402
from app.models.schemas import Decision  # noqa: E402
from app.services.chat import build_candidate_refs, build_context_block, select_candidates  # noqa: E402
from app.services.summary import build_summary  # noqa: E402

NOW = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)


def candidate(days_ago: float, value: float, **extra):
    return {"date": NOW - timedelta(days=days_ago), "value": value, **extra}


# ── Summary ───────────────────────────────────────
class TestSummary:
    def test_empty_input_does_not_invent_numbers(self):
        summary = build_summary([], now=NOW)
        assert summary.count == 0
        assert summary.period == "데이터 없음"
        assert "계산하지 않았다" in summary.trend

    def test_basic_metrics(self):
        rows = [candidate(1, 10.0), candidate(2, 20.0), candidate(3, 90.0)]
        summary = build_summary(rows, now=NOW)
        assert summary.count == 3
        assert summary.metrics.max_score == 90.0
        assert summary.metrics.min_score == 10.0
        assert summary.metrics.average_score == 40.0

    def test_small_sample_refuses_to_call_a_trend(self):
        """표본이 적으면 추세를 단정하지 않는다. 이것이 M1-1 의 교훈이다."""
        summary = build_summary([candidate(1, 80.0), candidate(2, 20.0)], now=NOW)
        assert "판단 보류" in summary.trend

    def test_trend_detected_with_enough_samples(self):
        recent = [candidate(i % 7, 80.0) for i in range(8)]
        previous = [candidate(8 + (i % 6), 40.0) for i in range(8)]
        summary = build_summary(recent + previous, now=NOW)
        assert "상승" in summary.trend

    def test_undecided_counted_separately_from_skip(self):
        rows = [
            candidate(1, 50.0, decision="MAKE"),
            candidate(1, 50.0, decision="SKIP"),
            candidate(1, 50.0),  # 미정
        ]
        summary = build_summary(rows, now=NOW)
        assert summary.decisions.MAKE == 1
        assert summary.decisions.SKIP == 1
        assert summary.decisions.PENDING == 1

    def test_rows_without_usable_date_or_value_are_dropped(self):
        rows = [candidate(1, 50.0), {"date": None, "value": 10}, {"date": NOW, "value": "abc"}]
        assert build_summary(rows, now=NOW).count == 1

    def test_source_mix_is_reported(self):
        rows = [candidate(1, 50.0, source="sample"), candidate(1, 60.0, source="radar")]
        summary = build_summary(rows, now=NOW)
        assert summary.source_mix == {"sample": 1, "radar": 1}


# ── 어댑터 ────────────────────────────────────────
class TestAdapters:
    def test_score_outside_range_is_rejected_not_clamped(self):
        assert _clamp_score(50) == 50.0
        assert _clamp_score(120) is None
        assert _clamp_score(-1) is None
        assert _clamp_score("nope") is None

    def test_parse_dt_assumes_utc_when_naive(self):
        assert _parse_dt("2026-09-11").tzinfo is not None
        assert _parse_dt("") is None

    def test_sample_source_forces_sample_label(self, tmp_path):
        """파일이 radar 라고 주장해도 표본 소스는 sample 로 덮어쓴다."""
        path = tmp_path / "candidates.json"
        path.write_text(
            '{"candidates":[{"date":"2026-09-01T00:00:00Z","value":50,"source":"radar",'
            '"decision":"MAKE","topic":"t"}]}',
            encoding="utf-8",
        )
        rows = SampleSource(path).load()
        assert len(rows) == 1
        assert rows[0]["source"] == "sample"
        assert SampleSource(path).describe()["is_real_data"] is False

    def test_sample_source_drops_invalid_rows(self, tmp_path):
        path = tmp_path / "candidates.json"
        path.write_text(
            '{"candidates":[{"date":"bad","value":50},{"date":"2026-09-01T00:00:00Z","value":999},'
            '{"date":"2026-09-01T00:00:00Z","value":40}]}',
            encoding="utf-8",
        )
        assert len(SampleSource(path).load()) == 1

    def test_unknown_decision_becomes_none(self, tmp_path):
        path = tmp_path / "candidates.json"
        path.write_text(
            '{"candidates":[{"date":"2026-09-01T00:00:00Z","value":40,"decision":"NOT_RECORDED"}]}',
            encoding="utf-8",
        )
        assert SampleSource(path).load()[0]["decision"] is None

    def test_missing_file_is_not_an_error(self, tmp_path):
        assert SampleSource(tmp_path / "nope.json").load() == []

    def test_radar_v1_envelope_is_skipped_with_a_stated_reason(self):
        """실제 아카이브는 아직 schema_version 1 이고 점수 필드가 없다.

        건너뛰는 것 자체는 옳다 — 점수를 지어내면 안 된다. 다만 이유 없이
        0건만 주면 사용자는 원인을 알 수 없으므로 사유가 남아야 한다.
        """
        source = RadarSource(".")
        envelope = {"schema_version": 1, "created_at": "2026-09-10T00:00:00Z",
                    "payload": {"opportunity_id": "abc123", "topic": "t"}}
        assert source._from_payload(envelope["payload"], envelope, {}) is None
        assert any("schema_version 1" in reason for reason in source._skipped)

    def test_radar_v2_envelope_maps_score_and_date(self):
        source = RadarSource(".")
        envelope = {
            "schema_version": 2, "created_at": "2026-09-10T00:00:00Z",
            "payload": {
                "opportunity_id": "abc123", "topic": "年金 損",
                "target_channel": {"id": "loss_defense"},
                "demand": {"video_score": 72.5},
                "discovery": {"observed_at": "2026-09-09T00:00:00Z"},
                "decision": {"decision": "WATCH", "note": "관찰"},
            },
        }
        record = source._from_payload(envelope["payload"], envelope, {})
        assert record["value"] == 72.5
        assert record["channel"] == "loss_defense"
        assert record["decision"] == "WATCH"
        assert record["source"] == "radar"
        assert source._skipped == {}

    def test_radar_real_v2_shape_nested_under_production_signals(self):
        """2026-09-11 실물 패키지 모양. demand/discovery 가 production_signals 안에 있다.

        이전 어댑터는 최상위 demand 만 봐서 실물을 «점수 없음» 으로 건너뛰었다(§G-3).
        """
        source = RadarSource(".")
        envelope = {
            "schema_version": 2, "created_at": "2026-09-11T18:23:39+00:00",
            "payload": {
                "opportunity_id": "tV8q8bQ9vKc", "topic": "60대 집돌이",
                "target_channel": {"id": "loss_defense"},
                "decision": None,
                "production_signals": {
                    "schema_version": 1,
                    "demand": {"video_score": 95.0, "components": {}},
                    "discovery": {"observed_at": "2026-09-11 11:58:22.439854+00:00"},
                },
            },
        }
        record = source._from_payload(envelope["payload"], envelope, {})
        assert record is not None, source._skipped
        assert record["value"] == 95.0
        assert record["channel"] == "loss_defense"
        assert record["radar_id"] == "tV8q8bQ9vKc"
        assert record["date"].year == 2026 and record["date"].tzinfo is not None
        assert record["decision"] is None  # RADAR 쪽 decision 은 항상 None (감사 §G-3)

    def test_radar_sqlite_outbox_latest_revision_wins(self, tmp_path):
        """실제 저장소는 data/automaker-outbox/outbox.sqlite3 의 packages(id, revision, body)."""
        import json as _json
        import sqlite3 as _sqlite3

        db_dir = tmp_path / "data" / "automaker-outbox"
        db_dir.mkdir(parents=True)
        db = db_dir / "outbox.sqlite3"
        conn = _sqlite3.connect(db)
        conn.execute("CREATE TABLE packages (id TEXT, revision INTEGER, body TEXT, PRIMARY KEY(id, revision))")

        def body(rev, score):
            return _json.dumps({
                "schema_version": 2, "package_id": "radar-abc", "revision": rev,
                "created_at": "2026-09-11T00:00:00Z",
                "payload": {
                    "opportunity_id": "vid1", "topic": "t", "target_channel": {"id": "solo_pride"},
                    "production_signals": {
                        "demand": {"video_score": score},
                        "discovery": {"observed_at": "2026-09-10T00:00:00Z"},
                    },
                },
            })
        conn.execute("INSERT INTO packages VALUES (?,?,?)", ("radar-abc", 1, body(1, 60.0)))
        conn.execute("INSERT INTO packages VALUES (?,?,?)", ("radar-abc", 2, body(2, 77.0)))
        conn.commit(); conn.close()

        source = RadarSource(tmp_path)
        rows = source.load()
        assert len(rows) == 1
        assert rows[0]["value"] == 77.0  # revision 2 가 이긴다
        assert rows[0]["source"] == "radar"
        assert source.describe()["outbox_backend"] == "sqlite"

    def test_radar_v2_without_score_is_skipped(self):
        source = RadarSource(".")
        envelope = {"schema_version": 2, "created_at": "2026-09-10T00:00:00Z",
                    "payload": {"opportunity_id": "abc", "target_channel": {"id": "x"}}}
        assert source._from_payload(envelope["payload"], envelope, {}) is None
        assert any("점수" in reason for reason in source._skipped)


# ── Decisions ledger (RADAR decisions.jsonl 단일 정본) ────────────────────
class TestDecisionsLedger:
    """DA 가 쓴 줄을 RADAR 가 자기 것처럼 읽을 수 있어야 한다.

    RADAR src/decisions.py 의 규칙을 그대로 따른다: append-only, (video_id, channel_id)
    별 revision, decision_id 해시식. 해시식이 한 바이트라도 다르면 두 시스템의 id 가 갈린다.
    """

    @staticmethod
    def _radar_candidate(**over):
        base = {
            "id": "da-1", "radar_id": "tV8q8bQ9vKc", "channel": "loss_defense",
            "title": "T", "radar_score": 95.0, "source": "radar",
            "radar_package_id": "radar-7a73", "radar_payload_hash": "sha256:abcd",
            "radar_metrics": {"video_score": 95.0, "age_adjusted_percentile": 94.6},
        }
        base.update(over)
        return base

    def test_decision_id_matches_radar_formula(self):
        from app.services.decisions_ledger import decision_id_for
        import hashlib as _h, json as _j
        # RADAR decisions.py:freeze() 의 식을 여기 그대로 옮겨 적는다 (독립 계산).
        identity = _j.dumps(["loss_defense", "tV8q8bQ9vKc", 1], ensure_ascii=False, separators=(",", ":"))
        expected = "dec_" + _h.sha256(identity.encode("utf-8")).hexdigest()[:32]
        assert decision_id_for("loss_defense", "tV8q8bQ9vKc", 1) == expected
        assert decision_id_for("loss_defense", "tV8q8bQ9vKc", 2) != expected

    def test_append_is_append_only_and_revisions_increment(self, tmp_path):
        from app.services.decisions_ledger import DecisionsLedger
        ledger = DecisionsLedger(tmp_path, enabled=True)
        ok1, _, r1 = ledger.append(self._radar_candidate(), "WATCH", "먼저 본다")
        ok2, _, r2 = ledger.append(self._radar_candidate(), "MAKE", "만든다")
        assert ok1 and ok2
        assert (r1["revision"], r2["revision"]) == (1, 2)
        assert r1["decision_id"] != r2["decision_id"]
        lines = (tmp_path / "data" / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2  # 덮어쓰지 않았다
        assert r2["producer"] == "decision-assistant"
        assert r2["metrics"]["video_score"] == 95.0
        assert r2["payload_hash"] == "sha256:abcd"
        assert r2["config_digest"] is None  # 모르는 값을 지어내지 않는다

    def test_radar_lookup_rule_finds_last_line(self, tmp_path):
        """automaker_intake.py:90 — reversed(records) 에서 (video_id, channel_id) 첫 일치."""
        import json as _j
        from app.services.decisions_ledger import DecisionsLedger
        ledger = DecisionsLedger(tmp_path, enabled=True)
        ledger.append(self._radar_candidate(), "SKIP")
        ledger.append(self._radar_candidate(), "MAKE", "바꿈")
        ledger.append(self._radar_candidate(radar_id="other"), "WATCH")
        records = [_j.loads(l) for l in (tmp_path / "data" / "decisions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        found = next((d for d in reversed(records)
                      if d.get("video_id") == "tV8q8bQ9vKc" and d.get("channel_id") == "loss_defense"), None)
        assert found["decision"] == "MAKE" and found["note"] == "바꿈"
        assert ledger.latest_by_key()[("tV8q8bQ9vKc", "loss_defense")]["decision"] == "MAKE"

    def test_sample_and_manual_are_never_written(self, tmp_path):
        from app.services.decisions_ledger import DecisionsLedger
        ledger = DecisionsLedger(tmp_path, enabled=True)
        ok, reason, rec = ledger.append(self._radar_candidate(source="sample", radar_id="SAMPLE_0051"), "MAKE")
        assert not ok and rec is None and "표본" in reason or "sample" in reason
        assert not (tmp_path / "data" / "decisions.jsonl").exists()

    def test_disabled_flag_refuses_and_says_why(self, tmp_path):
        from app.services.decisions_ledger import DecisionsLedger
        ok, reason, _ = DecisionsLedger(tmp_path, enabled=False).append(self._radar_candidate(), "MAKE")
        assert not ok and "RADAR_DECISIONS_WRITE" in reason

    def test_reload_overlays_ledger_over_package_snapshot(self, tmp_path):
        """재시작 후 outbox 를 다시 읽어도 결정이 살아 있어야 한다 — 원장이 정본."""
        import json as _json
        import sqlite3 as _sqlite3
        from app.services.decisions_ledger import DecisionsLedger

        db_dir = tmp_path / "data" / "automaker-outbox"; db_dir.mkdir(parents=True)
        conn = _sqlite3.connect(db_dir / "outbox.sqlite3")
        conn.execute("CREATE TABLE packages (id TEXT, revision INTEGER, body TEXT, PRIMARY KEY(id, revision))")
        conn.execute("INSERT INTO packages VALUES (?,?,?)", ("radar-x", 1, _json.dumps({
            "schema_version": 2, "package_id": "radar-x", "payload_hash": "sha256:ff",
            "created_at": "2026-09-11T00:00:00Z",
            "payload": {"opportunity_id": "vidZ", "topic": "t", "target_channel": {"id": "solo_pride"},
                        "decision": None,
                        "production_signals": {"demand": {"video_score": 80.0, "components": {"svr_percentile": 90.1}},
                                               "discovery": {"observed_at": "2026-09-10T00:00:00Z"}}}})))
        conn.commit(); conn.close()

        first = RadarSource(tmp_path).load()
        assert first[0]["decision"] is None and first[0]["radar_metrics"]["svr_percentile"] == 90.1
        DecisionsLedger(tmp_path, enabled=True).append({**first[0], "id": "da-9"}, "MAKE", "근거")
        again = RadarSource(tmp_path).load()
        assert again[0]["decision"] == "MAKE" and again[0]["decision_reason"] == "근거"


# ── RADAR bridge (인계) ───────────────────────────────────────────────
class TestRadarBridge:
    """DA 는 AutoMaker 로 직접 보내지 않는다. RADAR 의 package/send 를 부르고 결과만 받는다."""

    def test_unavailable_without_radar_root(self):
        from app.services.radar_bridge import RadarBridge
        b = RadarBridge(None, automaker_url="http://127.0.0.1:5300")
        assert not b.available
        assert b.package_and_send("v", "c")["ok"] is False

    def test_sent_list_only_includes_assistant_decisions(self, tmp_path):
        """outbox 저널에서 producer=decision-assistant 결정이 실린 패키지만 고른다. 새 파일을 만들지 않는다."""
        import json as _j, sqlite3 as _s
        from app.services.radar_bridge import RadarBridge
        d = tmp_path / "data" / "automaker-outbox"; d.mkdir(parents=True)
        conn = _s.connect(d / "outbox.sqlite3")
        conn.execute("CREATE TABLE packages (id TEXT, revision INTEGER, body TEXT, PRIMARY KEY(id, revision))")
        def env(rev, decision):
            return _j.dumps({"package_id": "radar-x", "revision": rev, "created_at": f"2026-09-1{rev}T00:00:00+00:00",
                             "payload_hash": f"h{rev}",
                             "payload": {"opportunity_id": "vid", "topic": "t", "target_channel": {"id": "ch"},
                                         "decision": decision}})
        conn.execute("INSERT INTO packages VALUES (?,?,?)", ("radar-x", 1, env(1, None)))               # RADAR 자체 패키징
        conn.execute("INSERT INTO packages VALUES (?,?,?)", ("radar-x", 2, env(2, {"decision": "MAKE", "producer": "decision-assistant", "decision_id": "dec_1", "revision": 1})))
        conn.commit(); conn.close()
        rows = RadarBridge(tmp_path, automaker_url="http://127.0.0.1:5300").sent_by_assistant()
        assert [r["revision"] for r in rows] == [2]
        assert rows[0]["decision_id"] == "dec_1" and rows[0]["link"].endswith("package_id=radar-x")
        assert not any(p.suffix == ".json" for p in tmp_path.rglob("*"))  # 파일을 만들지 않았다

    def test_runner_gate_refuses_when_ledger_is_not_make(self, tmp_path, monkeypatch):
        """관문: RADAR payload.decision 이 MAKE 가 아니면 package 도 send 도 하지 않는다."""
        import json as _j, sys as _sys
        from app.services.radar_bridge import RadarBridge
        # 가짜 RADAR: src/automaker_intake.py 가 WATCH 결정을 실은 payload 를 돌려준다
        src = tmp_path / "src"; src.mkdir()
        (src / "__init__.py").write_text("", encoding="utf-8")
        (src / "config.py").write_text("ROOT = None\n", encoding="utf-8")
        (src / "source_pack.py").write_text("def load_selected(*a, **k): return None\ndef load(*a, **k): return None\n", encoding="utf-8")
        (src / "automaker_intake.py").write_text(
            "def build_payload(root, v, c, t, expected_source_pack_hash=None):\n"
            "    return {'opportunity_id': v, 'target_channel': {'id': c}, 'input_type': t,\n"
            "            'decision': {'decision': 'WATCH', 'producer': 'decision-assistant'}}\n"
            "def package_payload(p, o): raise AssertionError('must not package')\n"
            "def send(e, u): raise AssertionError('must not send')\n", encoding="utf-8")
        b = RadarBridge(tmp_path, automaker_url="http://127.0.0.1:5300", python=_sys.executable)
        r = b.package_and_send("vid", "ch")
        assert r["ok"] is False and r.get("gate") == "not_make" and "WATCH" in r["error"]
        # Source Pack 조회가 실패해도(파일 없음) 보고만 하고 관문 판정은 진행된다
        assert r["source_pack"]["included"] is False and r["source_pack"]["reason"]


# ── Persona draft parsing (AutoMaker radar_intake_api.py:57 과 같은 규칙) ─────
class TestPersonaDraft:
    def test_parses_fenced_json_like_automaker(self):
        from app.services.persona import parse_draft
        text = '```json\n{"persona":"  60대 샐러리맨 출신 화자 ","art_direction":{"name":"n","description":"d","prompt":"p"}}\n```'
        d = parse_draft(text)
        assert d["persona"] == "60대 샐러리맨 출신 화자"
        assert set(d["art_direction"]) == {"name", "description", "prompt"}

    def test_rejects_incomplete_art_direction(self):
        import pytest
        from app.services.persona import parse_draft
        with pytest.raises(ValueError):
            parse_draft('{"persona":"x","art_direction":{"name":"n","description":"d"}}')
        with pytest.raises(ValueError):
            parse_draft('{"persona":"   ","art_direction":{"name":"n","description":"d","prompt":"p"}}')
