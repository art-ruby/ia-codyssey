# -*- coding: utf-8 -*-
"""번역 — 제공자를 갈아탈 수 있게 한 곳에 모은다.

새 제공자를 붙이는 일 = 아래 함수 하나 + PROVIDERS 한 줄 + .env 에 키 한 줄.
부르는 쪽(collector 등)은 손대지 않는다.

같은 프로젝트군의 automaker 는 호출 코드가 66곳에 흩어져 있어 엔진 하나
바꾸는 것이 큰 공사였다. 그 전철을 밟지 않는다.

**번역은 편의 기능이다.** 키가 없거나 실패해도 프로그램 전체가 돌아야 한다.
이 파일의 공개 함수는 예외를 던지지 않는다 — 빈 값을 돌려준다.
"""
import json
import re
import urllib.error
import urllib.request

from . import config

# 마지막 실패 이유. 호출부가 사람에게 한 번만 알려주도록 여기 담아 둔다.
last_error = ""


# ──────────────────────────────────────────────────────────────────
# 제공자별 호출 — 여기에 함수를 더하면 새 제공자가 붙는다
# ──────────────────────────────────────────────────────────────────

def _post(url, payload, headers, timeout):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _call_openai(prompt, key, model, base_url, timeout):
    url = (base_url or "https://api.openai.com/v1") + "/chat/completions"
    data = _post(url, {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }, {"Authorization": f"Bearer {key}"}, timeout)
    return data["choices"][0]["message"]["content"]


