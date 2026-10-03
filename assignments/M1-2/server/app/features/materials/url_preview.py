"""외부 URL의 제목·설명·본문을 안전하게 미리 가져온다.

사용자가 URL을 제출하기 전 명시적으로 요청하는 미리보기다. 개인 주소,
임의 포트, 비공개 IP, 큰 응답, 무제한 리디렉션은 허용하지 않는다.
"""
from __future__ import annotations

import html
import http.client
import ipaddress
import json
import re
import socket
import ssl
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

from app.features.materials.url_keys import check_url

MAX_BYTES = 2 * 1024 * 1024
MAX_TEXT = 20_000
TIMEOUT_SECONDS = 10
MAX_REDIRECTS = 4
USER_AGENT = "AISecretaryLinkPreview/1.0 (+https://ia-codyssey-web.vercel.app)"
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


class PreviewError(ValueError):
    """미리보기 실패. 사용자에게 보여도 안전한 안내만 담는다."""


class _PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host: str, address: str, **kwargs):
        super().__init__(host, **kwargs)
        self.address = address

    def connect(self):
        self.sock = socket.create_connection((self.address, self.port), self.timeout,
                                             self.source_address)


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, **kwargs):
        super().__init__(host, **kwargs)
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, self.port), self.timeout,
                                       self.source_address)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def _public_address(host: str, port: int) -> str:
    try:
        literal = ipaddress.ip_address(host)
        addresses = [str(literal)]
    except ValueError:
        try:
            addresses = list(dict.fromkeys(
                item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            ))
        except socket.gaierror:
            raise PreviewError("사이트 주소를 찾을 수 없습니다. URL을 확인해 주세요.") from None
    if not addresses or any(not ipaddress.ip_address(item).is_global for item in addresses):
        raise PreviewError("공개 웹사이트 주소만 미리 볼 수 있습니다.")
    return addresses[0]


