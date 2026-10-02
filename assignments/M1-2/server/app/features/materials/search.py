"""보관함 검색(PRD §5 S03·§11, T05.01, docs/decisions.md).

- 대상: 현재 모드의 보관 완료 자료(`is_kept`). 미승인·나중에 보기·휴지통은 제외한다.
- 필드: 사용자가 제공한 제목·설명·본문·저장 이유·메모·URL. AI가 만든 필드는 검색하지 않는다.
- 일치: 공백으로 나눈 검색어가 모두 들어 있어야 한다(AND). 유니코드 정규화(NFC)와 대소문자 무시, 한글 부분 일치.
- 필터: 기간(서울 날짜, 양 끝 포함), AI 종류(`ai_kind`), 원본 종류(`source_type`), 프로젝트(주·관련).
- 전략: Firestore Standard에는 전문 검색이 없다. 최신 접수부터 `MAX_SCAN`건을 읽어 Python에서 거른다.
  검색 범위(읽은 건수·한도 초과 여부)와 화면 페이지 크기를 따로 돌려준다. 한도를 넘으면 `truncated`로 알린다.
- 저장소 오류는 그대로 올린다. 검색 실패를 결과 0건으로 바꾸지 않는다.
- 채팅(T07)·관련 자료(T05.02)도 이 계약(`search_materials`)을 재사용한다.
"""
from __future__ import annotations

import base64
import hashlib
import json
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from app.core.context import RequestContext
from app.core.firestore import InvalidCursor, Store
from app.features.materials.service import COLLECTION, is_kept, public

SEARCH_FIELDS = ("title", "description", "body", "save_reason", "memo", "url")
MAX_SCAN = 1000
MAX_PAGE_SIZE = 50
SNIPPET_BEFORE, SNIPPET_AFTER = 40, 80
SEOUL = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class SearchFilters:
    date_from: str | None = None  # YYYY-MM-DD(서울), 포함
    date_to: str | None = None  # YYYY-MM-DD(서울), 포함
    kind: str | None = None  # ai_kind
    source_type: str | None = None  # url | text
    project_id: str | None = None  # 주 프로젝트 또는 관련 프로젝트


@dataclass(frozen=True)
class SearchPage:
    items: list[dict]
    next_cursor: str | None
    total_matches: int
    scope: dict  # 실제로 검색한 범위


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def _terms(query: str) -> list[str]:
    return [_norm(t) for t in query.split()]


def _seoul_date(iso: str | None) -> str:
    return datetime.fromisoformat(iso).astimezone(SEOUL).date().isoformat() if iso else ""


def _passes_filters(doc: dict, f: SearchFilters) -> bool:
    day = _seoul_date(doc.get("registered_at"))
    if f.date_from and day < f.date_from:
        return False
    if f.date_to and day > f.date_to:
        return False
    if f.kind and doc.get("ai_kind") != f.kind:
        return False
    if f.source_type and doc.get("source_type") != f.source_type:
        return False
    if f.project_id and f.project_id != doc.get("primary_project_id") \
            and f.project_id not in (doc.get("related_project_ids") or []):
        return False
    return True


def _match(doc: dict, terms: list[str]) -> dict | None | bool:
    """모든 검색어가 있으면 첫 검색어가 처음 나온 필드·문맥, 없으면 False. 검색어가 없으면 None(전체 보기)."""
    if not terms:
        return None
    texts = {name: doc.get(name) or "" for name in SEARCH_FIELDS}
    joined = "\n".join(_norm(t) for t in texts.values())
    if not all(term in joined for term in terms):
        return False
    for name, text in texts.items():
        at = _norm(text).find(terms[0])
        if at >= 0:
            start = max(at - SNIPPET_BEFORE, 0)
            snippet = text[start:at + len(terms[0]) + SNIPPET_AFTER]
            return {"field": name, "snippet": ("…" if start else "") + " ".join(snippet.split())}
    return {"field": None, "snippet": ""}


def _fingerprint(terms: list[str], filters: SearchFilters) -> str:
    raw = json.dumps({"terms": terms, "filters": asdict(filters)}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _encode(fp: str, offset: int) -> str:
    raw = json.dumps({"q": fp, "o": offset}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode(cursor: str, fp: str) -> int:
    """같은 검색어·필터로 만든 커서만 받는다. 다른 검색의 커서나 망가진 값은 InvalidCursor(422)."""
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        offset = data["o"]
        ok = data["q"] == fp and isinstance(offset, int) and offset >= 0
    except (ValueError, TypeError, KeyError):
        ok = False
    if not ok:
        raise InvalidCursor()
    return offset


def _scan(store: Store, ctx: RequestContext) -> tuple[list[dict], bool]:
    docs, cursor = [], None
    while True:
        page = store.list(ctx, COLLECTION, limit=100, cursor=cursor, descending=True)  # 최신 접수부터
        docs += page.items
        cursor = page.next_cursor
        if len(docs) >= MAX_SCAN:
            return docs[:MAX_SCAN], bool(cursor) or len(docs) > MAX_SCAN
        if not cursor:
            return docs, False


def search_materials(store: Store, ctx: RequestContext, query: str, filters: SearchFilters,
                     cursor: str | None = None, limit: int = 20) -> SearchPage:
    limit = max(1, min(int(limit), MAX_PAGE_SIZE))
    terms = _terms(query)
    fp = _fingerprint(terms, filters)
    offset = _decode(cursor, fp) if cursor else 0

    docs, truncated = _scan(store, ctx)
    kept = [d for d in docs if is_kept(d)]
    matched = []
    for doc in kept:
        if not _passes_filters(doc, filters):
            continue
        found = _match(doc, terms)
        if found is not False:
            matched.append((doc, found))
    matched.sort(key=lambda pair: pair[0].get("id", ""))
    matched.sort(key=lambda pair: pair[0].get("registered_at") or "", reverse=True)  # 최신 접수 → ID

    window = matched[offset:offset + limit]
    end = offset + len(window)
    return SearchPage(
        items=[{**public(doc), "match": found} for doc, found in window],
        next_cursor=_encode(fp, end) if end < len(matched) else None,
        total_matches=len(matched),
        scope={"scanned": len(docs), "scan_limit": MAX_SCAN, "truncated": truncated,
               "kept_scanned": len(kept), "fields": list(SEARCH_FIELDS)},
    )
