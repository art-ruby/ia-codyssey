"""Summary 서비스.

명세 4절: 단순 평균만 내는 API 가 아니라 AI 판단에 쓸 컨텍스트를 만든다.
RADAR 실제 데이터 구조가 바뀌어도 교체하기 쉽도록 라우터에서 분리해 둔다.

계산 원칙 — 표본이 적으면 추세를 단정하지 않는다. M1-1 에서 나이 보정 없이
성장률을 재다가 +16,162% 같은 값을 얻은 적이 있어, 여기서는 비교 구간의
표본 수를 함께 보고 부족하면 '판단 보류'라고 말한다.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from ..models.schemas import DecisionCounts, Summary, SummaryMetrics

RECENT_WINDOW_DAYS = 7
MIN_SAMPLES_FOR_TREND = 5


def _as_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _decision_value(raw: Any) -> str | None:
    """저장소마다 Enum 이거나 문자열이라 한쪽으로 모은다."""
    if raw is None:
        return None
    text = getattr(raw, "value", raw)
    return text if text in ("MAKE", "WATCH", "SKIP") else None


def _trend_label(recent: list[float], previous: list[float]) -> str:
    if len(recent) < MIN_SAMPLES_FOR_TREND:
        return f"최근 {RECENT_WINDOW_DAYS}일 표본 {len(recent)}건 — 추세 판단 보류"
    if len(previous) < MIN_SAMPLES_FOR_TREND:
        return f"최근 {RECENT_WINDOW_DAYS}일 평균 {sum(recent) / len(recent):.1f}점 — 비교 구간 표본 부족"
    now = sum(recent) / len(recent)
    before = sum(previous) / len(previous)
    delta = now - before
    if abs(delta) < 2.0:
        return f"최근 {RECENT_WINDOW_DAYS}일 평균 {now:.1f}점 — 직전 구간과 유지({delta:+.1f})"
    direction = "상승" if delta > 0 else "하락"
    return f"최근 {RECENT_WINDOW_DAYS}일 후보 점수 {direction} ({before:.1f} → {now:.1f}, {delta:+.1f})"


def build_summary(candidates: list[dict[str, Any]], *, now: datetime | None = None) -> Summary:
    now = now or datetime.now(timezone.utc)
    generated_at = now

    dated: list[tuple[datetime, float, dict[str, Any]]] = []
    for item in candidates:
        when = _as_dt(item.get("date"))
        try:
            score = float(item.get("value"))
        except (TypeError, ValueError):
            continue
        if when is not None:
            dated.append((when, score, item))

    if not dated:
        return Summary(
            period="데이터 없음",
            count=0,
            metrics=SummaryMetrics(average_score=0.0, max_score=0.0, min_score=0.0),
            trend="후보가 없어 추세를 계산하지 않았다",
            decisions=DecisionCounts(),
            top_topics=[],
            channels={},
            source_mix={},
            generated_at=generated_at,
        )

    dated.sort(key=lambda row: row[0])
    scores = [score for _, score, _ in dated]
    first, last = dated[0][0], dated[-1][0]

    cutoff = now - timedelta(days=RECENT_WINDOW_DAYS)
    prior_cutoff = now - timedelta(days=RECENT_WINDOW_DAYS * 2)
    recent = [s for w, s, _ in dated if w >= cutoff]
    previous = [s for w, s, _ in dated if prior_cutoff <= w < cutoff]

    counts = Counter()
    for _, _, item in dated:
        counts[_decision_value(item.get("decision")) or "PENDING"] += 1

    topics = Counter(
        (item.get("topic") or "").strip()
        for _, _, item in dated
        if (item.get("topic") or "").strip()
    )
    channels = Counter(
        (item.get("channel") or "").strip()
        for _, _, item in dated
        if (item.get("channel") or "").strip()
    )
    sources = Counter(
        getattr(item.get("source"), "value", item.get("source")) or "manual" for _, _, item in dated
    )

    return Summary(
        period=f"{first:%Y-%m-%d} ~ {last:%Y-%m-%d}",
        count=len(dated),
        metrics=SummaryMetrics(
            average_score=round(sum(scores) / len(scores), 1),
            max_score=round(max(scores), 1),
            min_score=round(min(scores), 1),
        ),
        trend=_trend_label(recent, previous),
        decisions=DecisionCounts(
            MAKE=counts.get("MAKE", 0),
            WATCH=counts.get("WATCH", 0),
            SKIP=counts.get("SKIP", 0),
            PENDING=counts.get("PENDING", 0),
        ),
        top_topics=[topic for topic, _ in topics.most_common(5)],
        channels=dict(channels.most_common()),
        source_mix=dict(sources.most_common()),
        generated_at=generated_at,
    )
