"""새 소식: 수집 조건·저장·숨기기·출처 관리·API(가짜 요청 함수, 외부 접속 없음)."""
import itertools
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.materials.url_preview import PreviewError
from app.features.news import service
from app.features.news.sources import DEFAULT_SOURCES
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
T0 = datetime(2026, 10, 4, 9, 0, tzinfo=timezone.utc)
_keys = itertools.count()
OPENAI = DEFAULT_SOURCES[0][2]
GEEK = DEFAULT_SOURCES[4][2]


def rss(*entries):
    body = "".join(f"<item><title>{t}</title><link>{l}</link><pubDate>{d}</pubDate>"
                   f"<description>{s}</description></item>" for t, l, d, s in entries)
    return f"<rss><channel>{body}</channel></rss>".encode("utf-8")


class FakeFeeds:
    """URL별 응답. 등록하지 않은 주소는 접근 제한(429)처럼 실패한다."""

    def __init__(self, feeds=None):
        self.feeds = dict(feeds or {})
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if url not in self.feeds:
            raise PreviewError("사이트가 내용을 공개하지 않았습니다 (HTTP 429).")
        return 200, {"content-type": "application/rss+xml"}, self.feeds[url], url


DEFAULT_FEEDS = {
    OPENAI: rss(("GPT agent memory update", "https://openai.com/n/1", "Fri, 03 Oct 2026 10:00:00 GMT", "Agent 기능"),
                ("Pricing change", "https://openai.com/n/2", "Thu, 02 Oct 2026 10:00:00 GMT", "새 가격")),
    GEEK: rss(("업무 자동화 도구 소개", "https://news.hada.io/t/1", "Sat, 04 Oct 2026 01:00:00 GMT", "자동화"),
              ("오늘의 잡담", "https://news.hada.io/t/2", "Sat, 04 Oct 2026 02:00:00 GMT", "잡담")),
}


def make_client(feeds=None):
    store = MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store)
    fake = FakeFeeds(DEFAULT_FEEDS if feeds is None else feeds)
    app.state.news_request = fake
    return TestClient(app), store, fake


def h(mode="personal", key=True):
    headers = {"Authorization": "Bearer t", "X-Data-Mode": mode}
    if key:
        headers["Idempotency-Key"] = f"n{next(_keys)}"
    return headers


# ── 수집 조건 ───────────────────────────────────────────────────

def test_first_view_starts_a_refresh_and_the_next_view_shows_items():
    c, _, fake = make_client()

    first = c.get("/api/news", headers=h(key=False)).json()
    second = c.get("/api/news", headers=h(key=False)).json()

    assert first["state"]["refreshing"] is True and first["items"] == []
    assert second["state"]["refreshing"] is False and second["total"] == 4
    enabled = [url for _, _, url, _, on in DEFAULT_SOURCES if on]
    assert sorted(fake.calls) == sorted(enabled)  # 꺼진 Reddit은 읽지 않는다


def test_auto_refresh_waits_six_hours_after_success_and_manual_waits_five_minutes():
    store, fake = MemoryStore(), FakeFeeds(DEFAULT_FEEDS)
    assert service.claim_refresh(store, ME, manual=False, now=T0)
    service.run_refresh(store, ME, fake, now=T0)

    assert not service.claim_refresh(store, ME, manual=False, now=T0 + timedelta(hours=5))
    assert not service.claim_refresh(store, ME, manual=True, now=T0 + timedelta(minutes=4))
    assert service.claim_refresh(store, ME, manual=True, now=T0 + timedelta(minutes=6))


def test_auto_refresh_runs_again_after_six_hours():
    store, fake = MemoryStore(), FakeFeeds(DEFAULT_FEEDS)
    service.claim_refresh(store, ME, manual=False, now=T0)
    service.run_refresh(store, ME, fake, now=T0)

    assert service.claim_refresh(store, ME, manual=False, now=T0 + timedelta(hours=6, minutes=1))


