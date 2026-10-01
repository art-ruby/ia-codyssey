"""T01.03: Codyssey 프록시의 GPT 텍스트 호출을 한 번 검증한다.

기본 설정 파일은 Git에서 제외한 M1-2/.env.codyssey다. 서버용
M1-2/.env는 읽지 않으며, 주소를 검사해 다른 서비스로 키를 보내지 않는다.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path

from dotenv import dotenv_values
from openai import APIStatusError, OpenAI, OpenAIError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env.codyssey"
CODYSSEY_BASE_URL = "https://copa.codyssey.kr/v1"


def _settings(path: Path) -> dict[str, str]:
    if path.exists():
        # 한 파일의 값을 함께 사용해 서로 다른 서비스의 키·주소를 섞지 않는다.
        source = dotenv_values(path)
    elif path == DEFAULT_ENV_FILE:
        raise ValueError(f"설정 파일이 없습니다: {path}")
    else:
        raise ValueError(f"지정한 설정 파일이 없습니다: {path}")
    return {
        name: str(source.get(name) or "").strip()
        for name in ("OPENAI_API_KEY", "AI_PROVIDER_BASE_URL", "AI_PROVIDER_MODEL")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--list-models", action="store_true", help="GPT 모델 후보만 확인하고 텍스트 호출은 하지 않음")
    args = parser.parse_args()

    try:
        settings = _settings(args.env_file.expanduser().resolve())
        base_url = settings["AI_PROVIDER_BASE_URL"].rstrip("/")
        if base_url != CODYSSEY_BASE_URL:
            raise ValueError("AI_PROVIDER_BASE_URL은 Codyssey 프록시 주소여야 합니다")
        if not settings["OPENAI_API_KEY"]:
            raise ValueError("OPENAI_API_KEY가 비어 있습니다")
        model = settings["AI_PROVIDER_MODEL"]
        if not args.list_models and "gpt" not in model.lower():
            raise ValueError("AI_PROVIDER_MODEL에 실제 제공되는 GPT 모델명을 입력하세요")

        client = OpenAI(base_url=base_url, api_key=settings["OPENAI_API_KEY"], timeout=60, max_retries=0)
        sdk_version = importlib.metadata.version("openai")

        if args.list_models:
            candidates = sorted(
                item.id for item in client.models.list().data if "gpt" in item.id.lower()
            )
            print(json.dumps({"provider": "Codyssey", "sdk_version": sdk_version, "gpt_models": candidates}, ensure_ascii=False))
            return 0 if candidates else 1

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "연결 확인입니다. OK라고만 답하세요."}],
        )
        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("응답의 choices[0].message.content가 비어 있습니다")
        if choice.finish_reason != "stop":
            raise ValueError(f"응답이 정상 종료되지 않았습니다: {choice.finish_reason}")
        print(json.dumps({
            "provider": "Codyssey",
            "requested_model": model,
            "response_model": response.model,
            "sdk_version": sdk_version,
            "response_shape": "choices[0].message.content: nonempty text",
            "finish_reason": choice.finish_reason,
            "success": True,
        }, ensure_ascii=False))
        return 0
    except APIStatusError as exc:
        print(f"Codyssey HTTP 오류: {exc.status_code}", file=sys.stderr)
    except ValueError as exc:
        print(f"설정/응답 검증 실패: {exc}", file=sys.stderr)
    except OpenAIError as exc:
        # SDK의 예외 본문에는 제공자 응답이 들어갈 수 있어 오류 종류만 기록한다.
        print(f"Codyssey 검증 실패: {type(exc).__name__}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
