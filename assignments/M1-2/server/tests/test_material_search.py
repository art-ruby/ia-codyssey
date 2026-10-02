"""T05.01 보관함 검색: 보관 완료 자료만, 첫 페이지 밖 정답, 한글·긴 본문, 기간 경계, 모드 분리, 페이지, 검색 범위.

`search_materials` 단위 시험과 `GET /api/materials/search` API 시험을 함께 둔다.
"""

from __future__ import annotations

import itertools

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import InvalidCursor, MemoryStore
from app.features.materials import search
from app.features.materials.search import SearchFilters, search_materials
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
SAMPLE = RequestContext(OWNER, "sample", None)
_ids = itertools.count()


def kept(store, ctx=ME, registered="2026-10-02T03:00:00+00:00", **fields):
    """보관 완료 자료를 만든다. registered: 접수 시각(UTC)."""
    data = {"source_type": "url" if fields.get("url") else "text", "title": "", "description": "", "body": "",
            "save_reason": "", "memo": "", "url": None, "primary_project_id": None, "related_project_ids": [],
            "review_status": "approved", "copy_status": "not_applicable", "lifecycle": "active",
            "registered_at": registered, **fields}
    return store.create(ctx, "materials", data, doc_id=f"m{next(_ids):04d}")


def find(store, q="", ctx=ME, limit=20, cursor=None, **filters):
    return search_materials(store, ctx, q, SearchFilters(**filters), cursor, limit)


def titles(page):
    return [m["title"] for m in page.items]


# ── 검색 대상과 일치 ─────────────────────────────────────────────

def test_answer_outside_first_list_page_is_found():
    store = MemoryStore()
    kept(store, title="정답 자료", body="찾아야 하는 결제 개편 문서", registered="2026-09-01T00:00:00+00:00")
    for i in range(30):
        kept(store, title=f"다른 자료 {i}", body="관계없는 내용", registered=f"2026-10-01T00:{i:02d}:00+00:00")
    page = find(store, "결제 개편")
    assert titles(page) == ["정답 자료"] and page.total_matches == 1


def test_korean_partial_case_insensitive_and_all_terms():
    store = MemoryStore()
    kept(store, title="정산 API 종료", body="인증 방식을 OAuth로 바꿔야 한다", registered="2026-10-02T00:00:00+00:00")
    kept(store, title="정산 보고서", body="월간 매출 정리", registered="2026-10-01T00:00:00+00:00")
    assert titles(find(store, "정산")) == ["정산 API 종료", "정산 보고서"]
    assert titles(find(store, "oauth")) == ["정산 API 종료"]
    assert titles(find(store, "정산 oauth")) == ["정산 API 종료"]  # 모든 검색어 포함
    assert titles(find(store, "정산 없는단어")) == []


@pytest.mark.parametrize("field", ["title", "description", "body", "save_reason", "memo", "url"])
def test_each_user_field_is_searched(field):
    store = MemoryStore()
    value = "https://example.com/특별한-검색어" if field == "url" else "특별한검색어 포함"
    kept(store, **{field: value}, **({} if field == "title" else {"title": "제목"}))
    assert find(store, "특별한").total_matches == 1


def test_ai_fields_are_not_searched():
    store = MemoryStore()
    kept(store, title="제목", ai_summary="AI만 쓴 표현 독특단어", ai_keywords=["독특단어"])
    assert find(store, "독특단어").total_matches == 0


def test_long_body_end_is_searched():
    store = MemoryStore()
    kept(store, title="긴 자료", body="가" * 19990 + "끝부분단어")
    page = find(store, "끝부분단어")
    assert titles(page) == ["긴 자료"]
    assert "끝부분단어" in page.items[0]["match"]["snippet"] and page.items[0]["match"]["field"] == "body"


def test_unapproved_trashed_and_other_mode_are_excluded():
    store = MemoryStore()
    kept(store, title="보관된 대상")
    kept(store, title="미검토 대상", review_status="unreviewed")
    kept(store, title="나중에 대상", review_status="later")
    kept(store, title="휴지통 대상", lifecycle="trash")
    kept(store, ctx=SAMPLE, title="표본 대상")
    assert titles(find(store, "대상")) == ["보관된 대상"]
    assert titles(find(store, "대상", ctx=SAMPLE)) == ["표본 대상"]


def test_empty_query_lists_all_kept_newest_first():
    store = MemoryStore()
    kept(store, title="이전", registered="2026-10-01T00:00:00+00:00")
    kept(store, title="최근", registered="2026-10-02T00:00:00+00:00")
    assert titles(find(store, "  ")) == ["최근", "이전"]