def test_only_one_request_claims_the_refresh_and_a_crashed_lease_expires():
    store = MemoryStore()

    assert service.claim_refresh(store, ME, manual=False, now=T0)
    assert not service.claim_refresh(store, ME, manual=True, now=T0 + timedelta(seconds=1))
    # 수집이 끝나지 못한 채 서버가 꺼졌다: 표시 기한(3분)과 최소 간격(5분)이 지나면 다시 수집한다.
    assert service.claim_refresh(store, ME, manual=False, now=T0 + timedelta(minutes=6))


def test_when_every_source_fails_old_items_stay_and_next_open_retries():
    store = MemoryStore()
    service.claim_refresh(store, ME, manual=False, now=T0)
    service.run_refresh(store, ME, FakeFeeds(DEFAULT_FEEDS), now=T0)
    later = T0 + timedelta(hours=7)
    service.claim_refresh(store, ME, manual=False, now=later)

    results = service.run_refresh(store, ME, FakeFeeds({}), now=later)

    assert all(not r["ok"] for r in results.values())
    view = service.news_view(store, ME)
    assert view["total"] == 4
    assert view["state"]["last_success_at"] == T0.isoformat()
    assert len(view["state"]["failures"]) == 6 and "HTTP 429" in view["state"]["failures"][0]["error"]
    assert service.claim_refresh(store, ME, manual=False, now=later + timedelta(minutes=6))


def test_partial_failure_keeps_successful_sources_and_reports_failed_ones():
    c, _, _ = make_client()
    c.get("/api/news", headers=h(key=False))

    view = c.get("/api/news", headers=h(key=False)).json()

    names = {f["source_name"] for f in view["state"]["failures"]}
    assert "OpenAI News" not in names and "GeekNews" not in names and "Google AI 블로그" in names
    assert view["state"]["last_success_at"]


def test_refetching_does_not_duplicate_or_reset_hidden_items():
    store, fake = MemoryStore(), FakeFeeds(DEFAULT_FEEDS)
    service.run_refresh(store, ME, fake, now=T0)
    hidden = service.news_view(store, ME)["items"][0]["id"]
    service.set_hidden(store, ME, hidden, True)

    service.run_refresh(store, ME, fake, now=T0 + timedelta(hours=7))

    view = service.news_view(store, ME)
    assert view["total"] == 3 and hidden not in [i["id"] for i in view["items"]]


# ── 순서·키워드 ─────────────────────────────────────────────────

def test_keyword_matches_come_first_then_newest_first():
    store = MemoryStore()
    service.run_refresh(store, ME, FakeFeeds(DEFAULT_FEEDS), now=T0)

    items = service.news_view(store, ME)["items"]

    # 기본 관심 분야: AI Agent·Memory·협업 / 자동화 / 개발 도구·API / 콘텐츠 생성 / 모델·서비스·가격·정책 변화
    assert [i["title"] for i in items] == ["업무 자동화 도구 소개", "GPT agent memory update", "Pricing change", "오늘의 잡담"]
    assert items[0]["matched_keywords"] == ["자동화"]
    assert items[1]["matched_keywords"] == ["Memory"]
    assert items[2]["matched_keywords"] == ["가격"]
    assert items[3]["matched_keywords"] == []


def test_paging_uses_offset_cursor_and_rejects_bad_cursor(monkeypatch):
    monkeypatch.setattr(service, "PAGE_SIZE", 3)
    c, _, _ = make_client()
    c.get("/api/news", headers=h(key=False))

    first = c.get("/api/news", headers=h(key=False)).json()
    second = c.get(f"/api/news?cursor={first['next_cursor']}", headers=h(key=False)).json()

    assert len(first["items"]) == 3 and first["next_cursor"] == "3"
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    assert c.get("/api/news?cursor=abc", headers=h(key=False)).status_code == 422


# ── 저장·숨기기 ────────────────────────────────────────────────

def _first_id(c):
    c.get("/api/news", headers=h(key=False))
    return c.get("/api/news", headers=h(key=False)).json()["items"][0]


