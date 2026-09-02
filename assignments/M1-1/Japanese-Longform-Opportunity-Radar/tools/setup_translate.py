# -*- coding: utf-8 -*-
"""번역 제공자 붙이기 — 주소 하나만 주면 나머지를 알아서 맞춘다.

    python tools/setup_translate.py https://.../v1

하는 일
  1. /v1/models 로 실제 쓸 수 있는 모델을 물어본다  (이름을 추측하지 않는다)
  2. 값싸 보이는 텍스트 모델을 골라 실제로 한 줄 번역해 본다
  3. 되면 config.py 의 TRANSLATE_BASE_URL · TRANSLATE_MODEL 을 고쳐 준다

모델 이름은 사라지거나 바뀐다. 그래서 문서에 적힌 것을 믿지 않고
서버에 직접 묻는다.
"""
import io
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config, translate  # noqa: E402

CONFIG_PY = ROOT / "src" / "config.py"

# 텍스트 채팅에 못 쓰는 것들. 이름으로 거른다.
NOT_TEXT = re.compile(
    r"image|audio|tts|whisper|video|veo|embed|moderation|realtime|dall", re.I)
# 값싼 쪽을 먼저 시험한다. 제목 번역에 큰 모델을 쓸 이유가 없다.
CHEAP_FIRST = ["nano", "mini", "flash", "haiku", "small", "lite"]


def fetch_models(base, key):
    url = base.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        print(f"  HTTP {e.code} — {url}")
        print(f"  {body}")
        if e.code == 401:
            print("\n  키가 거부됐습니다. .env 의 OPENAI_API_KEY 를 확인하세요.")
        elif e.code == 404:
            print("\n  주소가 틀렸을 수 있습니다. 콘솔 문서 탭의 Base URL 을")
            print("  그대로 넣었는지 확인하세요. 보통 .../v1 로 끝납니다.")
        return None
    except urllib.error.URLError as e:
        print(f"  접속하지 못했습니다: {e.reason}")
        return None

    items = data.get("data") if isinstance(data, dict) else data
    if not isinstance(items, list):
        print(f"  응답 형식이 예상과 다릅니다: {str(data)[:200]}")
        return None
    return sorted(str(m.get("id", m)) for m in items)


def rank(name):
    """값싸 보이는 것을 앞으로."""
    for i, kw in enumerate(CHEAP_FIRST):
        if kw in name.lower():
            return i
    return len(CHEAP_FIRST)


def patch_config(base, model):
    text = CONFIG_PY.read_text(encoding="utf-8")
    for key, value in (("TRANSLATE_BASE_URL", base), ("TRANSLATE_MODEL", model)):
        pat = re.compile(rf'^({key}\s*=\s*)"[^"]*"', re.M)
        if not pat.search(text):
            print(f"  config.py 에서 {key} 를 찾지 못했습니다 — 직접 고치세요")
            return False
        text = pat.sub(lambda m: f'{m.group(1)}"{value}"', text, count=1)
    CONFIG_PY.write_text(text, encoding="utf-8")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("콘솔 → 문서 탭 → 코드 예제(Python) 의 URL 을 그대로 넣으세요.")
        print("  예: python tools/setup_translate.py https://xxx.example.com/v1")
        return 1

    base = sys.argv[1].rstrip("/")
    # /chat/completions 까지 붙여 넣는 경우가 흔하다. 잘라 준다.
    base = re.sub(r"/(chat/completions|messages|models)$", "", base)

    provider = config.TRANSLATE_PROVIDER
    _, env_name = translate.PROVIDERS[provider]
    key = config.api_key(env_name)
    if not key:
        print(f".env 에 {env_name} 가 없습니다.")
        return 1

    print(f"제공자 {provider} · 주소 {base}")
    print(f"키 {key[:10]}…\n")

    print("① 쓸 수 있는 모델 물어보는 중…")
    models = fetch_models(base, key)
    if not models:
        return 1

    text_models = sorted((m for m in models if not NOT_TEXT.search(m)), key=rank)
    print(f"  전체 {len(models)}개 · 텍스트로 쓸 만한 것 {len(text_models)}개")
    for m in text_models[:10]:
        print(f"    {m}")
    if not text_models:
        print("  텍스트 모델이 없습니다. 문서 탭의 모델 목록을 확인하세요.")
        return 1

    print("\n② 실제로 번역해 보는 중… (값싼 것부터)")
    original_base, original_model = config.TRANSLATE_BASE_URL, config.TRANSLATE_MODEL
    config.TRANSLATE_BASE_URL = base

    picked = None
    for m in text_models[:5]:
        config.TRANSLATE_MODEL = m
        got = translate.translate_titles(["【ゆっくり解説】老後のお金が足りない理由"])
        if got and got[0]:
            print(f"    {m}  →  {got[0]}")
            picked = m
            break
        print(f"    {m}  ×  {translate.last_error.splitlines()[0]}")

    config.TRANSLATE_BASE_URL, config.TRANSLATE_MODEL = original_base, original_model

    if not picked:
        print("\n  어느 모델로도 번역에 실패했습니다. 위 오류를 보세요.")
        return 1

    print(f"\n③ config.py 에 반영 중…")
    if patch_config(base, picked):
        print(f"  TRANSLATE_BASE_URL = \"{base}\"")
        print(f"  TRANSLATE_MODEL    = \"{picked}\"")
        print("\n끝났습니다. 이제 수집할 때 제목이 한글로 같이 저장됩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