# ── 필터 ─────────────────────────────────────────────────────────

def test_period_uses_seoul_dates_inclusive():
    store = MemoryStore()
    kept(store, title="10월1일 밤", registered="2026-10-01T14:59:00+00:00")  # 서울 10-01 23:59
    kept(store, title="10월2일 자정", registered="2026-10-01T15:00:00+00:00")  # 서울 10-02 00:00
    assert titles(find(store, date_to="2026-10-01")) == ["10월1일 밤"]
    assert titles(find(store, date_from="2026-10-02")) == ["10월2일 자정"]
    assert len(find(store, date_from="2026-10-01", date_to="2026-10-02").items) == 2


def test_project_filter_includes_primary_and_related():
    store = MemoryStore()
    kept(store, title="주", primary_project_id="p1")
    kept(store, title="관련", related_project_ids=["p2", "p1"])
    kept(store, title="무관", primary_project_id="p2")
    assert sorted(titles(find(store, project_id="p1"))) == ["관련", "주"]


def test_kind_and_source_filters():
    store = MemoryStore()
    kept(store, title="링크", url="https://example.com/a", ai_kind="article")
    kept(store, title="메모", body="텍스트", ai_kind="note")
    assert titles(find(store, source_type="url")) == ["링크"]
    assert titles(find(store, kind="note")) == ["메모"]


# ── 페이지·범위 ───────────────────────────────────────────────────

def test_pages_do_not_overlap_and_end():
    store = MemoryStore()
    for i in range(45):
        kept(store, title=f"결과 {i:02d}", body="공통어", registered=f"2026-10-01T{i // 60:02d}:{i % 60:02d}:00+00:00")
    seen, cursor, sizes = [], None, []
    while True:
        page = find(store, "공통어", cursor=cursor)
        sizes.append(len(page.items))
        seen += titles(page)
        cursor = page.next_cursor
        if not cursor:
            break
    assert sizes == [20, 20, 5] and len(set(seen)) == 45 and page.total_matches == 45


def test_cursor_from_another_query_is_rejected():
    store = MemoryStore()
    for i in range(25):
        kept(store, title=f"자료 {i}", body="공통어")
    cursor = find(store, "공통어").next_cursor
    with pytest.raises(InvalidCursor):
        find(store, "다른 검색어", cursor=cursor)


def test_scope_reports_partial_search(monkeypatch):
    monkeypatch.setattr(search, "MAX_SCAN", 5)
    store = MemoryStore()
    for i in range(8):
        kept(store, title=f"자료 {i}", registered=f"2026-10-01T00:0{i}:00+00:00")
    page = find(store)
    assert page.scope["truncated"] is True and page.scope["scanned"] == 5
    assert titles(page) == [f"자료 {i}" for i in range(7, 2, -1)]  # 최신 5건 기준


# ── API ──────────────────────────────────────────────────────────

def make_client(store=None, raise_errors=True):
    store = store or MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store)
    return TestClient(app, raise_server_exceptions=raise_errors), store


H = {"Authorization": "Bearer t", "X-Data-Mode": "personal"}


def test_api_returns_search_page():
    c, store = make_client()
    kept(store, title="결제 개편 회의", body="정산 일정")
    res = c.get("/api/materials/search", params={"q": "결제", "limit": 5}, headers=H)
    assert res.status_code == 200
    body = res.json()
    assert [m["title"] for m in body["items"]] == ["결제 개편 회의"]
    assert body["total_matches"] == 1 and body["next_cursor"] is None
    assert body["scope"]["fields"] == list(search.SEARCH_FIELDS) and body["scope"]["truncated"] is False


@pytest.mark.parametrize("params", [
    {"date_from": "2026-10-03", "date_to": "2026-10-01"},
    {"date_from": "2026/10/01"},
    {"limit": 51},
    {"source_type": "file"},
    {"cursor": "망가진커서"},
])
def test_api_rejects_bad_input(params):
    c, _ = make_client()
    assert c.get("/api/materials/search", params=params, headers=H).status_code == 422


def test_store_failure_is_an_error_not_zero_results(monkeypatch):
    c, store = make_client(raise_errors=False)

    def broken(*_args, **_kwargs):
        raise RuntimeError("저장소 연결 실패")

    monkeypatch.setattr(store, "list", broken)
    res = c.get("/api/materials/search", params={"q": "아무거나"}, headers=H)
    assert res.status_code >= 500
