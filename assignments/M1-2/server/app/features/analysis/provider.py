"""도구 실행을 허용하지 않는 Hermes 텍스트 호출 경계.

분석 및 채팅 서비스가 준비되면 이 경계를 사용한다. Hermes API 프로필에
도구가 켜져 있으면 호출 전에 중단해 자료 속 지시문이 파일 작업으로
이어지지 않게 한다. Provider 오류 본문과 원문은 로그에 남기지 않는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from openai import APIStatusError, OpenAI, OpenAIError

from app.core.config import Settings


class ProviderError(RuntimeError):
    """사용자에게 전달 가능한 오류 종류만 담는다."""

    def __init__(self, kind: str, status_code: int | None = None) -> None:
        self.kind = kind
        self.status_code = status_code
        super().__init__(kind)


@dataclass(frozen=True)
class TextResult:
    text: str
    model: str
    total_tokens: int | None


class HermesProvider:
    def __init__(self, settings: Settings) -> None:
        settings.require("ai")
        base_url = settings.get("AI_PROVIDER_BASE_URL").rstrip("/")
        parsed = urlparse(base_url)
        if not base_url.endswith("/v1") or parsed.scheme not in {"http", "https"}:
            raise ProviderError("invalid_hermes_url")
        if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ProviderError("insecure_hermes_url")
        self.route = settings.get("AI_PROVIDER_ROUTE")
        if not self.route:
            raise ProviderError("missing_hermes_route")
        self.model = settings.get("AI_PROVIDER_MODEL")
        self.base_url = base_url
        self.api_key = settings.get("OPENAI_API_KEY")
        self.timeout = settings.ai_timeout_seconds
        self.max_output_tokens = settings.ai_max_output_tokens
        self.client = OpenAI(
            base_url=base_url,
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=0,
        )

    def _require_tool_free_profile(self) -> None:
        request = Request(
            f"{self.base_url}/toolsets",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        try:
            with urlopen(request, timeout=min(self.timeout, 10)) as response:
                payload = json.load(response)
        except Exception as exc:
            raise ProviderError("hermes_toolset_check_failed") from exc
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
            raise ProviderError("hermes_toolset_check_failed")
        if any(row.get("enabled") is not False for row in rows):
            raise ProviderError("hermes_tools_enabled")

    def complete_text(self, messages: list[dict[str, str]]) -> TextResult:
        self._require_tool_free_profile()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=self.max_output_tokens,
                extra_body={"provider": self.route},
            )
        except APIStatusError as exc:
            raise ProviderError("provider_http_error", exc.status_code) from exc
        except OpenAIError as exc:
            raise ProviderError("provider_connection_error") from exc
        choice = response.choices[0] if response.choices else None
        if choice is None or choice.finish_reason != "stop":
            raise ProviderError("provider_incomplete_response")
        content = choice.message.content
        if not isinstance(content, str) or not content.strip():
            raise ProviderError("provider_empty_response")
        return TextResult(
            text=content,
            model=response.model,
            total_tokens=response.usage.total_tokens if response.usage else None,
        )