def _request(url: str) -> tuple[int, dict[str, str], bytes, str]:
    """공개 HTTP(S) 주소에만 연결하고 리디렉션마다 주소를 다시 검사한다."""
    current = url
    for hop in range(MAX_REDIRECTS + 1):
        try:
            parts = urlsplit(current)
            scheme = parts.scheme.lower()
            host = parts.hostname or ""
            if ":" not in host:
                host = host.encode("idna").decode("ascii")
            port = parts.port if parts.port is not None else (443 if scheme == "https" else 80)
        except ValueError:
            raise PreviewError("사이트 주소가 올바르지 않습니다.") from None
        if scheme not in {"http", "https"} or not host or parts.username or parts.password:
            raise PreviewError("http 또는 https 웹 주소를 입력해 주세요.")
        if port not in {80, 443} or (scheme == "http" and port != 80) or (scheme == "https" and port != 443):
            raise PreviewError("보안을 위해 기본 웹 포트(80 또는 443)만 지원합니다.")
        address = _public_address(host, port)
        path = urlunsplit(("", "", parts.path or "/", parts.query, ""))
        connection_type = _PinnedHTTPS if scheme == "https" else _PinnedHTTP
        kwargs = {"port": port, "timeout": TIMEOUT_SECONDS}
        if scheme == "https":
            kwargs["context"] = ssl.create_default_context()
        conn = connection_type(host, address, **kwargs)
        try:
            conn.request("GET", path, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,text/plain,application/json;q=0.8,*/*;q=0.1",
                "Accept-Encoding": "identity",
                "Connection": "close",
            })
            response = conn.getresponse()
            headers = {key.lower(): value for key, value in response.getheaders()}
            if response.status in {301, 302, 303, 307, 308}:
                location = headers.get("location")
                if not location or hop == MAX_REDIRECTS:
                    raise PreviewError("페이지가 너무 여러 번 이동해 내용을 가져오지 못했습니다.")
                current = urljoin(current, location)
                continue
            if response.status < 200 or response.status >= 300:
                raise PreviewError(f"사이트가 내용을 공개하지 않았습니다 (HTTP {response.status}).")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise PreviewError("페이지가 너무 커서 미리 볼 수 없습니다.")
            return response.status, headers, body, current
        except PreviewError:
            raise
        except (OSError, http.client.HTTPException, ssl.SSLError, TimeoutError):
            raise PreviewError("사이트에 연결하지 못했습니다. 잠시 뒤 다시 시도해 주세요.") from None
        finally:
            conn.close()
    raise PreviewError("페이지 내용을 가져오지 못했습니다.")


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "svg", "noscript", "iframe", "template"}
    BLOCK = {"address", "article", "blockquote", "br", "div", "h1", "h2", "h3", "h4", "li",
             "main", "p", "section", "td", "th", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.meta_title = ""
        self.description = ""
        self.all_parts: list[str] = []
        self.article_parts: list[str] = []
        self.skip_depth = 0
        self.title_depth = 0
        self.article_depth = 0
        self.main_depth = 0

    def handle_starttag(self, tag, attrs):
        values = {key.lower(): value or "" for key, value in attrs}
        if tag in self.SKIP:
            self.skip_depth += 1
        if tag == "title":
            self.title_depth += 1
        if tag in {"article"}:
            self.article_depth += 1
        if tag == "main" or values.get("role") == "main":
            self.main_depth += 1
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            if key in {"og:title", "twitter:title"} and not self.meta_title and values.get("content"):
                self.meta_title = values["content"]
            if key in {"description", "og:description", "twitter:description"} and not self.description:
                self.description = values.get("content", "")
        if tag in self.BLOCK:
            self.all_parts.append("\n")
            if self.article_depth or self.main_depth:
                self.article_parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        if tag == "article" and self.article_depth:
            self.article_depth -= 1
        if (tag == "main" or tag == "body") and self.main_depth:
            self.main_depth -= 1
        if tag in self.BLOCK:
            self.all_parts.append("\n")
            if self.article_depth or self.main_depth:
                self.article_parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self.title_depth:
            self.title_parts.append(text)
        self.all_parts.append(text)
        if self.article_depth or self.main_depth:
            self.article_parts.append(text)

    def result(self) -> tuple[str, str, str]:
        clean = lambda parts: re.sub(r"\n{3,}", "\n\n", "\n".join(parts)).strip()
        title = re.sub(r"\s+", " ", self.meta_title or " ".join(self.title_parts)).strip()
        body = clean(self.article_parts) or clean(self.all_parts)
        return title[:200], html.unescape(self.description).strip()[:2000], body[:MAX_TEXT]


def _decode(body: bytes, content_type: str) -> str:
    charset = re.search(r"charset\s*=\s*[\"']?([\w.-]+)", content_type, re.I)
    encoding = charset.group(1) if charset else "utf-8"
    try:
        return body.decode(encoding, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _html_result(body: bytes, content_type: str) -> tuple[str, str, str]:
    if "html" not in content_type.lower():
        if "text/plain" in content_type.lower():
            text = _decode(body, content_type).strip()
            return "", "", text[:MAX_TEXT]
        raise PreviewError("이 페이지는 읽을 수 있는 웹 문서 형식이 아닙니다.")
    parser = _TextExtractor()
    parser.feed(_decode(body, content_type))
    return parser.result()


def _youtube(url: str) -> dict:
    query = urlencode({"url": url, "format": "json"})
    _, headers, body, _ = _request(f"https://www.youtube.com/oembed?{query}")
    try:
        metadata = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise PreviewError("YouTube 영상 정보를 읽지 못했습니다.") from None
    title = str(metadata.get("title", ""))[:200]
    author = str(metadata.get("author_name", ""))[:200]
    # oEmbed에는 설명·자막이 없다. 공개 페이지의 설명과 공개 자막 트랙을 가능한 범위에서 읽는다.
    description = ""
    transcript = ""
    try:
        _, page_headers, page, _ = _request(url)
        page_html = _decode(page, page_headers.get("content-type", ""))
        _, description, page_text = _html_result(page, page_headers.get("content-type", ""))
        if not description:
            description = page_text[:2000]
        transcript = _youtube_transcript(page_html)
    except PreviewError:
        # 영상 페이지가 봇 차단·지역 제한을 걸어도 oEmbed 제목은 보여 준다.
        pass
    if transcript:
        body = transcript
        notice = "YouTube 제목과 공개 자막을 가져왔습니다. 자막 내용을 확인한 뒤 접수하세요."
    elif description:
        body = description
        notice = "YouTube 제목과 공개 설명을 가져왔습니다. 공개 자막을 가져오지 못해 영상 설명을 본문으로 표시합니다."
    else:
        body = ""
        notice = "YouTube 영상 제목은 가져왔지만 설명·자막을 읽지 못했습니다. 본문을 직접 붙여 넣을 수 있습니다."
    return {
        "title": title,
        "description": description[:2000],
        "body": body[:MAX_TEXT],
        "source": "youtube_metadata",
        "notice": notice,
        "author": author,
    }


def _youtube_transcript(page_html: str) -> str:
    """페이지에 공개 자막 트랙이 있는 경우에만 가져온다. 로그인은 시도하지 않는다."""
    marker = "ytInitialPlayerResponse"
    start = page_html.find(marker)
    if start < 0:
        return ""
    brace = page_html.find("{", start + len(marker))
    if brace < 0:
        return ""
    try:
        player, _ = json.JSONDecoder().raw_decode(page_html[brace:])
        tracks = player.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    except (json.JSONDecodeError, AttributeError, TypeError):
        return ""
    if not tracks or not isinstance(tracks[0], dict) or not tracks[0].get("baseUrl"):
        return ""
    try:
        _, headers, data, _ = _request(tracks[0]["baseUrl"])
        if len(data) > MAX_BYTES:
            return ""
        root = ET.fromstring(data)
    except (PreviewError, ET.ParseError):
        return ""
    segments = [html.unescape("".join(node.itertext())).strip() for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] == "text"]
    return "\n".join(segment for segment in segments if segment)[:MAX_TEXT]


def preview_url(raw_url: str) -> dict:
    url = check_url(raw_url)
    host = (urlsplit(url).hostname or "").lower()
    if host in YOUTUBE_HOSTS:
        return _youtube(url)
    _, headers, body, _ = _request(url)
    title, description, text = _html_result(body, headers.get("content-type", ""))
    if not (title or description or text):
        raise PreviewError("페이지에서 읽을 수 있는 제목·설명·본문을 찾지 못했습니다.")
    return {
        "title": title,
        "description": description,
        "body": text,
        "source": "webpage",
        "notice": "페이지 내용을 가져왔습니다. 저장 전에 제목과 본문을 확인해 주세요.",
    }
