"""URL 검사와 같은 URL 판정용 비교 키(T03.02, PRD §6.1).

- 검사: http(s)이고 호스트가 있으며, 포트가 숫자 0~65535이고, 공백이 없어야 한다. 원래 문자열은 바꾸지 않는다.
- 비교 키: 스킴·호스트 소문자, 기본 포트(80/443) 제거만 한다. 경로·쿼리·조각은 그대로 두어
  추적 쿼리가 다른 링크를 같은 것으로 합치지 않는다. IPv6 호스트는 대괄호를 유지한다.
"""
from __future__ import annotations

import hashlib
from urllib.parse import urlsplit, urlunsplit

DEFAULT_PORTS = {"http": 80, "https": 443}


def check_url(value: str) -> str:
    if any(ch.isspace() for ch in value):
        raise ValueError("URL에 공백을 넣을 수 없습니다")
    try:
        parts = urlsplit(value)
        parts.port  # 숫자가 아니거나 0~65535 밖이면 ValueError
    except ValueError:
        raise ValueError("URL의 주소나 포트 형식이 올바르지 않습니다") from None
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise ValueError("URL은 http:// 또는 https://로 시작하는 주소여야 합니다")
    return value


def url_key(url: str) -> str:
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if ":" in host:  # IPv6 주소는 대괄호로 감싸야 주소와 포트가 구분된다
        host = f"[{host}]"
    port = parts.port
    if port is not None and port != DEFAULT_PORTS.get(scheme):
        host = f"{host}:{port}"
    userinfo = parts.netloc.rpartition("@")[0]
    netloc = f"{userinfo}@{host}" if userinfo else host
    return urlunsplit((scheme, netloc, parts.path, parts.query, parts.fragment))


def url_index_id(owner_id: str, mode: str, key: str) -> str:
    """동시 등록을 막는 URL별 예약 문서 ID(소유자·모드·비교 키 단위)."""
    return "url-" + hashlib.sha256(f"{owner_id}\n{mode}\n{key}".encode()).hexdigest()[:40]
