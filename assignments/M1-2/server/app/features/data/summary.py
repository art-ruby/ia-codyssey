"""숫자 요약(T06.02, PRD §11.2, docs/decisions.md).

- 출처: `actual`은 자료 상태에서 계산한다(접수 수 = 접수 기록, 보관 수 = 현재 보관 완료·활성 자료의 승인일).
  `manual`·`sample`은 `data`에서 같은 출처의 기록만 읽는다. 지표·출처·모드를 한 계산에 섞지 않는다.
- 기본값: 개인 모드 `actual + kept_count`, 표본 모드 `sample + kept_count`. 허용 조합은 `ALLOWED_SOURCES`.
- 날짜는 서울 기준. 관측 시작(첫 값이 있는 날) 이후 기록 없는 날은 0. 값이 전혀 없으면 합계 0, 나머지는 null.
- 추세 기준일: 개인 모드는 오늘(서울), 표본 모드는 그 계열의 최신 날짜. 최근 7일과 이전 7일의 일평균을 비교하며,
  관측 14일 미만이면 `insufficient`, 이전 0건이면 `new`(최근 > 0) 또는 `both_zero`. ±10% 경계는 증가·감소에 포함.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.core.context import RequestContext
from app.core.errors import NoChange
from app.core.firestore import Store
from app.features.data.service import scan_records
from app.features.materials.service import COLLECTION as MATERIALS, INTAKE, is_kept

SEOUL = timezone(timedelta(hours=9))
METRICS = ("received_count", "kept_count")
DEFAULT_SOURCE = {"personal": "actual", "sample": "sample"}
ALLOWED_SOURCES = {"personal": ("actual", "manual"), "sample": ("sample", "actual")}
LABELS = {
    ("kept_count", "actual"): "현재 보관 자료 수", ("kept_count", "manual"): "사용자 입력 보관 기록",
    ("kept_count", "sample"): "표본 보관 기록", ("received_count", "actual"): "실제 접수 건수",
    ("received_count", "manual"): "사용자 입력 접수 기록", ("received_count", "sample"): "표본 접수 기록",
}
TREND_DAYS = 7
CHANGE_THRESHOLD = 10.0
MAX_SCAN = 10000


class SourceNotAllowed(NoChange):
    """이 모드에서 쓸 수 없는 출처다(422). 예: 개인 모드에서 표본, 표본 모드에서 수기."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seoul_day(iso: str | None) -> date | None:
    return datetime.fromisoformat(iso).astimezone(SEOUL).date() if iso else None


def _scan(store: Store, ctx: RequestContext, collection: str) -> list[dict]:
    docs, cursor = [], None
    while True:
        page = store.list(ctx, collection, limit=100, cursor=cursor)
        docs += page.items
        cursor = page.next_cursor
        if not cursor or len(docs) >= MAX_SCAN:
            return docs


def daily_counts(store: Store, ctx: RequestContext, source: str, metric: str) -> dict[date, int]:
    counts: dict[date, int] = {}

    def add(day: date | None, value: int) -> None:
        if day is not None:
            counts[day] = counts.get(day, 0) + value

    if source == "actual" and metric == "received_count":
        for record in _scan(store, ctx, INTAKE):  # 영구 삭제한 자료의 접수 기록은 이미 지워졌다
            add(_seoul_day(record.get("received_at")), 1)
    elif source == "actual":
        for doc in _scan(store, ctx, MATERIALS):  # 휴지통·삭제 중 자료는 빠진다
            if is_kept(doc):
                add(_seoul_day(doc.get("storage_approved_at")), 1)
    else:
        records, _ = scan_records(store, ctx)
        for record in records:
            if record.get("origin") == source and record.get("metric_type") == metric:
                add(date.fromisoformat(record["date"]), int(record["value"]))
    return counts


def _average(values: list[int]) -> float:
    return round(sum(values) / len(values), 2)


def _trend(counts: dict[date, int], observed_from: date, reference: date) -> dict:
    window = [reference - timedelta(days=i) for i in range(2 * TREND_DAYS)]
    trend = {"reference_date": reference.isoformat(), "recent_average": None, "previous_average": None,
             "change_rate": None}
    if (reference - observed_from).days + 1 < 2 * TREND_DAYS:
        return {**trend, "status": "insufficient"}
    recent_total = sum(counts.get(d, 0) for d in window[:TREND_DAYS])
    previous_total = sum(counts.get(d, 0) for d in window[TREND_DAYS:])
    trend.update(recent_average=round(recent_total / TREND_DAYS, 2),
                 previous_average=round(previous_total / TREND_DAYS, 2))
    if previous_total == 0:
        return {**trend, "status": "new" if recent_total else "both_zero"}
    rate = (recent_total - previous_total) * 100 / previous_total  # 같은 일수라 합계 비율 = 평균 비율
    status = "increase" if rate >= CHANGE_THRESHOLD else "decrease" if rate <= -CHANGE_THRESHOLD else "flat"
    return {**trend, "status": status, "change_rate": round(rate, 1)}


def _summary(store: Store, ctx: RequestContext, source: str, metric: str,
             start_date: str | None, end_date: str | None) -> dict:
    counts = daily_counts(store, ctx, source, metric)
    base = {"metric_type": metric, "source": source, "mode": ctx.mode, "label": LABELS[(metric, source)]}
    empty = {"period": None, "days": 0, "daily": [], "total": 0, "average": None, "min": None, "max": None,
             "trend": None}
    if not counts:
        return {**base, **empty}
    observed_from = min(counts)
    reference = _now().astimezone(SEOUL).date() if ctx.mode == "personal" else max(counts)
    start = max(date.fromisoformat(start_date), observed_from) if start_date else observed_from
    end = date.fromisoformat(end_date) if end_date else reference
    trend = _trend(counts, observed_from, reference)
    if start > end:
        return {**base, **empty, "trend": trend}
    daily = [{"date": (start + timedelta(days=i)).isoformat(), "value": counts.get(start + timedelta(days=i), 0)}
             for i in range((end - start).days + 1)]
    values = [d["value"] for d in daily]
    return {**base, "period": {"start": start.isoformat(), "end": end.isoformat()}, "days": len(daily),
            "daily": daily, "total": sum(values), "average": _average(values), "min": min(values), "max": max(values),
            "trend": trend}


def summarize_data(store: Store, ctx: RequestContext, source: str | None, metric: str,
                   start_date: str | None, end_date: str | None) -> dict:
    """task.md의 `summarize_data(context, source, metric, start_date, end_date) -> Summary`."""
    source = source or DEFAULT_SOURCE[ctx.mode]
    if source not in ALLOWED_SOURCES[ctx.mode]:
        raise SourceNotAllowed()
    if metric == "all":
        return {"source": source, "mode": ctx.mode,
                "results": [_summary(store, ctx, source, m, start_date, end_date) for m in METRICS]}
    return _summary(store, ctx, source, metric, start_date, end_date)
