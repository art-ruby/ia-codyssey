# -*- coding: utf-8 -*-
"""일본어 판정.

regionCode=JP 로 검색했다고 그 영상이 일본어인 것은 아니다.
regionCode·relevanceLanguage 는 요청 파라미터라 모든 결과가 같은 값을
가지므로 판정에 쓸 수 없다. 실제로 쓸 수 있는 신호는 셋뿐이다.

  · 제목·설명의 일본 문자 비율   ← 주력. 항상 있다
  · default_audio_language      ← 있으면 강하다. 자주 빈다
  · 자막 언어                   ← 정확하나 수집 비용이 있다
"""
import re

# 히라가나 · 가타카나. 한자는 중국어와 겹쳐 단독 근거로 쓰지 않는다.
KANA = re.compile(r'[ぁ-んァ-ヶー]')
# 글자 수를 셀 때 공백·기호는 뺀다. 안 그러면 비율이 낮게 나온다.
NON_TEXT = re.compile(r'[\s\d\W_]', re.UNICODE)


def kana_ratio(text):
    """글자 중 가나가 차지하는 비율."""
    if not text:
        return 0.0
    body = NON_TEXT.sub("", text)
    if not body:
        return 0.0
    return len(KANA.findall(body)) / len(body)


def detect(title, description="", default_audio_language="", min_ratio=0.10):
    """(판정, 비율, 근거) 를 돌려준다.

    default_audio_language 가 있으면 그것을 우선한다 — 유튜버가 직접 설정한
    값이라 추정보다 정확하다. 다만 자주 비어 있어 주력으로 삼을 수는 없다.
    """
    lang = (default_audio_language or "").lower()
    if lang.startswith("ja"):
        return "ja", kana_ratio(f"{title} {description}"), "default_audio_language"
    if lang and not lang.startswith("ja"):
        # 명시적으로 다른 언어라고 밝힌 경우. 가나가 섞여 있어도 믿는다.
        return lang.split("-")[0], kana_ratio(f"{title} {description}"), "default_audio_language"

    ratio = kana_ratio(f"{title} {description}")
    return ("ja" if ratio >= min_ratio else "other"), ratio, "kana_ratio"
