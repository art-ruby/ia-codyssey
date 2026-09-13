"""채널 운영 판단 — Identity / Fit 상태 / 게이트 / Portfolio / 회귀(집돌이 소재).

    python -m pytest tests/test_judgment.py -q
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services import assessment as A  # noqa: E402
from app.services import fit_state as F  # noqa: E402
from app.services import identity as I  # noqa: E402
from app.services.radar_data import RadarData  # noqa: E402
from app.adapters.sources import RadarSource  # noqa: E402


# ── 픽스처: 최소 RADAR 루트 ─────────────────────────────────────────────────
PROFILE = {"id": "loss_defense", "name_ko": "정년 후 돈·연금·생활비", "audience": "50-69",
           "promise_ko": "연금·퇴직금·노후자금·생활비·보험·의료비·세금·절약의 재정 실수를 줄인다",
           "core_question_ko": "이 선택이 정년 전후 내 현금흐름과 자산에 손해를 끼치는가?",
           "tone_ko": "보통 샐러리맨이 겪은 실수와 반성",
           "lenses": ["pension_trap", "tax_shock", "insurance_cost", "caregiving_cost"],
           "profile_version": 3}

FIT_HEADER = ["video_id", "channel_id", "profile_version", "audience_fit", "channel_relevance", "money_impact",
              "problem_strength", "longform_potential", "news_risk", "evergreen_potential", "reason", "angle_ko",
              "analyzed_at"]


def make_root(tmp_path: Path, *, fit_rows: list[dict] | None = None) -> Path:
    (tmp_path / "data/config").mkdir(parents=True)
    (tmp_path / "data/config/channels.json").write_text(json.dumps([PROFILE], ensure_ascii=False), encoding="utf-8")
    (tmp_path / "data/processed").mkdir(parents=True)
    with open(tmp_path / "data/processed/channel_fit.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIT_HEADER)
        w.writeheader()
        for r in fit_rows or []:
            w.writerow({k: r.get(k, "") for k in FIT_HEADER})
    (tmp_path / "data/briefs/loss_defense").mkdir(parents=True)
    (tmp_path / "data/briefs/loss_defense/tV8q8bQ9vKc.md").write_text("## ■ 주제 (원 소재)\n- 60대 집돌이\n", encoding="utf-8")
    return tmp_path


def fit_row(version: int, relevance: str = "MEDIUM") -> dict:
    return {"video_id": "tV8q8bQ9vKc", "channel_id": "loss_defense", "profile_version": version,
            "audience_fit": "HIGH", "channel_relevance": relevance, "money_impact": "MEDIUM",
            "problem_strength": "HIGH", "longform_potential": "HIGH", "news_risk": "LOW",
            "evergreen_potential": "HIGH", "reason": "r", "angle_ko": "집돌이=경제 전략",
            "analyzed_at": "2026-09-11T18:22:43+00:00"}


IDENTITY = {
    "channel_id": "loss_defense", "identity_version": 1, "status": "approved", "built_on_profile_version": 3,
    "problem_space": "정년 전후 현금흐름·자산 손실 위험", "expectations": "재정 실수를 줄인다",
    "pillars": [{"id": "pension", "label": "연금·퇴직금", "description": "", "lenses": ["pension_trap"]},
                {"id": "living_cost", "label": "생활비·고정비", "description": "", "lenses": []},
                {"id": "insurance", "label": "보험·의료비", "description": "", "lenses": ["insurance_cost"]}],
    "boundary": {"in": ["정년 후 소비 감소", "고정비", "현금흐름"],
                 "out": ["홈트레이닝", "외로움", "실내 취미", "사회성"]},
    "narrator_pool": [
        {"id": "experience", "role_type": "경험형", "label": "전직 회사원", "viewpoint": "", "tone": "", "why_needed": ""},
        {"id": "analysis", "role_type": "분석형", "label": "숫자·제도", "viewpoint": "", "tone": "", "why_needed": ""},
        {"id": "living", "role_type": "생활형", "label": "가족·주거", "viewpoint": "", "tone": "", "why_needed": ""}],
}

CANDIDATE = {"id": "da-1", "radar_id": "tV8q8bQ9vKc", "channel": "loss_defense", "source": "radar",
             "title": "【必見】60代で賢い人ほど家にいたくなる理由", "topic": "60대 집돌이", "radar_score": 95.0, "value": 95.0}


# ── Fit 상태 모델 ───────────────────────────────────────────────────────────
class TestFitState:
    def test_not_evaluated_when_no_row(self, tmp_path):
        fit = F.evaluate(RadarData(make_root(tmp_path)), "tV8q8bQ9vKc", "loss_defense")
        assert fit["state"] == "NOT_EVALUATED" and fit["profile_version"] == 3

    def test_stale_when_only_old_version(self, tmp_path):
        """실물 사례: 프로필 v2→v3 뒤 v2 판정만 남음. 점수가 이를 덮으면 안 된다."""
        fit = F.evaluate(RadarData(make_root(tmp_path, fit_rows=[fit_row(2)])), "tV8q8bQ9vKc", "loss_defense")
        assert fit["state"] == "STALE" and "2 → 3" in fit["stale_reason"]
        assert fit["channel_relevance"] == "MEDIUM"  # 참고값은 보인다

    def test_valid_when_current_version(self, tmp_path):
        fit = F.evaluate(RadarData(make_root(tmp_path, fit_rows=[fit_row(2), fit_row(3)])), "tV8q8bQ9vKc", "loss_defense")
        assert fit["state"] == "VALID" and fit["evaluated_profile_version"] == "3"

    def test_invalid_when_fields_missing(self, tmp_path):
        row = fit_row(3)
        row["channel_relevance"] = ""
        fit = F.evaluate(RadarData(make_root(tmp_path, fit_rows=[row])), "tV8q8bQ9vKc", "loss_defense")
        assert fit["state"] == "INVALID"

    def test_basis_hash_ignores_version_number(self):
        a = F.basis_hash(PROFILE)
        b = F.basis_hash({**PROFILE, "profile_version": 4})
        c = F.basis_hash({**PROFILE, "promise_ko": "다른 약속"})
        assert a == b and a != c


# ── 게이트 규칙표 ───────────────────────────────────────────────────────────
class TestGates:
    M = {"level": "HIGH", "score": 95.0}
    P = {"duplicates": []}
    OK = {"pillar_confidence": "HIGH", "anchor_angle": "고정비", "boundary_risk": "LOW",
          "expansion_kind": "reinforce", "narrator_id": "experience"}
    VALID_HIGH = {"state": "VALID", "channel_relevance": "HIGH"}

    def test_score_never_overrides_unevaluated_fit(self):
        d = A.decide(IDENTITY, {"state": "STALE"}, self.M, self.P, None, has_brief=True)
        assert d["suggested"] == "REVIEW_REQUIRED" and any(b.startswith("fit_stale") for b in d["blockers"])

    def test_missing_identity_blocks(self):
        d = A.decide(None, self.VALID_HIGH, self.M, self.P, None, has_brief=True)
        assert d["suggested"] == "REVIEW_REQUIRED" and any(b.startswith("identity_missing") for b in d["blockers"])

    def test_low_relevance_is_skip_even_with_high_market(self):
        d = A.decide(IDENTITY, {"state": "VALID", "channel_relevance": "LOW"}, self.M, self.P, self.OK, has_brief=True)
        assert d["suggested"] == "SKIP" and d["gates"]["fit"] == "fail"

    def test_medium_relevance_needs_anchor(self):
        weak = {**self.OK, "pillar_confidence": "MEDIUM"}
        d = A.decide(IDENTITY, {"state": "VALID", "channel_relevance": "MEDIUM"}, self.M, self.P, weak, has_brief=True)
        assert d["suggested"] == "WATCH"
        d2 = A.decide(IDENTITY, {"state": "VALID", "channel_relevance": "MEDIUM"}, self.M, self.P, self.OK, has_brief=True)
        assert d2["suggested"] == "MAKE"

    def test_low_market_lowers_priority_not_skip(self):
        d = A.decide(IDENTITY, self.VALID_HIGH, {"level": "LOW", "score": 40}, self.P, self.OK, has_brief=True)
        assert d["suggested"] == "WATCH" and d["gates"]["market"] == "warn"

    def test_boundary_high_is_watch_and_drift_is_skip(self):
        d = A.decide(IDENTITY, self.VALID_HIGH, self.M, self.P, {**self.OK, "boundary_risk": "HIGH"}, has_brief=True)
        assert d["suggested"] == "WATCH"
        d2 = A.decide(IDENTITY, self.VALID_HIGH, self.M, self.P, {**self.OK, "expansion_kind": "drift"}, has_brief=True)
        assert d2["suggested"] == "SKIP"

    def test_duplicate_is_watch(self):
        dup = {"duplicates": [{"title": "t", "similarity": 0.5}]}
        d = A.decide(IDENTITY, self.VALID_HIGH, self.M, dup, self.OK, has_brief=True)
        assert d["suggested"] == "WATCH"

    def test_missing_brief_blocks_production(self):
        d = A.decide(IDENTITY, self.VALID_HIGH, self.M, self.P, self.OK, has_brief=False)
        assert d["suggested"] == "REVIEW_REQUIRED" and d["gates"]["production"] == "blocked"

    def test_all_pass_is_make(self):
        d = A.decide(IDENTITY, self.VALID_HIGH, self.M, self.P, self.OK, has_brief=True)
        assert d["suggested"] == "MAKE" and not d["blockers"]


# ── Portfolio 규칙 ──────────────────────────────────────────────────────────
class TestPortfolio:
    def test_duplicate_by_title_similarity_excludes_self(self):
        makes = [{"video_id": "tV8q8bQ9vKc", "title": CANDIDATE["title"]},
                 {"video_id": "other", "title": "【必見】60代で賢い人ほど家にいたくなる本当の理由"},
                 {"video_id": "far", "title": "年金 減額 の 落とし穴"}]
        p = A.portfolio_rules(CANDIDATE, makes, [])
        assert [d["video_id"] for d in p["duplicates"]] == ["other"]

    def test_pillar_balance_counts_past_assessments(self):
        p = A.portfolio_rules(CANDIDATE, [], [{"pillar": {"id": "pension"}}, {"pillar": {"id": "pension"}}, {"pillar": None}])
        assert p["pillar_balance"] == {"pension": 2, "unassigned": 1}


# ── Identity 승인 ───────────────────────────────────────────────────────────
class TestIdentity:
    def test_approve_bumps_version_and_locks_status(self, tmp_path):
        store = I.IdentityStore(tmp_path)
        store.save({**IDENTITY, "status": "proposed", "identity_version": 0})
        doc = I.approve("loss_defense", store)
        assert doc["status"] == "approved" and doc["identity_version"] == 1 and doc["approved_at"]
        again = I.approve("loss_defense", store, edits={"boundary": {"in": ["x"], "out": ["y"]}})
        assert again["identity_version"] == 2 and again["boundary"]["out"] == ["y"]

    def test_normalize_rejects_narrator_count_out_of_range(self):
        with pytest.raises(ValueError):
            I._normalize({"pillars": IDENTITY["pillars"], "narrator_pool": IDENTITY["narrator_pool"][:1]}, PROFILE)

    def test_summary_line(self):
        assert "Pillars" in I.summary_line(IDENTITY) and "Narrators" in I.summary_line(IDENTITY)


# ── 회귀: 집돌이 소재 ───────────────────────────────────────────────────────
class TestRegressionHomebody:
    """«외출을 줄이는 것이 돈을 지키는 전략인가» — 점수 95 · 관련성 MEDIUM · 프로필 v3 미평가.

    옛 DA: 점수만 보고 MAKE, 그 패키지로 채널 페르소나 생성.
    새 DA: (1) v3 미평가면 REVIEW_REQUIRED (2) 재판정 뒤에도 MEDIUM+boundary HIGH 면 WATCH(앵글 조건)
           (3) 왜 이 Episode 로 Identity 를 만들면 안 되는지 문장으로 남는다.
    """
    INTERP = {"pillar_id": "living_cost", "pillar_confidence": "MEDIUM",
              "anchor_angle": "정년 후 고정비·현금흐름 관점으로 고정",
              "boundary_risk": "HIGH",
              "boundary_reason": "안쪽: 소비 감소·고정비·교통비·외식비. 바깥: 홈트·외로움·실내 취미·사회성",
              "expansion_kind": "extend", "series_potential": "MEDIUM",
              "followups_in": ["정년 후 고정비 점검", "외식비·교통비 절감 현금흐름"],
              "followups_out": ["집 운동 루틴", "혼자 사는 법"],
              "narrator_id": "experience", "narrator_why": "실수·반성 회고 톤",
              "identity_caution": "이 소재는 living_cost 의 한 에피소드일 뿐이다. 이것으로 채널을 정의하면 집돌이 채널이 된다."}

    def test_stale_fit_blocks_regardless_of_score_95(self):
        fit = {"state": "STALE", "channel_relevance": "MEDIUM", "stale_reason": "profile_version 2 → 3"}
        d = A.decide(IDENTITY, fit, {"level": "HIGH", "score": 95.0}, {"duplicates": []}, None, has_brief=True)
        assert d["suggested"] == "REVIEW_REQUIRED"
        assert d["gates"]["fit"] == "blocked" and d["gates"]["market"] == "pass"

    def test_after_reevaluation_medium_plus_boundary_high_is_watch(self):
        fit = {"state": "VALID", "channel_relevance": "MEDIUM", "audience_fit": "HIGH", "money_impact": "MEDIUM"}
        d = A.decide(IDENTITY, fit, {"level": "HIGH", "score": 95.0}, {"duplicates": []}, self.INTERP, has_brief=True)
        assert d["suggested"] == "WATCH"
        text = " ".join(d["reasons"])
        assert "Boundary 위험 HIGH" in text and "관련성 MEDIUM" in text
        assert d["gates"] == {"fit": "warn", "market": "pass", "portfolio": "warn", "production": "pass"}

    def test_ledger_signals_carry_the_why(self):
        doc = {"assessed_at": "t", "identity_version": 1, "decision": {"suggested": "WATCH", "gates": {}},
               "market": {"level": "HIGH"}, "fit": {"state": "VALID", "channel_relevance": "MEDIUM"},
               "pillar": {"id": "living_cost", "anchor_angle": "고정비"},
               "portfolio": {"boundary_risk": "HIGH", "expansion_kind": "extend"},
               "series": {"potential": "MEDIUM"},
               "narrator": {"id": "experience", "label": "전직 회사원", "role_type": "경험형"}}
        s = A.ledger_signals(doc)
        assert s["assessment"]["suggested"] == "WATCH" and s["assessment"]["boundary_risk"] == "HIGH"
        assert s["narrator"]["id"] == "experience"

    def test_identity_is_not_derived_from_episode(self, tmp_path):
        """Identity 제안 입력에 패키지/브리프가 들어가지 않는다 — 채널 수준 입력만."""
        from app.services.decisions_ledger import DecisionsLedger
        root = make_root(tmp_path)
        inputs = I.gather_inputs(RadarData(root), DecisionsLedger(root, enabled=False), "loss_defense")
        assert set(inputs) == {"profile", "dna", "make_history", "performance"}
        assert inputs["profile"]["id"] == "loss_defense" and inputs["make_history"] == []


# ── RADAR 후보 풀 병합 ──────────────────────────────────────────────────────
class TestCandidatePool:
    def test_pool_rows_merge_with_outbox_and_key_is_video_x_channel(self, tmp_path):
        """같은 영상이 두 채널의 후보일 수 있다. 패키지가 있으면 패키지가 이긴다."""
        root = make_root(tmp_path)
        (root / "data/decision_assistant").mkdir(parents=True)
        (root / "data/decision_assistant/candidate_pool.json").write_text(json.dumps({"rows": [
            {"video_id": "v1", "channel_id": "loss_defense", "stage": "scored", "title": "A", "video_score": 88.0,
             "found_at": "2026-09-10T00:00:00Z", "metrics": {"video_score": 88.0, "svr_percentile": 90.0}},
            {"video_id": "v1", "channel_id": "solo_pride", "stage": "fit_judged", "title": "A", "video_score": 88.0,
             "found_at": "2026-09-10T00:00:00Z", "metrics": {"video_score": 88.0}},
            {"video_id": "bad", "channel_id": "loss_defense", "stage": "scored", "title": "no score", "video_score": None,
             "found_at": "2026-09-10T00:00:00Z", "metrics": {}},
        ]}, ensure_ascii=False), encoding="utf-8")
        rows = RadarSource(root).load()
        keys = {(r["radar_id"], r["channel"]) for r in rows}
        assert keys == {("v1", "loss_defense"), ("v1", "solo_pride")}
        assert {r["radar_stage"] for r in rows} == {"scored", "fit_judged"}
        assert all(r["source"] == "radar" for r in rows)
        src = RadarSource(root); src.load()
        assert src._skipped.get("풀 행에 점수/시점 없음") == 1  # 점수 없는 행은 지어내지 않고 뺀다