def test_save_creates_an_inbox_material_from_the_feed_item():
    c, _, _ = make_client()
    item = _first_id(c)

    res = c.post(f"/api/news/{item['id']}/save", headers=h())

    body = res.json()
    assert res.status_code == 200 and body["created"] is True
    material = c.get(f"/api/materials/{body['material_id']}", headers=h(key=False)).json()
    assert material["url"] == item["link"] and material["title"] == item["title"]
    assert material["body"] == item["summary"] and material["description"] == "" and material["save_reason"] == ""
    assert material["review_status"] == "unreviewed"
    inbox = c.get("/api/materials?view=inbox", headers=h(key=False)).json()["items"]
    assert [m["id"] for m in inbox] == [body["material_id"]]
    after = c.get("/api/news", headers=h(key=False)).json()["items"]
    assert next(i for i in after if i["id"] == item["id"])["saved_material_id"] == body["material_id"]


def test_save_links_to_an_existing_material_with_the_same_url():
    c, _, _ = make_client()
    item = _first_id(c)
    existing = c.post("/api/materials", json={"url": item["link"]}, headers=h()).json()

    body = c.post(f"/api/news/{item['id']}/save", headers=h()).json()

    assert body == {**body, "material_id": existing["id"], "created": False}
    assert len(c.get("/api/materials?view=inbox", headers=h(key=False)).json()["items"]) == 1


def test_save_twice_with_new_keys_or_the_same_key_creates_one_material():
    c, _, _ = make_client()
    item = _first_id(c)
    headers = h()

    first = c.post(f"/api/news/{item['id']}/save", headers=headers).json()
    replay = c.post(f"/api/news/{item['id']}/save", headers=headers).json()
    again = c.post(f"/api/news/{item['id']}/save", headers=h()).json()

    assert first["material_id"] == replay["material_id"] == again["material_id"]
    assert again["created"] is False
    assert len(c.get("/api/materials?view=inbox", headers=h(key=False)).json()["items"]) == 1


def test_hide_and_unhide():
    c, _, _ = make_client()
    item = _first_id(c)

    assert c.post(f"/api/news/{item['id']}/hide", headers=h()).json()["hidden"] is True
    assert item["id"] not in [i["id"] for i in c.get("/api/news", headers=h(key=False)).json()["items"]]
    c.post(f"/api/news/{item['id']}/unhide", headers=h())
    assert item["id"] in [i["id"] for i in c.get("/api/news", headers=h(key=False)).json()["items"]]


def test_change_requests_need_an_idempotency_key_and_unknown_items_are_404():
    c, _, _ = make_client()
    item = _first_id(c)

    assert c.post(f"/api/news/{item['id']}/save", headers=h(key=False)).status_code == 422
    assert c.post("/api/news/news-unknown/hide", headers=h()).status_code == 404


# ── 정리 ───────────────────────────────────────────────────────

def test_cleanup_drops_unsaved_items_older_than_30_days_and_keeps_saved():
    store = MemoryStore()
    service.run_refresh(store, ME, FakeFeeds(DEFAULT_FEEDS), now=T0)
    saved = service.news_view(store, ME)["items"][0]["id"]
    service.save_item(store, ME, saved)

    service.cleanup(store, ME, T0 + timedelta(days=31))

    assert [i["id"] for i in service.news_view(store, ME)["items"]] == [saved]


def test_cleanup_caps_total_items_dropping_oldest_unsaved(monkeypatch):
    monkeypatch.setattr(service, "MAX_ITEMS", 2)
    store = MemoryStore()
    service.run_refresh(store, ME, FakeFeeds(DEFAULT_FEEDS), now=T0)

    titles = [i["title"] for i in service.news_view(store, ME)["items"]]

    assert sorted(titles) == ["업무 자동화 도구 소개", "오늘의 잡담"]  # 게시 시각이 가장 늦은 두 글


# ── 출처 관리 ───────────────────────────────────────────────────

