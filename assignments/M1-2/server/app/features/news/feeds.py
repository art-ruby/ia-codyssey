"""RSS·Atom 피드 읽기(설계: docs/superpowers/specs/2026-10-04-ai-news-feed-design.md §4).

외부 접속은 URL 미리보기의 안전한 요청 함수(`url_preview._request`: 공개 IP 고정·리다이렉트 재검사·2MiB)를 쓴다.
DOCTYPE·ENTITY가 든 문서는 파싱하기 전에 거부한다.
"""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Callable

from app.features.materials import url_preview
from app.features.materials.url_keys import check_url

MAX_ENTRIES = 20
TITLE_LIMIT = 200
SUMMARY_LIMIT = 500
URL_LIMIT = 2048
FEED_TYPES = {"application/rss+xml", "application/atom+xml", "application/rdf+xml", "application/xml", "text/xml"}

Request = Callable[[str], tuple[int, dict, bytes, str]]


class FeedError(Exception):
    """피드를 읽지 못했다. message는 화면에 보여도 안전한 안내다."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Entry:
    title: str
    link: str
    summary: str
    published_at: str | None


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def plain_text(value: str) -> str:
    """HTML 조각을 한 줄 글로 바꾼다(태그·스크립트 제거, 공백 정리)."""
    parser = _Text()
    parser.feed(html.unescape(value or ""))
    parser.close()
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child(node: ET.Element, *names: str) -> ET.Element | None:
    for child in node:
        if _local(child.tag) in names:
            return child
    return None


def _text(node: ET.Element | None) -> str:
    return "".join(node.itertext()) if node is not None else ""


def parse_date(value: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


def _link(node: ET.Element) -> str:
    for child in node:
        if _local(child.tag) != "link":
            continue
        href = child.get("href")
        if href is not None:  # Atom
            if child.get("rel", "alternate") == "alternate":
                return href.strip()
            continue
        if _text(child).strip():
            return _text(child).strip()
    guid = _child(node, "guid", "id")
    return _text(guid).strip() if guid is not None and guid.get("isPermaLink", "true") != "false" else ""


def _safe_link(value: str) -> str | None:
    if not value or len(value) > URL_LIMIT:
        return None
    try:
        return check_url(value)
    except ValueError:
        return None


def parse_feed(data: bytes) -> list[Entry]:
    """피드 문서에서 글 목록(게시 시각 최신순, 최대 MAX_ENTRIES)을 뽑는다."""
    head = data[:4096].upper()
    if b"<!DOCTYPE" in head or b"<!ENTITY" in data.upper():
        raise FeedError("unsafe_feed", "안전하지 않은 형식(DOCTYPE)이 들어 있어 읽지 않았습니다.")
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        raise FeedError("not_feed", "RSS·Atom 피드 형식이 아닙니다.") from None
    kind = _local(root.tag)
    if kind == "rss":
        channel = _child(root, "channel")
        nodes = [n for n in (channel if channel is not None else []) if _local(n.tag) == "item"]
    elif kind == "rdf":
        nodes = [n for n in root if _local(n.tag) == "item"]
    elif kind == "feed":
        nodes = [n for n in root if _local(n.tag) == "entry"]
    else:
        raise FeedError("not_feed", "RSS·Atom 피드 형식이 아닙니다.")

    entries: list[Entry] = []
    seen: set[str] = set()
    for node in nodes:
        title = plain_text(_text(_child(node, "title")))[:TITLE_LIMIT]
        link = _safe_link(_link(node))
        if not title or not link or link in seen:
            continue
        seen.add(link)
        summary = plain_text(_text(_child(node, "description", "summary", "content")))[:SUMMARY_LIMIT]
        published = parse_date(_text(_child(node, "pubdate", "published", "updated", "date")))
        entries.append(Entry(title, link, summary, published))
    entries.sort(key=lambda e: e.published_at or "", reverse=True)
    return entries[:MAX_ENTRIES]


def read_feed(url: str, request: Request | None = None) -> list[Entry]:
    """공개 피드 주소를 읽어 글 목록을 돌려준다. 실패는 FeedError."""
    fetch = request or url_preview._request
    try:
        _, headers, body, _ = fetch(url)
    except url_preview.PreviewError as exc:
        raise FeedError("fetch_failed", str(exc)) from None
    content_type = (headers.get("content-type") or "").split(";")[0].strip().lower()
    if content_type and content_type not in FEED_TYPES:
        raise FeedError("not_feed", "RSS·Atom 피드 주소가 아닙니다(웹페이지 주소일 수 있습니다).")
    return parse_feed(body)
