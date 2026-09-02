# -*- coding: utf-8 -*-
"""자막을 받아 «고르는 데 필요한 만큼» 만 남긴다.

    from src import subtitles
    d = subtitles.digest("DD3gDj8cKGo")
    d["head"]      앞 3분
    d["keywords"]  반복해서 나온 말
    d["tail"]      마지막 1분

전체를 넣지 않는 이유 — 20분물이 7,000자, 37분물이 13,000자다. 채팅창에
그대로 붙이면 읽는 쪽도 부담이고 정작 «이 소재를 할까 말까» 를 정하는 데는
필요 없다. 앞 3분에 세계관과 훅이, 마지막 1분에 결론과 다음 화 예고가 있다.
그 사이는 반복되는 낱말만 봐도 무엇을 다루는지 잡힌다. (prd F-3)

받은 자막은 파일로 남긴다. 같은 영상을 다시 열 때 또 내려받지 않기 위해서다.
자막은 변하지 않는다.
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from . import config

CACHE = config.DATA_RAW / "subs"

HEAD_SECONDS = 180        # 앞 3분
TAIL_SECONDS = 60         # 마지막 1분
KEYWORD_TOP = 12
FETCH_TIMEOUT = 120

# 조사·조동사처럼 뜻이 없는 조각. 반복 낱말에서 뺀다.
STOP = {
    "そう", "これ", "それ", "あれ", "ここ", "そこ", "この", "その", "あの",
    "です", "ます", "ました", "でしょ", "ですね", "ますね", "という", "って",
    "こと", "もの", "ため", "よう", "みたい", "ちょっと", "本当", "自分",
    "思い", "思う", "なん", "なる", "する", "した", "して", "ある", "いる",
    "わけ", "はず", "だけ", "まで", "から", "でも", "けど", "ない", "だと",
}


def _run(args):
    """yt-dlp 를 부른다. 실패해도 예외를 올리지 않는다."""
    try:
        p = subprocess.run(
            [sys.executable, "-m", "yt_dlp", *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=FETCH_TIMEOUT)
        return p.returncode, (p.stderr or "") + (p.stdout or "")
    except subprocess.TimeoutExpired:
        return -1, f"{FETCH_TIMEOUT}초 안에 끝나지 않았습니다"
    except Exception as e:                       # yt-dlp 자체가 없을 때
        return -1, str(e)


def fetch(video_id, force=False):
    """자막 원본(json3)을 받아 캐시에 넣고 경로를 돌려준다. 없으면 None."""
    CACHE.mkdir(parents=True, exist_ok=True)
    dst = CACHE / f"{video_id}.ja.json3"
    if dst.exists() and not force:
        return dst

    # 자동생성 자막만 쓴다. 사람이 단 자막은 일본어 롱폼에 거의 없다.
    code, log = _run([
        f"https://www.youtube.com/watch?v={video_id}",
        "--skip-download", "--write-auto-subs", "--sub-lang", "ja",
        "--sub-format", "json3", "--no-warnings",
        "-o", str(CACHE / "%(id)s.%(ext)s"),
    ])
    if dst.exists():
        return dst
    # 자막이 없는 영상은 흔하다. 오류가 아니라 «없음» 으로 다룬다.
    fetch.last_error = _why(log, code)
    return None


fetch.last_error = ""


def _why(log, code):
    """못 받은 이유를 사람 말로. «없다» 와 «지금 못 받는다» 를 가른다.

    둘을 뭉뜽그리면 자막이 있는 영상을 «자막 없음» 으로 적어 둔다.
    429 는 잠깐 쉬면 풀리므로 다시 부르면 된다 — 다르게 말해 줘야 한다.
    """
    low = log.lower()
    if "429" in log or "too many requests" in low:
        return "요청이 몰려 잠시 막혔습니다 (자막이 없는 것이 아닙니다). 조금 뒤 다시"
    if "sign in" in low or "bot" in low:
        return "유튜브가 사람 확인을 요구합니다. 조금 뒤 다시"
    if "unavailable" in low or "private" in low or "removed" in low:
        return "영상이 내려갔거나 비공개입니다"
    if "incomplete youtube id" in low or "not a valid url" in low:
        return "영상 ID 가 올바르지 않습니다"
    if "no subtitles" in low or "unable to download video subtitles" in low:
        return "이 영상에는 일본어 자막이 없습니다"
    if "no module named" in low:
        return "yt-dlp 가 설치되어 있지 않습니다 (pip install yt-dlp)"
    if code == -1:
        return log.strip()[:200] or "자막을 받지 못했습니다"
    return "이 영상에는 일본어 자막이 없습니다"


def retryable(reason):
    """다시 부르면 될 수도 있는 실패인가. 화면에서 «다시» 를 보일지 정한다."""
    return "다시" in (reason or "")


def _events(path):
    """(초, 문장) 목록. 자동자막의 겹쳐 쓰기를 걷어낸다."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []

    out, prev = [], ""
    for e in data.get("events", []):
        text = "".join(s.get("utf8", "") for s in e.get("segs", []))
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        # 자동자막은 앞 줄을 다시 쓰며 한 낱말씩 늘려 간다.
        # 앞 줄로 시작하는 줄은 «자라는 중» 이므로 앞 줄을 버리고 이것만 남긴다.
        if prev and text.startswith(prev):
            out.pop()
        elif prev and prev.startswith(text):
            continue
        out.append((e.get("tStartMs", 0) / 1000.0, text))
        prev = text
    return out