def test_default_sources_are_created_once_and_reddit_is_off():
    c, _, _ = make_client()

    first = c.get("/api/news/sources", headers=h(key=False)).json()["items"]
    second = c.get("/api/news/sources", headers=h(key=False)).json()["items"]

    assert [s["id"] for s in first] == [s["id"] for s in second] and len(first) == 7
    assert [s["name"] for s in first if not s["enabled"]] == ["Reddit r/LocalLLaMA"]
    assert all(s["builtin"] for s in first)


def test_add_source_checks_the_feed_and_rejects_duplicates_and_non_feeds():
    custom = "https://blog.example/feed.xml"
    c, _, _ = make_client({**DEFAULT_FEEDS, custom: rss(("글", "https://blog.example/1", "", ""))})

    added = c.post("/api/news/sources", json={"name": "내 블로그", "feed_url": custom}, headers=h())
    dup = c.post("/api/news/sources", json={"name": "또", "feed_url": "HTTPS://Blog.Example/feed.xml"}, headers=h())
    bad = c.post("/api/news/sources", json={"name": "웹페이지", "feed_url": "https://nofeed.example/"}, headers=h())
    unsafe = c.post("/api/news/sources", json={"name": "x", "feed_url": "javascript:alert(1)"}, headers=h())

    assert added.status_code == 201 and added.json()["kind"] == "custom" and added.json()["builtin"] is False
    assert dup.status_code == 409 and dup.json()["reason"] == "duplicate_source"
    assert bad.status_code == 422 and bad.json()["reason"] == "fetch_failed"
    assert unsafe.status_code == 422


def test_source_limit_toggle_and_delete_rules(monkeypatch):
    monkeypatch.setattr(service, "MAX_SOURCES", 8)
    feeds = {**DEFAULT_FEEDS, "https://a.example/f": rss(), "https://b.example/f": rss()}
    c, _, fake = make_client(feeds)
    custom = c.post("/api/news/sources", json={"name": "A", "feed_url": "https://a.example/f"}, headers=h()).json()

    over = c.post("/api/news/sources", json={"name": "B", "feed_url": "https://b.example/f"}, headers=h())
    builtin = c.get("/api/news/sources", headers=h(key=False)).json()["items"][0]
    off = c.put(f"/api/news/sources/{builtin['id']}", json={"enabled": False, "expected_version": builtin["version"]},
                headers=h())
    stale = c.put(f"/api/news/sources/{builtin['id']}", json={"enabled": True, "expected_version": builtin["version"]},
                  headers=h())
    no_delete = c.delete(f"/api/news/sources/{builtin['id']}", headers=h())
    deleted = c.delete(f"/api/news/sources/{custom['id']}", headers=h())

    assert over.status_code == 422 and over.json()["reason"] == "too_many_sources"
    assert off.json()["enabled"] is False and stale.status_code == 409
    assert no_delete.status_code == 409 and no_delete.json()["reason"] == "builtin_source"
    assert deleted.json() == {"deleted": True, "id": custom["id"]}
    fake.calls.clear()
    c.get("/api/news", headers=h(key=False))
    assert builtin["feed_url"] not in fake.calls  # 끈 출처는 읽지 않는다


# ── 인증·모드·격리 ──────────────────────────────────────────────

@pytest.mark.parametrize("method,path", [("get", "/api/news"), ("post", "/api/news/refresh"),
                                         ("get", "/api/news/sources"), ("post", "/api/news/x/save")])
def test_news_requires_login_and_personal_mode(method, path):
    c, _, fake = make_client()

    assert getattr(c, method)(path).status_code == 401
    res = getattr(c, method)(path, headers=h("sample"))
    assert res.status_code == 422 and res.json()["reason"] == "personal_only"
    assert fake.calls == []


def test_other_owners_cannot_see_or_change_items():
    store, fake = MemoryStore(), FakeFeeds(DEFAULT_FEEDS)
    service.run_refresh(store, ME, fake, now=T0)
    mine = service.news_view(store, ME)["items"][0]["id"]
    other = RequestContext("owner-2", "personal", None)

    assert service.news_view(store, other)["total"] == 0
    with pytest.raises(Exception) as info:
        service.set_hidden(store, other, mine, True)
    assert type(info.value).__name__ == "NotFound"
