"""새 소식의 관심 키워드(설계 §6). AI 호출 없이 설정의 관심 분야와 활성 프로젝트 이름으로 만든다."""
from __future__ import annotations

import re

_SPLIT = re.compile(r"[·/,]")


def build_keywords(interests: list[str], project_names: list[str]) -> list[str]:
    """관심 분야를 `·`·`/`·`,`로 나누고 프로젝트 이름을 더한다. 2자 미만은 버리고 대소문자 무시로 중복을 없앤다."""
    words: list[str] = []
    seen: set[str] = set()
    candidates = [part for item in interests for part in _SPLIT.split(item or "")] + list(project_names)
    for raw in candidates:
        word = re.sub(r"\s+", " ", raw or "").strip()
        if len(word) < 2 or word.lower() in seen:
            continue
        seen.add(word.lower())
        words.append(word)
    return words


def match(keywords: list[str], text: str) -> list[str]:
    """text에 들어 있는 키워드. 영문·숫자 키워드는 단어 단위로, 한글이 든 키워드는 부분 일치로 찾는다."""
    lowered = (text or "").lower()
    found = []
    for word in keywords:
        if word.isascii():
            pattern = r"(?<![a-z0-9])" + re.escape(word.lower()) + r"(?![a-z0-9])"
            if re.search(pattern, lowered):
                found.append(word)
        elif word.lower() in lowered:
            found.append(word)
    return found