def _call_gemini(prompt, key, model, base_url, timeout):
    base = base_url or "https://generativelanguage.googleapis.com/v1beta"
    url = f"{base}/models/{model}:generateContent?key={key}"
    data = _post(url, {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0},
    }, {}, timeout)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_claude(prompt, key, model, base_url, timeout):
    url = (base_url or "https://api.anthropic.com/v1") + "/messages"
    data = _post(url, {
        "model": model, "max_tokens": 4096, "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }, {"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout)
    return data["content"][0]["text"]


# 제공자 이름 → (호출 함수, .env 에서 찾을 키 이름)
PROVIDERS = {
    "openai": (_call_openai, "OPENAI_API_KEY"),
    "gemini": (_call_gemini, "GEMINI_API_KEY"),
    "claude": (_call_claude, "ANTHROPIC_API_KEY"),
}


# ──────────────────────────────────────────────────────────────────
# 공통 — 예외를 밖으로 내보내지 않는다
# ──────────────────────────────────────────────────────────────────

def available():
    """지금 설정으로 번역할 수 있는가. (가능여부, 이유) 를 돌려준다."""
    if not config.TRANSLATE_ENABLED:
        return False, "config.TRANSLATE_ENABLED 가 꺼져 있습니다"

    entry = PROVIDERS.get(config.TRANSLATE_PROVIDER)
    if not entry:
        return False, (f"모르는 제공자 '{config.TRANSLATE_PROVIDER}'. "
                       f"쓸 수 있는 것: {', '.join(PROVIDERS)}")

    _, env_name = entry
    if not config.api_key(env_name):
        return False, f".env 에 {env_name} 가 없습니다"
    return True, ""


def _ask(prompt):
    """제공자에게 묻는다. 실패하면 None 과 함께 last_error 를 채운다."""
    global last_error
    ok, why = available()
    if not ok:
        last_error = why
        return None

    fn, env_name = PROVIDERS[config.TRANSLATE_PROVIDER]
    try:
        return fn(prompt, config.api_key(env_name), config.TRANSLATE_MODEL,
                  config.TRANSLATE_BASE_URL, config.TRANSLATE_TIMEOUT)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        if e.code == 401:
            last_error = (f"키가 거부됐습니다 (401). .env 의 "
                          f"{env_name} 를 확인하세요.\n  {body}")
        elif e.code == 404 or "model" in body.lower():
            # 모델은 사라지거나 이름이 바뀐다. 어디를 고쳐야 하는지 알려준다.
            last_error = (f"모델 '{config.TRANSLATE_MODEL}' 을 쓸 수 없습니다.\n"
                          f"  src/config.py 의 TRANSLATE_MODEL 을 확인하세요.\n"
                          f"  {body}")
        elif e.code == 429:
            last_error = "요청 한도를 넘었습니다 (429). 잠시 뒤 다시 시도하세요."
        else:
            last_error = f"HTTP {e.code}: {body}"
    except urllib.error.URLError as e:
        last_error = f"네트워크 오류: {e.reason}"
    except (KeyError, IndexError, ValueError) as e:
        last_error = f"응답을 읽지 못했습니다 ({type(e).__name__}) — 형식이 바뀌었을 수 있습니다"
    except OSError as e:
        # 읽기 타임아웃(TimeoutError)은 URLError 로 감싸이지 않고 그대로 올라온다.
        # 이것 때문에 수집이 통째로 죽어 검색 2,400 units 를 날린 적이 있다.
        last_error = f"응답이 {config.TRANSLATE_TIMEOUT}초 안에 오지 않았습니다 ({e})"
    except Exception as e:                       # noqa: BLE001
        # 번역은 편의 기능이다. 어떤 이유로도 부르는 쪽을 죽이지 않는다.
        last_error = f"번역 중 예상 못한 오류 ({type(e).__name__}: {e})"
    return None


def _extract_json(text):
    """모델이 설명을 덧붙여도 JSON 만 뽑아낸다."""
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = text.find(opener), text.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(text[i:j + 1])
            except ValueError:
                continue
    return None


# ──────────────────────────────────────────────────────────────────
# A. 제목 → 한글 한 줄
# ──────────────────────────────────────────────────────────────────

_TITLE_PROMPT = """다음은 일본 유튜브 영상 제목이다. 각각을 한국어 한 줄로 옮겨라.

규칙
- 직역보다 무슨 내용인지 알 수 있게. 50자 이내
- 【ゆっくり解説】같은 대괄호 표시는 형식 표기이므로 «[해설]» 처럼 짧게 남긴다
- 고유명사는 한국에서 통용되는 표기로
- 설명을 덧붙이지 말고 JSON 배열만 출력한다

입력(번호 순서대로):
{items}

출력 형식(반드시 {n}개):
["번역1", "번역2", ...]"""


def translate_titles(titles):
    """제목 목록 → 한글 목록. 실패하면 같은 길이의 빈 문자열 목록.

    낱개로 부르지 않고 묶어 보낸다. 60번 부르면 분당 요청 한도에 걸린다.
    """
    titles = list(titles)
    if not titles:
        return []

    out = []
    size = max(1, config.TRANSLATE_BATCH)
    for i in range(0, len(titles), size):
        chunk = titles[i:i + size]
        items = "\n".join(f"{k + 1}. {t}" for k, t in enumerate(chunk))
        got = _extract_json(_ask(_TITLE_PROMPT.format(items=items, n=len(chunk))))

        if isinstance(got, list) and len(got) == len(chunk):
            out.extend(str(x)[:120] for x in got)
        else:
            # 개수가 안 맞으면 그 묶음은 통째로 포기한다. 어긋난 채로 붙이면
            # 엉뚱한 제목에 엉뚱한 번역이 달려 더 나쁘다.
            if isinstance(got, list):
                global last_error
                last_error = f"번역 개수가 안 맞습니다 ({len(got)} ≠ {len(chunk)})"
            out.extend([""] * len(chunk))
    return out


_TERM_PROMPT = """다음은 일본어 낱말이다. 각각의 뜻을 한국어로 짧게 적어라.

규칙
- **낱말의 뜻만.** 제목을 짓거나 설명을 덧붙이지 않는다
- 12자 이내. 한국어에 같은 한자어가 있으면 그것을 쓴다
- 뜻이 여럿이면 «/» 로 두 개까지
- JSON 배열만 출력한다

보기
  注文住宅 → "주문주택"      (X: "나만의 맞춤 주택 짓기 노하우")
  家づくり → "집짓기"
  シャドウ → "그림자/융의 개념"

입력(번호 순서대로):
{items}

출력 형식(반드시 {n}개):
["뜻1", "뜻2", ...]"""


def translate_terms(terms):
    """낱말 목록 → 뜻 목록. 실패하면 같은 길이의 빈 문자열 목록.

    `translate_titles` 로 낱말을 넣으면 안 된다. 그 프롬프트는 «제목» 을
    시키므로 「注文住宅」 에 「나만의 맞춤형 주문주택 짓기 노하우」 같은
    없는 제목을 지어낸다. 오류는 안 나지만 **읽는 사람이 낱말 뜻으로 믿는다.**
    """
    terms = list(terms)
    if not terms:
        return []
    items = "\n".join(f"{k + 1}. {t}" for k, t in enumerate(terms))
    got = _extract_json(_ask(_TERM_PROMPT.format(items=items, n=len(terms))))
    if isinstance(got, list) and len(got) == len(terms):
        return [str(x)[:30] for x in got]
    global last_error
    if isinstance(got, list):
        last_error = f"뜻 개수가 안 맞습니다 ({len(got)} ≠ {len(terms)})"
    return [""] * len(terms)


# ──────────────────────────────────────────────────────────────────
# B. 한글 뜻 → 일본어 검색어 후보  (다음 단계에서 화면에 붙인다)
# ──────────────────────────────────────────────────────────────────

_SEARCH_PROMPT = """일본 유튜브에서 검색할 말을 만든다.

주제(한국어): {korean}

규칙
- 사전적 번역이 아니라 **일본인이 실제로 검색창에 치는 말**이어야 한다
  나쁜 예: "지위 불안" → "地位不安" (아무도 안 친다)
  좋은 예: "他人と比べる", "承認欲求", "年収 比較", "SNS 疲れ"
- 2~4 단어의 짧은 말. 문장이 아니다
- 서로 다른 각도로 4개
- 각각에 한국어 뜻을 붙인다

JSON 배열만 출력:
[{{"term": "일본어 검색어", "meaning": "한국어 뜻"}}, ...]"""


def suggest_search_terms(korean):
    """한글 주제 → [{term, meaning}, ...]. 실패하면 빈 목록."""
    got = _extract_json(_ask(_SEARCH_PROMPT.format(korean=korean)))
    if not isinstance(got, list):
        return []
    return [{"term": str(d.get("term", "")).strip(),
             "meaning": str(d.get("meaning", "")).strip()}
            for d in got
            if isinstance(d, dict) and d.get("term")]


# ──────────────────────────────────────────────────────────────────
# C. 일반 질의 — 다른 모듈이 같은 제공자 계층을 쓰게 열어 둔다
# ──────────────────────────────────────────────────────────────────

def ask_json(prompt):
    """프롬프트를 보내고 JSON 을 받는다. 실패하면 None 과 `last_error`.

    이 파일 이름은 «translate» 지만 제공자 교체 지점이 여기 하나뿐이라
    channel_fit·comment_analyzer 도 이 문을 쓴다. 호출 코드를 여러 곳에
    흩으면 제공자를 갈아탈 때 다 찾아다녀야 한다.
    """
    return _extract_json(_ask(prompt))


def load_prompt(name, **kw):
    """`prompts/{name}.md` 를 읽어 자리표시자를 채운다.

    긴 프롬프트를 파이썬 코드에 박지 않는다 — 고칠 때 코드를 건드리게 되고,
    무엇이 바뀌었는지 diff 에서 읽기 어렵다. (지시서 §46)
    """
    path = config.ROOT / "prompts" / f"{name}.md"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8").format(**kw)
    except KeyError as e:
        global last_error
        last_error = f"프롬프트 {name}.md 에 채우지 못한 자리 {e}"
        return None
