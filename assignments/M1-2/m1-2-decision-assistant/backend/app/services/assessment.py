"""Episode Assessment — «이 소재를 이 채널에서 만드는 것이 장기 운영에 도움이 되는가».

네 층을 따로 본다. 점수는 그중 하나의 입력일 뿐이다.
  A. Market Opportunity  — RADAR 패키지의 demand·growth·patterns·similar (재계산 없음)
  B. Channel Fit         — RADAR channel_fit 판정 + 상태 모델(VALID/STALE/NOT_EVALUATED/INVALID)
  C. Portfolio Fit       — 승인된 MAKE 이력과의 중복·편중·정체성 이동(boundary)·확장 종류
  D. Narrator Fit        — Identity 의 narrator_pool 중 설명 관점이 맞는 역할 (Fit·MAKE 판단보다 아래 층)

규칙 게이트가 먼저, AI 는 «해석» 한 곳(pillar·boundary·series·narrator)에만. 최종 MAKE/WATCH/SKIP 은 사람이.
결과는 RADAR `data/decision_assistant/assessments/<channel>/<video>.json` 에 남고 근거를 추적할 수 있다.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import Settings
from .decisions_ledger import DecisionsLedger
from .fit_state import evaluate as evaluate_fit
from .identity import IdentityStore
from .llm import ask_json
from .radar_data import RadarData

def _fill(template: str, **values: Any) -> str:
    """JSON 예시가 든 템플릿은 str.format 을 쓸 수 없다(중괄호 충돌). «name» 자리만 바꾼다."""
    for k, v in values.items():
        template = template.replace("«" + k + "»", str(v))
    return template


REL_DIR = Path("data") / "decision_assistant" / "assessments"
LEVELS = ("LOW", "MEDIUM", "HIGH")

INTERPRET_PROMPT = """당신은 채널 운영 판단 보조자다. 아래 «채널 운영 기준(Identity)» 을 기준으로 «소재 하나» 를 해석하라.
소재로 채널을 재정의하지 않는다. 채널 기준에 소재를 비춘다.

반드시 JSON 만 반환한다:
{
  "pillar_id": "Identity.pillars 중 하나의 id (없으면 null)",
  "pillar_confidence": "LOW|MEDIUM|HIGH",
  "anchor_angle": "이 소재를 채널 안쪽에 고정하는 앵글 한 문장 (예: 정년 후 고정비·현금흐름 관점)",
  "boundary_risk": "LOW|MEDIUM|HIGH  — 이 소재에서 파생되는 방향이 boundary.out 으로 흐를 위험",
  "boundary_reason": "한두 문장. 어떤 파생 방향이 안쪽이고 어떤 것이 바깥쪽인지",
  "expansion_kind": "reinforce|extend|drift  — 기존 영역 강화 / 유효한 새 확장 / 정체성 이동",
  "series_potential": "LOW|MEDIUM|HIGH",
  "followups_in": ["채널 안쪽으로 이어질 후속 소재 2~4개"],
  "followups_out": ["바깥으로 새는 후속 소재 2~4개 — 만들지 말 것"],
  "narrator_id": "Identity.narrator_pool 중 하나의 id",
  "narrator_why": "이 설명 관점이 맞는 이유 한 문장",
  "identity_caution": "왜 이 Episode 하나로 채널 Identity 를 다시 만들면 안 되는지 한두 문장"
}

[채널 운영 기준 — Identity v«identity_version»]
«identity»

[소재]
«candidate»

[RADAR 적합성 판정 (참고)]
«fit»

