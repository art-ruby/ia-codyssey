"""숫자 기록 CRUD(T06.01, PRD §11.1·§13, docs/decisions.md).

- `data`에는 사용자가 명시적으로 저장한 수기(개인 모드)·표본(표본 모드) 기록만 둔다. 실제 지표는 저장하지 않고
  요약(T06.02)할 때 자료에서 계산한다.
- 같은 날짜·지표에 기록이 여러 건 있을 수 있다. 일별 값은 요약에서 합계로 계산한다. 중복 전송은 요청 키로 막는다.
- 목록은 현재 모드의 기록을 읽어 날짜 최신순으로 정렬하고 지표·기간으로 거른 뒤 나눠 준다.
"""
from __future__ import annotations

import base64
import hashlib
import json

from app.core.context import RequestContext
from app.core.firestore import InvalidCursor, NotFound, Store, VersionConflict

COLLECTION = "data"
ORIGIN = {"personal": "manual", "sample": "sample"}
PUBLIC_FIELDS = ("id", "date", "metric_type", "value", "memo", "origin", "mode", "version", "created_at", "updated_at")
MAX_SCAN = 5000


def public(doc: dict) -> dict:
    return {name: doc.get(name) for name in PUBLIC_FIELDS}


def create_record(store: Store, ctx: RequestContext, data: dict) -> dict:
    record = {**data, "memo": data.get("memo") or "", "origin": ORIGIN[ctx.mode]}
    return public(store.create(ctx, COLLECTION, record))


def get_record(store: Store, ctx: RequestContext, record_id: str) -> dict:
    return public(store.get(ctx, COLLECTION, record_id))


def update_record(store: Store, ctx: RequestContext, record_id: str, expected_version: int, changes: dict) -> dict:
    store.get(ctx, COLLECTION, record_id)  # 남의 기록·다른 모드는 404
    if "memo" in changes and changes["memo"] is None:
        changes["memo"] = ""
    return public(store.update(ctx, COLLECTION, record_id, expected_version, changes))


def delete_record(store: Store, ctx: RequestContext, record_id: str, expected_version: int) -> dict:
    """버전 확인과 삭제를 한 트랜잭션에서 한다."""
    key = (COLLECTION, record_id)

    def check(docs):
        current = docs[key]
        if current is None:
            raise NotFound(COLLECTION)
        if current["version"] != expected_version:
            raise VersionConflict(current["version"])
        return [(*key, None)], None

    store.run_transaction(ctx, [key], check)
    return {"deleted": True, "id": record_id}


def _fingerprint(filters: dict) -> str:
    return hashlib.sha256(json.dumps(filters, sort_keys=True).encode()).hexdigest()[:16]


def _encode(fp: str, offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"q": fp, "o": offset}).encode()).decode().rstrip("=")


def _decode(cursor: str, fp: str) -> int:
    """같은 필터로 만든 커서만 받는다. 다른 필터의 커서나 망가진 값은 InvalidCursor(422)."""
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        offset = data["o"]
        ok = data["q"] == fp and isinstance(offset, int) and offset >= 0
    except (ValueError, TypeError, KeyError):
        ok = False
    if not ok:
        raise InvalidCursor()
    return offset


def scan_records(store: Store, ctx: RequestContext) -> tuple[list[dict], bool]:
    """현재 모드의 숫자 기록 전부(최대 MAX_SCAN). 요약(T06.02)도 함께 쓴다."""
    docs, cursor = [], None
    while True:
        page = store.list(ctx, COLLECTION, limit=100, cursor=cursor)  # 기존 오름차순 색인
        docs += page.items
        cursor = page.next_cursor
        if not cursor or len(docs) >= MAX_SCAN:
            return docs, bool(cursor)


def list_records(store: Store, ctx: RequestContext, metric_type: str | None, date_from: str | None,
                 date_to: str | None, limit: int, cursor: str | None) -> dict:
    filters = {"metric_type": metric_type, "date_from": date_from, "date_to": date_to}
    fp = _fingerprint(filters)
    offset = _decode(cursor, fp) if cursor else 0
    docs, truncated = scan_records(store, ctx)
    matched = [d for d in docs
               if (not metric_type or d.get("metric_type") == metric_type)
               and (not date_from or d.get("date", "") >= date_from)
               and (not date_to or d.get("date", "") <= date_to)]
    matched.sort(key=lambda d: d.get("id", ""))
    matched.sort(key=lambda d: (d.get("date", ""), d.get("created_at", "")), reverse=True)  # 날짜 최신순
    window = matched[offset:offset + limit]
    end = offset + len(window)
    return {"items": [public(d) for d in window], "next_cursor": _encode(fp, end) if end < len(matched) else None,
            "total": len(matched), "truncated": truncated}
