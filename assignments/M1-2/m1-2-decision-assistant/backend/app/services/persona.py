"""AutoMaker 채널 페르소나 초안 — AutoMaker 의 프롬프트를 DA 의 모델 키로 돌린다.

AutoMaker 는 RADAR 초안 채널의 페르소나를 «사람이 승인하기 전엔» 채우지 않는다
(radar_intake.approve_draft: "User approval is the only promotion from evidence to identity").
승인 전 단계인 초안 생성은 AutoMaker 안에서 AI 호출인데, 그쪽에 키가 없다.

여기서는 키를 AutoMaker 로 옮기지 않는다. 대신
  ① AutoMaker `draft-input` 이 주는 **AutoMaker 자신의 프롬프트·근거** 를 받아
  ② DA 에 이미 설정된 모델로 JSON 초안을 만들고
  ③ AutoMaker `save-draft` 에 넣는다 — 검토·승인은 AutoMaker 의 관문 그대로.
프롬프트를 DA 가 바꾸지 않는다. 바꾸면 AutoMaker 가 정한 «근거≠정체성» 규칙이 흐려진다.
"""
from __future__ import annotations

import json
from typing import Any

from ..config import Settings

REQUIRED_ART = ("name", "description", "prompt")


def parse_draft(text: str) -> dict[str, Any]:
    """AutoMaker radar_intake_api.py:57 과 같은 방식으로 모델 출력을 JSON 으로 푼다."""
    body = (text or "").strip().removeprefix("```json").removesuffix("```").strip()
    draft = json.loads(body)
    if not isinstance(draft, dict) or not isinstance(draft.get("persona"), str) or not draft["persona"].strip():
        raise ValueError("persona 가 비어 있습니다")
    art = draft.get("art_direction")
    if not isinstance(art, dict) or not all(isinstance(art.get(k), str) and art[k].strip() for k in REQUIRED_ART):
        raise ValueError("art_direction 에 name/description/prompt 가 모두 있어야 합니다")
    return {"persona": draft["persona"].strip(), "art_direction": {k: art[k].strip() for k in REQUIRED_ART}}


def generate_draft(prompt: str, settings: Settings) -> tuple[dict[str, Any], str]:
    """(초안, 모델명). 키가 없으면 지어내지 않고 예외."""
    if not settings.openai_enabled:
        raise RuntimeError("OPENAI_API_KEY 가 없어 페르소나 초안을 만들 수 없습니다.")
    from openai import OpenAI

    client = (
        OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        if settings.openai_base_url
        else OpenAI(api_key=settings.openai_api_key)
    )
    # temperature 는 넣지 않는다 — chat.py 와 같은 이유(게이트웨이 뒤 reasoning 모델이 거부).
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max(settings.openai_max_tokens, 1500),
    )
    text = (completion.choices[0].message.content or "").strip()
    return parse_draft(text), settings.openai_model