[승인된 MAKE 이력 — «make_count»건]
«make_history»
"""


# ── A. Market ──────────────────────────────────────────────────────────────────
def market_opportunity(package: dict[str, Any] | None, fit: dict[str, Any], fallback_score: float | None) -> dict[str, Any]:
    signals = ((package or {}).get("payload") or {}).get("production_signals") or {}
    demand = signals.get("demand") or {}
    score = demand.get("video_score", fallback_score)
    growth = demand.get("growth") or {}
    patterns = signals.get("patterns") or []
    similar = signals.get("similar") or {}
    level = "HIGH" if (score or 0) >= 80 else "MEDIUM" if (score or 0) >= 60 else "LOW"
    notes = []
    if patterns:
        notes.append(f"반복 패턴 {len(patterns)}건 — 단발이 아닐 근거")
    if similar.get("n"):
        notes.append(f"유사 소재 {similar.get('n')}건(채널 {similar.get('channels')}개) — 경쟁·포화 참고")
    if growth.get("velocity_trend"):
        notes.append(f"속도 추세 {growth.get('velocity_trend')}")
    return {
        "level": level, "score": score,
        "growth": {k: growth.get(k) for k in ("velocity_trend", "view_gain", "elapsed_hours") if k in growth},
        "repeat_patterns": len(patterns), "similar": {k: similar.get(k) for k in ("n", "channels", "recent") if k in similar},
        "longform_potential": fit.get("longform_potential"), "evergreen_potential": fit.get("evergreen_potential"),
        "notes": notes,
    }


# ── C. Portfolio (규칙 부분) ────────────────────────────────────────────────
def _bigrams(text: str) -> set[str]:
    t = "".join(ch for ch in (text or "") if ch.isalnum())
    return {t[i:i + 2] for i in range(len(t) - 1)} if len(t) > 1 else set()


def _similarity(a: str, b: str) -> float:
    x, y = _bigrams(a), _bigrams(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def portfolio_rules(candidate: dict[str, Any], makes: list[dict[str, Any]], past_assessments: list[dict[str, Any]]) -> dict[str, Any]:
    me = str(candidate.get("radar_id") or "")
    title = f"{candidate.get('title') or ''} {candidate.get('topic') or ''}"
    dups = []
    for m in makes:
        if str(m.get("video_id")) == me:
            continue
        s = _similarity(title, f"{m.get('title') or ''}")
        if s >= 0.35:
            dups.append({"video_id": m.get("video_id"), "title": m.get("title"), "similarity": round(s, 2)})
    balance: dict[str, int] = {}
    for a in past_assessments:
        pid = ((a.get("pillar") or {}).get("id")) or "unassigned"
        balance[pid] = balance.get(pid, 0) + 1
    return {"make_count": len(makes), "duplicates": dups, "pillar_balance": balance}


# ── 저장 ──────────────────────────────────────────────────────────────────────
class AssessmentStore:
    def __init__(self, root: str | Path | None) -> None:
        self.root = Path(root) if root else None

    def path(self, channel_id: str, video_id: str) -> Path | None:
        return (self.root / REL_DIR / channel_id / f"{video_id}.json") if self.root else None

    def load(self, channel_id: str, video_id: str) -> dict[str, Any] | None:
        p = self.path(channel_id, video_id)
        if not p or not p.is_file():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def load_channel(self, channel_id: str) -> list[dict[str, Any]]:
        if not self.root:
            return []
        out = []
        for p in sorted((self.root / REL_DIR / channel_id).glob("*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return out

    def save(self, doc: dict[str, Any]) -> Path:
        p = self.path(doc["channel_id"], doc["video_id"])
        assert p is not None
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, p)
        return p


# ── 게이트 ────────────────────────────────────────────────────────────────────
def decide(identity: dict[str, Any] | None, fit: dict[str, Any], market: dict[str, Any],
           portfolio: dict[str, Any], interp: dict[str, Any] | None, has_brief: bool) -> dict[str, Any]:
    """규칙 게이트. 반환: suggested · blockers(REVIEW 사유) · gates · reasons."""
    blockers: list[str] = []
    reasons: list[str] = []
    gates = {"fit": "pass", "market": "pass", "portfolio": "pass", "production": "pass"}
    skip = False
    watch = False

    if not identity or identity.get("status") != "approved":
        blockers.append("identity_missing — 승인된 Channel Identity 가 없다. Episode 는 Identity 를 참조해야 한다.")
    # Gate 1 — Channel Fit. 미평가를 점수가 덮지 않는다.
    if fit.get("state") != "VALID":
        gates["fit"] = "blocked"
        blockers.append(f"fit_{fit.get('state', 'NOT_EVALUATED').lower()} — RADAR 적합성 판정이 현재 프로필 기준으로 없다"
                        + (f" ({fit.get('stale_reason')})" if fit.get("stale_reason") else "") + ". 재판정 후 판단한다.")
    else:
        rel = fit.get("channel_relevance")
        if rel == "LOW":
            gates["fit"] = "fail"; skip = True
            reasons.append("채널 관련성 LOW — 시장성이 있어도 이 채널의 소재가 아니다.")
        elif rel == "MEDIUM":
            gates["fit"] = "warn"
            conf = (interp or {}).get("pillar_confidence")
            if conf != "HIGH":
                watch = True
                reasons.append("채널 관련성 MEDIUM 인데 Pillar 앵글이 확실하지 않다 — 앵글을 고정하기 전엔 WATCH.")
            else:
                reasons.append(f"채널 관련성 MEDIUM 이지만 앵글로 고정 가능: {(interp or {}).get('anchor_angle')}")
    # Gate 2 — Market. 낮으면 우선순위만 내린다.
    if market.get("level") == "LOW":
        gates["market"] = "warn"; watch = True
        reasons.append(f"시장 기회 LOW (점수 {market.get('score')}) — 채널에 맞아도 우선순위가 낮다.")
    # Gate 3 — Portfolio.
    if portfolio.get("duplicates"):
        gates["portfolio"] = "warn"; watch = True
        d = portfolio["duplicates"][0]
        reasons.append(f"기존 MAKE 와 중복 가능: «{d.get('title')}» (유사도 {d.get('similarity')}).")
    if interp:
        if interp.get("boundary_risk") == "HIGH":
            gates["portfolio"] = "warn"; watch = True
            reasons.append(f"Boundary 위험 HIGH — {interp.get('boundary_reason')}")
        if interp.get("expansion_kind") == "drift":
            gates["portfolio"] = "fail"; skip = True
            reasons.append("정체성 이동(drift) — 이 소재가 주축이 되면 채널이 다른 채널이 된다.")
        elif interp.get("expansion_kind") == "extend":
            reasons.append("유효한 확장(extend) — 기존 영역에 붙는 새 방향.")
        elif interp.get("expansion_kind") == "reinforce":
            reasons.append("기존 영역 강화(reinforce).")
    # Gate 4 — Production suitability.
    if not has_brief:
        gates["production"] = "blocked"
        blockers.append("brief_missing — RADAR 브리프가 없어 AutoMaker 패키지를 만들 수 없다.")
    if identity and identity.get("status") == "approved" and not (interp or {}).get("narrator_id"):
        gates["production"] = "warn"
        reasons.append("Narrator 추천 없음 — 제작 전 화자 관점을 정해야 한다.")

    if blockers:
        suggested = "REVIEW_REQUIRED"
    elif skip:
        suggested = "SKIP"
    elif watch:
        suggested = "WATCH"
    else:
        suggested = "MAKE"
        reasons.append("네 게이트 통과 — MAKE 후보. 최종 확정은 사용자.")
    return {"suggested": suggested, "blockers": blockers, "gates": gates, "reasons": reasons}


# ── 실행 ──────────────────────────────────────────────────────────────────────
def _fit_block(fit: dict[str, Any]) -> str:
    keys = ("state", "channel_relevance", "audience_fit", "money_impact", "problem_strength",
            "longform_potential", "evergreen_potential", "news_risk", "angle_ko", "reason")
    return json.dumps({k: fit.get(k) for k in keys}, ensure_ascii=False, indent=1)


def _identity_block(identity: dict[str, Any]) -> str:
    keys = ("problem_space", "expectations", "pillars", "boundary", "narrator_pool")
    return json.dumps({k: identity.get(k) for k in keys}, ensure_ascii=False, indent=1)


def run(candidate: dict[str, Any], *, settings: Settings, data: RadarData, ledger: DecisionsLedger,
        identity_store: IdentityStore, store: AssessmentStore, force: bool = False) -> dict[str, Any]:
    video_id = str(candidate.get("radar_id") or "")
    channel_id = str(candidate.get("channel") or "")
    if not video_id or not channel_id:
        raise ValueError("radar_id 와 channel 이 있어야 판정할 수 있습니다 (실측 후보만).")
    identity = identity_store.load(channel_id)
    approved = identity if identity and identity.get("status") == "approved" else None
    fit = evaluate_fit(data, video_id, channel_id)
    package = data.latest_package(video_id, channel_id)
    market = market_opportunity(package, fit, candidate.get("radar_score") or candidate.get("value"))
    makes = [r for r in ledger.latest_by_key().values() if r.get("channel_id") == channel_id and r.get("decision") == "MAKE"]
    past = [a for a in store.load_channel(channel_id) if a.get("video_id") != video_id]
    portfolio = portfolio_rules(candidate, makes, past)
    brief = data.brief(channel_id, video_id)

    # AI 해석 — Identity 가 있고 Fit 이 VALID 일 때만 부른다(그 전엔 근거가 없다). 캐시 키로 재호출을 막는다.
    interp: dict[str, Any] | None = None
    interp_meta: dict[str, Any] = {"called": False}
    if approved and fit.get("state") == "VALID":
        key = hashlib.sha256(json.dumps([video_id, channel_id, approved.get("identity_version"), fit.get("evaluated_at"),
                                         (brief or "")[:500]], ensure_ascii=False).encode()).hexdigest()[:16]
        previous = store.load(channel_id, video_id)
        if not force and previous and (previous.get("interpretation") or {}).get("cache_key") == key:
            interp = previous["interpretation"]
            interp_meta = {"called": False, "cached": True}
        else:
            prompt = _fill(INTERPRET_PROMPT, 
                identity_version=approved.get("identity_version"), identity=_identity_block(approved),
                candidate=json.dumps({"video_id": video_id, "title": candidate.get("title"), "topic": candidate.get("topic"),
                                      "brief_excerpt": (brief or "")[:1800]}, ensure_ascii=False, indent=1),
                fit=_fit_block(fit), make_count=len(makes),
                make_history=json.dumps([{"video_id": m.get("video_id"), "title": m.get("title")} for m in makes], ensure_ascii=False) or "(없음)",
            )
            got, model = ask_json(prompt, settings)
            if not isinstance(got, dict):
                raise ValueError("AI 해석이 JSON 객체가 아닙니다")
            valid_p = {p["id"] for p in approved.get("pillars", [])}
            valid_n = {n["id"] for n in approved.get("narrator_pool", [])}
            interp = {
                "pillar_id": got.get("pillar_id") if got.get("pillar_id") in valid_p else None,
                "pillar_confidence": got.get("pillar_confidence") if got.get("pillar_confidence") in LEVELS else "LOW",
                "anchor_angle": got.get("anchor_angle"),
                "boundary_risk": got.get("boundary_risk") if got.get("boundary_risk") in LEVELS else "MEDIUM",
                "boundary_reason": got.get("boundary_reason"),
                "expansion_kind": got.get("expansion_kind") if got.get("expansion_kind") in ("reinforce", "extend", "drift") else "extend",
                "series_potential": got.get("series_potential") if got.get("series_potential") in LEVELS else "MEDIUM",
                "followups_in": list(got.get("followups_in") or [])[:6],
                "followups_out": list(got.get("followups_out") or [])[:6],
                "narrator_id": got.get("narrator_id") if got.get("narrator_id") in valid_n else None,
                "narrator_why": got.get("narrator_why"),
                "identity_caution": got.get("identity_caution"),
                "model": model, "cache_key": key,
            }
            interp_meta = {"called": True, "cached": False, "model": model}

    decision = decide(identity, fit, market, portfolio, interp, has_brief=bool(brief))
    narrator = None
    if interp and interp.get("narrator_id") and approved:
        n = next((x for x in approved["narrator_pool"] if x["id"] == interp["narrator_id"]), None)
        if n:
            narrator = {"id": n["id"], "label": n["label"], "role_type": n["role_type"], "why": interp.get("narrator_why")}
    pillar = None
    if interp and interp.get("pillar_id") and approved:
        p = next((x for x in approved["pillars"] if x["id"] == interp["pillar_id"]), None)
        if p:
            pillar = {"id": p["id"], "label": p["label"], "confidence": interp.get("pillar_confidence"),
                      "anchor_angle": interp.get("anchor_angle")}

    doc = {
        "video_id": video_id, "channel_id": channel_id, "candidate_id": candidate.get("id"),
        "title": candidate.get("title"), "topic": candidate.get("topic"),
        "identity_version": (identity or {}).get("identity_version"), "identity_status": (identity or {}).get("status"),
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "market": market, "fit": fit, "pillar": pillar,
        "portfolio": {**portfolio, "boundary_risk": (interp or {}).get("boundary_risk"),
                      "boundary_reason": (interp or {}).get("boundary_reason"),
                      "expansion_kind": (interp or {}).get("expansion_kind")},
        "series": {"potential": (interp or {}).get("series_potential"),
                   "followups_in": (interp or {}).get("followups_in") or [],
                   "followups_out": (interp or {}).get("followups_out") or []},
        "narrator": narrator,
        "identity_caution": (interp or {}).get("identity_caution"),
        "decision": decision,
        "interpretation": interp, "interpretation_meta": interp_meta,
        "package_revision": (package or {}).get("revision"),
    }
    store.save(doc)
    return doc


def ledger_signals(doc: dict[str, Any]) -> dict[str, Any]:
    """decisions.jsonl 의 signals 에 실을 요약 — AutoMaker 까지 payload.decision.signals 로 간다."""
    return {
        "assessment": {
            "assessed_at": doc.get("assessed_at"), "identity_version": doc.get("identity_version"),
            "suggested": (doc.get("decision") or {}).get("suggested"),
            "gates": (doc.get("decision") or {}).get("gates"),
            "market_level": (doc.get("market") or {}).get("level"),
            "fit_state": (doc.get("fit") or {}).get("state"),
            "channel_relevance": (doc.get("fit") or {}).get("channel_relevance"),
            "pillar": (doc.get("pillar") or {}).get("id"),
            "anchor_angle": (doc.get("pillar") or {}).get("anchor_angle"),
            "boundary_risk": (doc.get("portfolio") or {}).get("boundary_risk"),
            "expansion_kind": (doc.get("portfolio") or {}).get("expansion_kind"),
            "series_potential": (doc.get("series") or {}).get("potential"),
        },
        "narrator": doc.get("narrator"),
    }
