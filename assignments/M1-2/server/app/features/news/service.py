"""AI 동향 '새 소식'(설계: docs/superpowers/specs/2026-10-04-ai-news-feed-design.md).

- 개인 모드 전용. 표본 모드 요청은 422(personal_only).
- 수집 조건: 마지막 성공이 6시간 지났고 마지막 시도가 5분 지났을 때(수동 새로고침은 5분 조건만).
  수집 중 표시(`refreshing_until`, 3분)를 트랜잭션으로 차지한 요청 하나만 수집한다.
- 같은 글은 링크 비교 키의 해시로 문서 ID가 정해져 한 번만 저장되고, 숨김·저장 상태를 덮어쓰지 않는다.
- 저장하지 않은 글은 30일이 지나면, 전체가 300건을 넘으면 오래된 것부터 지운다.
"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone

from app.core.context import RequestContext
from app.core.errors import NoChange
from app.core.firestore import NotFound, Store, VersionConflict
from app.features.materials import service as materials
from app.features.materials.url_keys import url_key
from app.features.news import feeds, keywords
from app.features.news.sources import DEFAULT_SOURCES, MAX_SOURCES
from app.features.projects.service import list_projects
from app.features.settings.service import get_settings

SOURCES = "news_sources"
ITEMS = "news_items"
STATE = "news_state"
AUTO_INTERVAL = timedelta(hours=6)
MIN_GAP = timedelta(minutes=5)
LEASE = timedelta(minutes=3)
TOTAL_SECONDS = 90
KEEP = timedelta(days=30)
MAX_ITEMS = 300
PAGE_SIZE = 30

log = logging.getLogger("ai_secretary.news")


class NewsError(NoChange):
    """쓰기 전에 거부했다. message는 화면에 그대로 보여도 되는 안내다."""

    def __init__(self, status: int, reason: str, message: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.message = message


def require_personal(ctx: RequestContext) -> None:
    if ctx.mode != "personal":
        raise NewsError(422, "personal_only", "새 소식은 개인 모드에서만 볼 수 있습니다")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _digest(*parts: str) -> str:
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:40]


def state_id(ctx: RequestContext) -> str:
    return "news-state-" + _digest(ctx.owner_id, ctx.mode)


def item_id(ctx: RequestContext, link: str) -> str:
    return "news-" + _digest(ctx.owner_id, ctx.mode, url_key(link))


def source_id(ctx: RequestContext, key: str) -> str:
    return "news-src-" + _digest(ctx.owner_id, ctx.mode, key)


def _all(store: Store, ctx: RequestContext, collection: str) -> list[dict]:
    docs, cursor = [], None
    while True:
        page = store.list(ctx, collection, limit=100, cursor=cursor)
        docs.extend(page.items)
        if not page.next_cursor:
            return docs
        cursor = page.next_cursor


def _sort_time(doc: dict) -> str:
    return doc.get("published_at") or doc.get("fetched_at") or ""


# ── 출처 ──────────────────────────────────────────────────────────

def public_source(doc: dict) -> dict:
    return {"id": doc["id"], "name": doc["name"], "feed_url": doc["feed_url"], "kind": doc["kind"],
            "enabled": bool(doc.get("enabled")), "builtin": doc.get("builtin_key") is not None,
            "version": doc["version"]}


def ensure_sources(store: Store, ctx: RequestContext) -> list[dict]:
    """기본 출처가 없으면 만들고, 기본 출처 → 직접 추가한 출처 순으로 돌려준다."""
    docs = {d["id"]: d for d in _all(store, ctx, SOURCES)}
    for order, (key, name, url, kind, enabled) in enumerate(DEFAULT_SOURCES):
        sid = source_id(ctx, "builtin:" + key)
        if sid in docs:
            continue
        data = {"name": name, "feed_url": url, "kind": kind, "enabled": enabled, "builtin_key": key, "order": order}
        try:
            docs[sid] = store.create(ctx, SOURCES, data, doc_id=sid)
        except VersionConflict:  # 다른 요청이 먼저 만들었다
            docs[sid] = store.get(ctx, SOURCES, sid)
    return sorted(docs.values(), key=lambda d: (d.get("order", 1000), d["created_at"], d["id"]))


def list_sources(store: Store, ctx: RequestContext) -> dict:
    require_personal(ctx)
    return {"items": [public_source(d) for d in ensure_sources(store, ctx)]}


def add_source(store: Store, ctx: RequestContext, name: str, feed_url: str, request: feeds.Request | None = None) -> dict:
    require_personal(ctx)
    current = ensure_sources(store, ctx)
    if len(current) >= MAX_SOURCES:
        raise NewsError(422, "too_many_sources", f"소식 출처는 최대 {MAX_SOURCES}곳까지 등록할 수 있습니다")
    key = url_key(feed_url)
    if any(url_key(s["feed_url"]) == key for s in current):
        raise NewsError(409, "duplicate_source", "이미 등록된 피드 주소입니다")
    try:
        feeds.read_feed(feed_url, request)  # 저장 전에 실제 피드인지 확인한다
    except feeds.FeedError as exc:
        raise NewsError(422, exc.code, exc.message) from None
    data = {"name": name, "feed_url": feed_url, "kind": "custom", "enabled": True, "builtin_key": None, "order": 1000}
    return public_source(store.create(ctx, SOURCES, data, doc_id=source_id(ctx, "custom:" + key)))


def set_source_enabled(store: Store, ctx: RequestContext, sid: str, expected_version: int, enabled: bool) -> dict:
    require_personal(ctx)
    return public_source(store.update(ctx, SOURCES, sid, expected_version, {"enabled": enabled}))


def delete_source(store: Store, ctx: RequestContext, sid: str) -> dict:
    require_personal(ctx)
    if store.get(ctx, SOURCES, sid).get("builtin_key"):
        raise NewsError(409, "builtin_source", "기본 출처는 삭제할 수 없습니다. 끄기만 할 수 있습니다")
    store.delete(ctx, SOURCES, sid)
    return {"deleted": True, "id": sid}


# ── 수집 ──────────────────────────────────────────────────────────

def _state(store: Store, ctx: RequestContext) -> dict:
    try:
        return store.get(ctx, STATE, state_id(ctx))
    except NotFound:
        return {}


def _lease_active(state: dict, now: datetime) -> bool:
    until = _parse(state.get("refreshing_until"))
    return bool(until and until > now)


def _due(state: dict, now: datetime, manual: bool) -> bool:
    attempted = _parse(state.get("last_attempt_at"))
    if attempted and now - attempted < MIN_GAP:
        return False
    if manual:
        return True
    succeeded = _parse(state.get("last_success_at"))
    return succeeded is None or now - succeeded >= AUTO_INTERVAL


def claim_refresh(store: Store, ctx: RequestContext, manual: bool, now: datetime | None = None) -> bool:
    """수집할 때가 됐고 다른 수집이 없으면 수집 중 표시를 차지한다. 차지했으면 True."""
    now = now or _now()
    sid = state_id(ctx)

    def decide(docs):
        current = docs[(STATE, sid)] or {}
        if _lease_active(current, now) or not _due(current, now, manual):
            return [], False
        return [(STATE, sid, {"refreshing_until": (now + LEASE).isoformat(), "last_attempt_at": now.isoformat()})], True

    claimed, _ = store.run_transaction(ctx, [(STATE, sid)], decide)
    return claimed


def _store_entries(store: Store, ctx: RequestContext, source: dict, entries: list[feeds.Entry], now: datetime) -> int:
    added = 0
    for entry in entries:
        data = {"source_id": source["id"], "source_name": source["name"], "kind": source["kind"],
                "title": entry.title, "link": entry.link, "summary": entry.summary,
                "published_at": entry.published_at, "fetched_at": now.isoformat(),
                "saved_material_id": None, "hidden": False}
        try:
            store.create(ctx, ITEMS, data, doc_id=item_id(ctx, entry.link))
            added += 1
        except VersionConflict:  # 이미 있는 글: 숨김·저장 상태를 지키기 위해 건드리지 않는다
            pass
    return added


def cleanup(store: Store, ctx: RequestContext, now: datetime) -> int:
    docs = _all(store, ctx, ITEMS)
    unsaved = [d for d in docs if not d.get("saved_material_id")]
    drop = {d["id"] for d in unsaved if _parse(d["fetched_at"]) < now - KEEP}
    remaining = len(docs) - len(drop)
    if remaining > MAX_ITEMS:
        older = sorted((d for d in unsaved if d["id"] not in drop), key=lambda d: (_sort_time(d), d["id"]))
        drop |= {d["id"] for d in older[:remaining - MAX_ITEMS]}
    for doc_id in drop:
        store.delete(ctx, ITEMS, doc_id)
    return len(drop)


def run_refresh(store: Store, ctx: RequestContext, request: feeds.Request | None = None,
                now: datetime | None = None) -> dict:
    """켜진 출처를 차례로 읽어 새 글을 저장한다. 끝나면 수집 중 표시를 풀고 출처별 결과를 남긴다."""
    started = time.monotonic()
    results: dict[str, dict] = {}
    any_ok = False
    try:
        for source in ensure_sources(store, ctx):
            if not source.get("enabled"):
                continue
            if time.monotonic() - started > TOTAL_SECONDS:
                results[source["id"]] = {"ok": False, "count": 0, "error": "시간이 부족해 이번에는 읽지 못했습니다."}
                continue
            try:
                entries = feeds.read_feed(source["feed_url"], request)
            except feeds.FeedError as exc:
                results[source["id"]] = {"ok": False, "count": 0, "error": exc.message}
                continue
            except Exception:
                log.exception("news source failed")
                results[source["id"]] = {"ok": False, "count": 0, "error": "읽는 중 오류가 났습니다."}
                continue
            count = _store_entries(store, ctx, source, entries, now or _now())
            results[source["id"]] = {"ok": True, "count": count, "error": None}
            any_ok = True
        cleanup(store, ctx, now or _now())
    finally:
        changes = {"refreshing_until": None, "sources": results}
        if any_ok:
            changes["last_success_at"] = (now or _now()).isoformat()
        sid = state_id(ctx)
        store.run_transaction(ctx, [(STATE, sid)], lambda docs: ([(STATE, sid, changes)], None))
    return results


# ── 보기·저장·숨기기 ───────────────────────────────────────────────

def public_item(doc: dict, matched: list[str]) -> dict:
    return {"id": doc["id"], "title": doc["title"], "link": doc["link"], "summary": doc.get("summary", ""),
            "source_name": doc["source_name"], "kind": doc["kind"], "published_at": doc.get("published_at"),
            "fetched_at": doc["fetched_at"], "saved_material_id": doc.get("saved_material_id"),
            "hidden": bool(doc.get("hidden")), "matched_keywords": matched}


def _offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    if not cursor.isdigit() or int(cursor) > 10000:
        raise NewsError(422, "invalid_cursor", "목록 위치가 올바르지 않습니다. 처음부터 다시 불러오세요")
    return int(cursor)


def current_keywords(store: Store, ctx: RequestContext) -> list[str]:
    names = [p["name"] for p in list_projects(store, ctx)]
    return keywords.build_keywords(get_settings(store, ctx)["interests"], names)


def news_view(store: Store, ctx: RequestContext, cursor: str | None = None, refreshing: bool = False) -> dict:
    require_personal(ctx)
    offset = _offset(cursor)
    state = _state(store, ctx)
    words = current_keywords(store, ctx)
    rows = [(d, keywords.match(words, f"{d['title']}\n{d.get('summary', '')}"))
            for d in _all(store, ctx, ITEMS) if not d.get("hidden")]
    rows.sort(key=lambda r: r[0]["id"])
    rows.sort(key=lambda r: _sort_time(r[0]), reverse=True)
    rows.sort(key=lambda r: 0 if r[1] else 1)
    page = rows[offset:offset + PAGE_SIZE]
    names = {s["id"]: s["name"] for s in _all(store, ctx, SOURCES)}
    failures = [{"source_name": names.get(sid, "삭제된 출처"), "error": r.get("error")}
                for sid, r in (state.get("sources") or {}).items() if not r.get("ok")]
    return {
        "items": [public_item(d, m) for d, m in page],
        "next_cursor": str(offset + PAGE_SIZE) if offset + PAGE_SIZE < len(rows) else None,
        "total": len(rows),
        "keywords": words,
        "state": {"refreshing": refreshing or _lease_active(state, _now()),
                  "last_success_at": state.get("last_success_at"),
                  "last_attempt_at": state.get("last_attempt_at"), "failures": failures},
    }


def save_item(store: Store, ctx: RequestContext, news_id: str) -> dict:
    """글을 받은 자료로 저장한다. 같은 URL 자료가 있으면 새로 만들지 않고 연결한다."""
    require_personal(ctx)
    item = store.get(ctx, ITEMS, news_id)
    if item.get("saved_material_id"):
        return {"item": public_item(item, []), "material_id": item["saved_material_id"], "created": False}
    data = {"url": item["link"], "title": item["title"], "body": item.get("summary") or ""}
    try:
        _, material = materials.create_material(store, ctx, data)
        material_id, created = material["id"], True
    except materials.DuplicateUrl as exc:
        material_id, created = exc.existing[0]["id"], False
    updated = store.transform(ctx, ITEMS, news_id, lambda _doc: {"saved_material_id": material_id})
    return {"item": public_item(updated, []), "material_id": material_id, "created": created}


def set_hidden(store: Store, ctx: RequestContext, news_id: str, hidden: bool) -> dict:
    require_personal(ctx)
    return public_item(store.transform(ctx, ITEMS, news_id, lambda _doc: {"hidden": hidden}), [])
