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
    CONTENT_FIELDS, INPUT_FIELDS, KINDS, MIN_EVIDENCE_CHARS, MIN_SUMMARY_OVERLAP, UNVERIFIED_FIELDS,
    AnalysisResult, ModelOutput, normalize_space, numbers, overlap_ratio, sentences, word_chars,
)


# Provider에 요청을 보내기 전에 멈춘 오류. 이 밖의 오류는 요청이 나갔다고 보고 사용량에 센다(T04.03).
# 연결 오류는 도달 여부가 불확실하므로 보낸 쪽으로 센다(한도를 넘지 않는 쪽).
PRE_SEND_KINDS = frozenset({
    "invalid_hermes_url", "insecure_hermes_url", "missing_hermes_route",
    "hermes_toolset_check_failed", "hermes_tools_enabled", "ai_excluded", "no_content",
})


class ProviderError(RuntimeError):
    """사용자에게 전달 가능한 오류 종류만 담는다."""

    def __init__(self, kind: str, status_code: int | None = None, total_tokens: int | None = None) -> None:
        self.kind = kind
        self.status_code = status_code
        # 응답은 받았지만 검증에 실패한 경우의 토큰 사용량. 사용량 정산(T04.03)이 버리지 않게 담아 둔다.
        self.total_tokens = total_tokens
        super().__init__(kind)

    @property
    def request_sent(self) -> bool:
        return self.kind not in PRE_SEND_KINDS


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
        if choice is not None and choice.finish_reason == "length":
            raise ProviderError("output_truncated")  # 출력 한도(AI_MAX_OUTPUT_TOKENS)에 걸렸다
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
        offered = [{"id": p["id"], "name": p["name"]} for p in projects if p.get("active", True)]

        reply = self.completer.complete_text(build_messages(payload, offered))
        try:
            return self._validate(reply, sent, offered)
        except ProviderError as exc:
            exc.total_tokens = reply.total_tokens  # 응답은 도착했으므로 검증 실패여도 토큰은 쓰였다
            raise

    def _validate(self, reply: TextResult, sent: dict, offered: list[dict]) -> AnalysisResult:
        """응답을 형식·근거 순서로 검증해 결과로 바꾼다. 실패하면 ProviderError."""
        try:
            out = ModelOutput.model_validate(_parse_json(reply.text))
        except ValidationError as exc:
            raise ProviderError("invalid_output") from exc

        # 인용은 한 필드 안에 그대로 있어야 한다(필드 경계를 넘는 인용은 지어낸 문장일 수 있다).
        # 저장 이유·메모는 사용자가 쓴 말이므로, 자료 내용(제목·설명·본문) 인용이 하나 이상 있어야 한다.
        normalized = {name: normalize_space(value) for name, value in sent.items()}

        def found_in(quote: str) -> set[str]:
            q = normalize_space(quote)
            if len(word_chars(q)) < MIN_EVIDENCE_CHARS:
                return set()
            return {name for name, value in normalized.items() if q in value}

        evidence = [q for q in out.evidence if found_in(q)]
        if not any(found_in(q) & set(CONTENT_FIELDS) for q in evidence):
            raise ProviderError("ungrounded_output")
        # 인용이 맞아도 요약에 입력과 무관한 문장이 섞일 수 있다. 문장마다 입력과의 겹침을 보고,
        # 모든 문장 필드에서 입력에 없는 숫자(날짜·금액 등)를 거부한다. 사실 검증은 아니다.
        source = " ".join(sent.values())
        if any(overlap_ratio(s, source) < MIN_SUMMARY_OVERLAP for s in sentences(out.summary)):
            raise ProviderError("ungrounded_output")
        stated = " ".join([out.title, out.summary, out.importance_reason, out.recommended_action,
                           *out.keywords, *out.uncertainties])
        if not numbers(stated) <= numbers(source):
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
            ai_grounding={
                "evidence": "quote_match",
                "summary": "lexical_overlap",
                "numbers": "must_appear_in_input",
                "unverified": list(UNVERIFIED_FIELDS),
                "fact_checked": False,
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
