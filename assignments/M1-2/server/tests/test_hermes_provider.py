"""Hermes 경계가 도구 사용과 실패 응답을 거부하는지 확인한다."""

from __future__ import annotations

import io
import json
from types import SimpleNamespace

import pytest

from app.core.config import load_settings
from app.features.analysis import provider as module


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def make_provider(monkeypatch, *, finish_reason="stop"):
    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    finish_reason=finish_reason,
                    message=SimpleNamespace(content="연결됨"),
                )],
                model="gpt-5.5",
                usage=SimpleNamespace(total_tokens=12),
            )

    monkeypatch.setattr(module, "OpenAI", lambda **_kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    ))
    settings = load_settings({
        "OPENAI_API_KEY": "test-key",
        "AI_PROVIDER_BASE_URL": "http://127.0.0.1:8642/v1",
        "AI_PROVIDER_MODEL": "gpt-5.5",
        "AI_PROVIDER_ROUTE": "openai-codex",
    })
    return module.HermesProvider(settings), calls


def test_hermes_requires_disabled_tools_and_explicit_route(monkeypatch):
    provider, calls = make_provider(monkeypatch)
    monkeypatch.setattr(module, "urlopen", lambda *_args, **_kwargs: FakeResponse(
        json.dumps({"data": [{"name": "terminal", "enabled": False}]}).encode()
    ))
    result = provider.complete_text([{"role": "user", "content": "test"}])
    assert result.text == "연결됨"
    assert calls[0]["extra_body"] == {"provider": "openai-codex"}
    assert calls[0]["model"] == "gpt-5.5"


def test_hermes_rejects_enabled_tools_before_sending_text(monkeypatch):
    provider, calls = make_provider(monkeypatch)
    monkeypatch.setattr(module, "urlopen", lambda *_args, **_kwargs: FakeResponse(
        json.dumps({"data": [{"name": "terminal", "enabled": True}]}).encode()
    ))
    with pytest.raises(module.ProviderError, match="hermes_tools_enabled"):
        provider.complete_text([{"role": "user", "content": "test"}])
    assert calls == []


def test_hermes_rejects_http_200_error_finish(monkeypatch):
    provider, _calls = make_provider(monkeypatch, finish_reason="error")
    monkeypatch.setattr(module, "urlopen", lambda *_args, **_kwargs: FakeResponse(
        json.dumps({"data": [{"name": "terminal", "enabled": False}]}).encode()
    ))
    with pytest.raises(module.ProviderError, match="provider_incomplete_response"):
        provider.complete_text([{"role": "user", "content": "test"}])


def test_hermes_rejects_unverifiable_toolsets(monkeypatch):
    provider, calls = make_provider(monkeypatch)
    monkeypatch.setattr(module, "urlopen", lambda *_args, **_kwargs: FakeResponse(b'{"data": []}'))
    with pytest.raises(module.ProviderError, match="hermes_toolset_check_failed"):
        provider.complete_text([{"role": "user", "content": "test"}])
    assert calls == []
