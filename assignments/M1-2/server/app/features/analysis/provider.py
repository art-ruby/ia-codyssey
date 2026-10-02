"""도구 실행을 허용하지 않는 Hermes 텍스트 호출 경계와 AI Adapter.

Hermes API 프로필에 도구가 켜져 있으면 호출 전에 중단해 자료 속 지시문이 파일 작업으로
이어지지 않게 한다. Provider 오류 본문과 원문은 로그에 남기지 않는다.

`AnalysisAdapter`는 PRD §12의 네 책임(분석·분류·중요도 제안·답변)을 갖는다. 분석은
Provider를 한 번만 부르고, 분류·중요도는 그 결과에서 꺼낸다. 형식·근거 검증에 실패해도
비용이 드는 호출을 자동으로 다시 하지 않는다(재시도는 사용자가 고른다, T04.02).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from openai import APIStatusError, APITimeoutError, OpenAI, OpenAIError, RateLimitError
from pydantic import ValidationError

from app.core.config import Settings
from app.features.analysis.prompts import build_messages
from app.features.analysis.schemas import (
    CONTENT_FIELDS, INPUT_FIELDS, KINDS, MIN_EVIDENCE_CHARS, AnalysisResult, ModelOutput, normalize_space,
)


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
        except RateLimitError as exc:
            raise ProviderError("rate_limited", exc.status_code) from exc
        except APIStatusError as exc:
            raise ProviderError("provider_http_error", exc.status_code) from exc
        except APITimeoutError as exc:
            raise ProviderError("timeout") from exc
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


class TextCompleter(Protocol):
    """Adapter가 쓰는 호출 경계. 실제로는 `HermesProvider`, 테스트에서는 가짜 응답이다."""

    def complete_text(self, messages: list[dict[str, str]]) -> TextResult: ...


def _parse_json(text: str) -> dict:
    """JSON 객체 하나만 받는다. 모델이 붙이는 코드 블록 표시 한 겹만 벗긴다."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else ""
        raw = raw.rsplit("```", 1)[0]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError("invalid_output") from exc
    if not isinstance(data, dict):
        raise ProviderError("invalid_output")
    return data


class AnalysisAdapter:
    def __init__(self, completer: TextCompleter) -> None:
        self.completer = completer

    def analyze_material(self, material: dict, projects: list[dict]) -> AnalysisResult:
        """자료 하나를 분석한다. `projects`는 활성 프로젝트(`id`, `name`)만 넘긴다."""
        if material.get("ai_excluded"):
            raise ProviderError("ai_excluded")
        if not any(material.get(name) for name in CONTENT_FIELDS):
            raise ProviderError("no_content")  # URL만 있는 자료: 본문을 읽은 것처럼 만들지 않는다
        sent = {name: material[name] for name in INPUT_FIELDS if material.get(name)}
        payload = dict(sent, url=material["url"]) if material.get("url") else dict(sent)
        offered = [{"id": p["id"], "name": p["name"]} for p in projects]

        reply = self.completer.complete_text(build_messages(payload, offered))
        try:
            out = ModelOutput.model_validate(_parse_json(reply.text))
        except ValidationError as exc:
            raise ProviderError("invalid_output") from exc

        source = normalize_space(" ".join(sent.values()))
        evidence = [q for q in out.evidence
                    if len(normalize_space(q)) >= MIN_EVIDENCE_CHARS and normalize_space(q) in source]
        if not evidence:
            raise ProviderError("ungrounded_output")

        notes = list(out.uncertainties)
        project_id = out.primary_project_id
        if project_id is not None and project_id not in {p["id"] for p in offered}:
            project_id = None
            notes.append("제안한 프로젝트가 현재 프로젝트 목록에 없어 비워 두었습니다.")
        kind = out.kind
        if kind is not None and kind not in KINDS:
            kind = None
            notes.append("제안한 종류가 정해진 목록에 없어 비워 두었습니다.")

        return AnalysisResult(
            ai_title=out.title,
            ai_summary=out.summary,
            ai_importance=out.importance,
            ai_importance_reason=out.importance_reason,
            ai_primary_project_id=project_id,
            ai_kind=kind,
            ai_keywords=out.keywords,
            ai_uncertainties=notes,
            ai_recommended_action=out.recommended_action or None,
            ai_evidence=evidence,
            ai_checked_scope={
                "fields": list(sent),
                "chars": sum(len(value) for value in sent.values()),
                "url_fetched": False,
            },
            model=reply.model,
            total_tokens=reply.total_tokens,
        )

    def classify_material(self, result: AnalysisResult) -> dict:
        return {"ai_kind": result.ai_kind, "ai_primary_project_id": result.ai_primary_project_id}

    def suggest_importance(self, result: AnalysisResult) -> dict:
        return {"ai_importance": result.ai_importance, "ai_importance_reason": result.ai_importance_reason}

    def answer_question(self, messages: list[dict[str, str]]) -> TextResult:
        """채팅 답변 호출. 문맥 구성·근거 검증은 채팅 서비스(T07.02)가 맡는다."""
        return self.completer.complete_text(messages)