def _keywords(lines):
    """되풀이되는 말. 형태소 분석기 없이 한자·가타카나 덩어리를 센다.

    정확한 분석은 아니다. 「무엇에 대한 영상인가」만 알면 되므로 이 정도면
    충분하고, 사전을 깔 필요가 없다는 이점이 크다.
    """
    body = " ".join(t for _, t in lines)
    chunks = re.findall(r"[一-鿿]{2,}|[゠-ヿー]{3,}", body)
    counts = Counter(c for c in chunks if c not in STOP and len(c) <= 8)
    # 두 번 이하로 나온 말은 «되풀이» 가 아니다.
    return [(w, n) for w, n in counts.most_common(KEYWORD_TOP * 2) if n >= 3
            ][:KEYWORD_TOP]


def digest(video_id, force=False):
    """앞 3분 · 반복 낱말 · 마지막 1분.

    자막이 없으면 ok=False 로 돌려준다. 부르는 쪽은 그 칸만 «자막 없음» 으로
    두고 나머지는 그대로 낸다 — 자막이 없다고 소재가 못 쓸 것은 아니다.
    """
    path = fetch(video_id, force=force)
    if path is None:
        return {"ok": False, "why": fetch.last_error or "자막이 없습니다",
                "head": "", "keywords": [], "tail": "", "chars": 0}

    lines = _events(path)
    if not lines:
        return {"ok": False, "why": "자막 파일이 비어 있습니다",
                "head": "", "keywords": [], "tail": "", "chars": 0}

    end = lines[-1][0]
    head = "".join(t for s, t in lines if s <= HEAD_SECONDS)
    tail = "".join(t for s, t in lines if s >= end - TAIL_SECONDS)
    return {
        "ok": True, "why": "",
        "head": head,
        "keywords": _keywords(lines),
        "tail": tail,
        "chars": sum(len(t) for _, t in lines),
        "minutes": end / 60.0,
    }


def _clock(sec):
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


def digest_text(video_id, force=False):
    """LLM 에 넣을 자막 요약 한 덩어리. 최대 `TRANSCRIPT_DIGEST_MAX_CHARS`.

    raw 전체 자막을 넣지 않는다 — 20분물이 약 6,900자, 37분물이 13,000자다.
    (지시서 §37)

    `digest()` 는 앞 3분과 마지막 1분만 뽑아 **가운데가 통째로 안 보였다.**
    여기서는 사이를 몇 지점 찍어 «어떤 순서로 풀어 가는가» 를 남긴다.

    사실 검증은 여기서 하지 않는다. 자막은 원 영상의 주장일 뿐이라 그것을
    한 번 더 요약해도 참이 되지 않는다. 검증 목록은 대본 작성 프롬프트가
    [FACT CHECK] 로 내놓는다.
    """
    d = digest(video_id, force=force)
    if not d["ok"]:
        return d

    path = fetch(video_id)
    lines = _events(path) if path else []
    end = lines[-1][0] if lines else 0

    # 앞 3분과 마지막 1분을 뺀 «가운데» 를 고르게 4지점 찍는다.
    mid = [(s, t) for s, t in lines
           if HEAD_SECONDS < s < end - TAIL_SECONDS]
    picks = []
    if mid:
        step = max(1, len(mid) // 5)
        for i in range(step, len(mid), step):
            s, t = mid[i]
            picks.append((s, t))
            if len(picks) >= 4:
                break

    cap = config.TRANSCRIPT_DIGEST_MAX_CHARS
    # 앞·뒤·가운데에 예산을 나눠 준다. 앞이 가장 중요하다(훅과 세계관).
    head = d["head"][:int(cap * 0.40)]
    tail = d["tail"][:int(cap * 0.20)]
    kw = " · ".join(f"{w}({n})" for w, n in d["keywords"][:10])

    parts = [f"[앞 {HEAD_SECONDS // 60}분] {head}"]
    if picks:
        body = " / ".join(f"{_clock(s)} {t}" for s, t in picks)
        parts.append(f"[중간 흐름] {body[:int(cap * 0.25)]}")
    parts.append(f"[반복 낱말] {kw}")
    parts.append(f"[마지막 {TAIL_SECONDS}초] {tail}")

    text = "\n".join(parts)
    if len(text) > cap:
        text = text[:cap - 1] + "…"

    return {**d, "text": text, "digest_chars": len(text)}
