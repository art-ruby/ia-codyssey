"""새 소식: 피드 파싱과 키워드(외부 접속 없음)."""
import pytest

from app.features.materials.url_preview import PreviewError
from app.features.news import feeds
from app.features.news.feeds import FeedError, parse_feed, read_feed
from app.features.news.keywords import build_keywords, match


def rss(*items: str) -> bytes:
    return ("<?xml version='1.0' encoding='utf-8'?><rss version='2.0'><channel><title>c</title>"
            + "".join(items) + "</channel></rss>").encode("utf-8")


def item(title, link, date="", desc=""):
    return (f"<item><title>{title}</title><link>{link}</link>"
            + (f"<pubDate>{date}</pubDate>" if date else "")
            + (f"<description><![CDATA[{desc}]]></description>" if desc else "") + "</item>")


def code_of(call):
    with pytest.raises(FeedError) as info:
        call()
    return info.value.code


def test_rss_items_are_parsed_sorted_newest_first_and_dates_normalized():
    data = rss(item("옛 글", "https://a.example/1", "Mon, 01 Sep 2026 10:00:00 +0900"),
               item("새 글", "https://a.example/2", "Fri, 03 Oct 2026 09:00:00 GMT"),
               item("날짜 없음", "https://a.example/3"))

    entries = parse_feed(data)

    assert [e.title for e in entries] == ["새 글", "옛 글", "날짜 없음"]
    assert entries[0].published_at == "2026-10-03T09:00:00+00:00"
    assert entries[1].published_at == "2026-09-01T01:00:00+00:00"
    assert entries[2].published_at is None


def test_atom_entries_use_alternate_link_and_summary():
    data = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Atom &amp; \xea\xb8\x80</title><link rel="self" href="https://x.example/self"/>
      <link rel="alternate" href="https://x.example/post"/><updated>2026-10-02T03:04:05Z</updated>
      <summary type="html">&lt;p&gt;\xec\x9a\x94\xec\x95\xbd &lt;b&gt;\xea\xb5\xb5\xea\xb2\x8c&lt;/b&gt;&lt;/p&gt;</summary></entry></feed>"""

    [entry] = parse_feed(data)

    assert entry.title == "Atom & 글"
    assert entry.link == "https://x.example/post"
    assert entry.summary == "요약 굵게"
    assert entry.published_at == "2026-10-02T03:04:05+00:00"


def test_only_newest_twenty_entries_are_kept():
    data = rss(*[item(f"글 {i:02d}", f"https://a.example/{i}", f"Thu, {i + 1:02d} Oct 2026 00:00:00 GMT")
                 for i in range(25)])

    entries = parse_feed(data)

    assert len(entries) == 20 and entries[0].title == "글 24" and entries[-1].title == "글 05"


def test_summary_html_and_scripts_are_removed_and_lengths_limited():
    data = rss(item("t" * 300, "https://a.example/x", desc="<script>alert(1)</script><p>안녕 <a href='#'>링크</a></p>" + "가" * 600))

    [entry] = parse_feed(data)

    assert "alert" not in entry.summary and entry.summary.startswith("안녕 링크")
    assert len(entry.title) == 200 and len(entry.summary) == 500


@pytest.mark.parametrize("link", ["javascript:alert(1)", "file:///etc/passwd", "ftp://a.example/x", "", "relative/path",
                                  "https://a.example/" + "x" * 2100])
def test_entries_with_unsafe_or_missing_links_are_skipped(link):
    data = rss(item("나쁜 링크", link), item("좋은 글", "https://a.example/ok"))

    assert [e.title for e in parse_feed(data)] == ["좋은 글"]


def test_entries_without_title_and_duplicate_links_are_skipped():
    data = rss(item("", "https://a.example/1"), item("하나", "https://a.example/2"), item("둘", "https://a.example/2"))

    assert [e.title for e in parse_feed(data)] == ["하나"]


def test_doctype_and_entity_documents_are_rejected_before_parsing():
    bomb = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><rss><channel></channel></rss>'

    assert code_of(lambda: parse_feed(bomb)) == "unsafe_feed"
    assert code_of(lambda: parse_feed(b'<rss><channel><!ENTITY x "y"></channel></rss>')) == "unsafe_feed"


@pytest.mark.parametrize("data", [b"<html><body>not a feed</body></html>", b"not xml at all", b"<rss><channel>"])
def test_non_feed_documents_are_rejected(data):
    assert code_of(lambda: parse_feed(data)) == "not_feed"


def test_read_feed_maps_fetch_errors_and_rejects_html_pages():
    def blocked(url):
        raise PreviewError("공개 웹사이트 주소만 미리 볼 수 있습니다.")

    def html_page(url):
        return 200, {"content-type": "text/html; charset=utf-8"}, b"<html></html>", url

    def feed(url):
        return 200, {"content-type": "application/rss+xml"}, rss(item("글", "https://a.example/1")), url

    with pytest.raises(FeedError) as info:
        read_feed("http://127.0.0.1/feed", blocked)
    assert info.value.code == "fetch_failed" and "공개 웹사이트" in info.value.message
    assert code_of(lambda: read_feed("https://a.example/", html_page)) == "not_feed"
    assert [e.title for e in read_feed("https://a.example/feed", feed)] == ["글"]


def test_read_feed_uses_the_safe_preview_request_by_default(monkeypatch):
    seen = []
    monkeypatch.setattr(feeds.url_preview, "_request",
                        lambda url: seen.append(url) or (200, {"content-type": "text/xml"}, rss(), url))

    read_feed("https://a.example/feed")

    assert seen == ["https://a.example/feed"]


def test_keywords_split_interests_add_projects_and_drop_short_or_duplicate_words():
    words = build_keywords(["AI Agent·Memory·협업", "개발 도구/API, 자동화", "X", "memory"], ["결제 개편", "Agent SDK"])

    assert words == ["AI Agent", "Memory", "협업", "개발 도구", "API", "자동화", "결제 개편", "Agent SDK"]


def test_keyword_matching_uses_word_boundaries_for_ascii_and_substrings_for_korean():
    words = ["API", "AI Agent", "자동화"]

    assert match(words, "New rapid release") == []
    assert match(words, "Public API pricing; ai agent memory") == ["API", "AI Agent"]
    assert match(words, "업무자동화 도구 출시") == ["자동화"]
