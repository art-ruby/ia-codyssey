"""AI 사용량과 일일 한도(T04.03, PRD §14, docs/decisions.md).

- 소유자 전체(개인·표본 합산), 서울 날짜 기준으로 센다. 하루가 바뀌면 새 기록이다.
- Provider에 요청을 보내기 전에 `reserve`로 1을 원자적으로 차감한다. 동시 요청도 한도를 넘지 않는다.
- 보내기 전에 멈춘 실패(`request_sent=False`)만 `refund`로 돌려준다. 서버가 죽어 결과를 모르는 요청은
  실제로 나갔을 수 있으므로 사용으로 남긴다(한도를 넘지 않는 쪽).
- 요청 수는 실제 모델 호출만 센다. Hermes 도구 확인(`/toolsets`)과 수동 스모크 스크립트는 세지 않는다.
- 분석·채팅이 같은 한도를 쓴다(`kind`: analysis | chat). 채팅은 T07.02에서 같은 함수를 쓴다.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, time, timedelta, timezone

from app.core.firestore import Store

SEOUL = timezone(timedelta(hours=9))
KINDS = ("analysis", "chat")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def usage_day(now: datetime | None = None) -> str:
    return (now or _now()).astimezone(SEOUL).date().isoformat()


def _record_id(owner_id: str, day: str) -> str:
    return hashlib.sha256(f"{owner_id}\n{day}".encode()).hexdigest()


class _Full(Exception):
    """한도에 도달해 예약하지 않는다."""


def reserve(store: Store, owner_id: str, kind: str, limit: int) -> str | None:
    """요청 1회를 예약한다. 성공하면 예약한 날짜(환불·결과 기록에 쓴다), 한도에 도달했으면 None."""
    day = usage_day()

    def take(current: dict) -> dict:
        used = current.get("used", 0)
        if used >= limit:
            raise _Full()
        return {**current, "day": day, "used": used + 1,
                f"{kind}_count": current.get(f"{kind}_count", 0) + 1}

    try:
        store.change_usage(owner_id, _record_id(owner_id, day), take)
    except _Full:
        return None
    return day


def refund(store: Store, owner_id: str, day: str, kind: str) -> None:
    """보내기 전에 멈춘 요청의 예약을 돌려준다. 예약한 날짜의 기록에서 뺀다."""
    store.change_usage(owner_id, _record_id(owner_id, day), lambda c: {
        **c, "day": day, "used": max(c.get("used", 0) - 1, 0),
        f"{kind}_count": max(c.get(f"{kind}_count", 0) - 1, 0),
        "refunded": c.get("refunded", 0) + 1,
    })


def record_sent(store: Store, owner_id: str, day: str, *, failed: bool, tokens: int | None) -> None:
    """실제로 보낸 요청의 결과를 더한다(실패·429도 사용량에 남는다)."""
    store.change_usage(owner_id, _record_id(owner_id, day), lambda c: {
        **c, "day": day,
        "failed_sent": c.get("failed_sent", 0) + (1 if failed else 0),
        "total_tokens": c.get("total_tokens", 0) + (tokens or 0),
    })


def summary(store: Store, owner_id: str, limit: int) -> dict:
    now = _now()
    day = usage_day(now)
    record = store.read_usage(owner_id, _record_id(owner_id, day)) or {}
    used = record.get("used", 0)
    tomorrow = datetime.combine(now.astimezone(SEOUL).date() + timedelta(days=1), time(), SEOUL)
    return {
        "date": day,
        "used": used,
        "limit": limit,
        "remaining": max(limit - used, 0),
        "failed_sent": record.get("failed_sent", 0),
        "by_kind": {kind: record.get(f"{kind}_count", 0) for kind in KINDS},
        "total_tokens": record.get("total_tokens", 0),
        "resets_at": tomorrow.astimezone(timezone.utc).isoformat(),
    }
