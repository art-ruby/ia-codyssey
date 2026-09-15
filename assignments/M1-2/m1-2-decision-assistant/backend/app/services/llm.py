"""DA 의 모델 호출 한 곳. JSON 을 요구하고, 실패는 예외로 올린다(지어내지 않는다)."""
from __future__ import annotations

import json
from typing import Any

from ..config import Settings


def _client(settings: Settings):
    from openai import OpenAI

    return (
        OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        if settings.openai_base_url
        else OpenAI(api_key=settings.openai_api_key)
    )


def parse_json(text: str) -> Any:
    body = (text or "").strip()
    if body.startswith("```"):
        body = body.split("\n", 1)[1] if "\n" in body else body
        body = body.rsplit("```", 1)[0]
    return json.loads(body.strip())


def ask_json(prompt: str, settings: Settings, *, max_tokens: int = 16000) -> tuple[Any, str]:
    """(파싱된 JSON, 모델명). 키가 없으면 RuntimeError."""
    if not settings.openai_enabled:
        raise RuntimeError("OPENAI_API_KEY 가 없어 AI 해석을 만들 수 없습니다.")
    # reasoning 계열(gpt-5-mini 등)은 생각에 토큰을 먼저 쓴다. 상한이 작으면 finish_reason=length 로
    # 본문이 비어 온다(실측: 2,500 에서 content ""). 그래서 JSON 호출은 넉넉히 잡는다.
    completion = _client(settings).chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max(settings.openai_max_tokens, max_tokens),
    )
    choice = completion.choices[0]
    text = (choice.message.content or "").strip()
    if not text:
        raise RuntimeError(f"모델이 본문 없이 끝남 (finish_reason={choice.finish_reason}) — max_tokens 를 늘리거나 프롬프트를 줄이세요")
    return parse_json(text), settings.openai_model
