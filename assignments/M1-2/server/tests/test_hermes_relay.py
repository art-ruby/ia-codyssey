"""Hermes relay tests use synthetic credentials and a mocked upstream."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import ConfigError, load_settings
from app.hermes_relay import create_relay_app


def relay_settings(**overrides):
    values = {
        "OPENAI_API_KEY": "hermes-test-key",
        "HERMES_RELAY_TOKEN": "relay-test-token",
    }
    values.update(overrides)
    return load_settings(values)


def test_missing_relay_credentials_fail_closed():
    with pytest.raises(ConfigError):
        create_relay_app(relay_settings(HERMES_RELAY_TOKEN=""))

    with pytest.raises(ConfigError):
        create_relay_app(relay_settings(OPENAI_API_KEY=""))

    with pytest.raises(ConfigError):
        create_relay_app(relay_settings(HERMES_RELAY_TOKEN="hermes-test-key"))


def test_relay_token_is_optional_for_normal_settings():
    settings = load_settings({
        "OPENAI_API_KEY": "hermes-test-key",
        "AI_PROVIDER_BASE_URL": "http://127.0.0.1:8642/v1",
        "AI_PROVIDER_MODEL": "gpt-test",
        "AI_PROVIDER_ROUTE": "openai-codex",
    })

    assert settings.get("HERMES_RELAY_TOKEN") == ""
    settings.require("ai")


def test_valid_bearer_token_is_replaced_with_local_hermes_key():
    calls: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"data": [{"name": "terminal", "enabled": False}]})

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_relay_app(relay_settings(), upstream_client=upstream_client)
    try:
        with TestClient(app) as client:
            response = client.get("/v1/toolsets", headers={"Authorization": "Bearer relay-test-token"})

        assert response.status_code == 200
        assert response.json()["data"][0]["enabled"] is False
        assert len(calls) == 1
        assert str(calls[0].url) == "http://127.0.0.1:8642/v1/toolsets"
        assert calls[0].headers["authorization"] == "Bearer hermes-test-key"
        assert "relay-test-token" not in calls[0].headers["authorization"]
    finally:
        import asyncio

        asyncio.run(upstream_client.aclose())


@pytest.mark.parametrize("authorization", [None, "Bearer wrong-token", "Basic relay-test-token"])
def test_missing_or_wrong_token_does_not_call_upstream(authorization):
    calls: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_relay_app(relay_settings(), upstream_client=upstream_client)
    headers = {} if authorization is None else {"Authorization": authorization}
    try:
        with TestClient(app) as client:
            response = client.get("/v1/toolsets", headers=headers)
        assert response.status_code == 401
        assert response.json() == {"detail": "인증이 필요합니다"}
        assert calls == []
    finally:
        import asyncio

        asyncio.run(upstream_client.aclose())


@pytest.mark.parametrize(
    ("method", "path", "expected_status"),
    [
        ("GET", "/v1/models", 404),
        ("GET", "/unknown", 404),
        ("PUT", "/v1/toolsets", 405),
        ("GET", "/v1/toolsets?debug=1", 404),
    ],
)
def test_unlisted_operation_is_rejected_before_upstream(method, path, expected_status):
    calls: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_relay_app(relay_settings(), upstream_client=upstream_client)
    try:
        with TestClient(app) as client:
            response = client.request(
                method, path, content=b"{}",
                headers={"Authorization": "Bearer relay-test-token", "Content-Type": "application/json"},
            )
        assert response.status_code == expected_status
        assert calls == []
    finally:
        import asyncio

        asyncio.run(upstream_client.aclose())


def test_chat_completion_forwards_json_but_not_caller_credentials():
    calls: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "응답"}}]})

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_relay_app(relay_settings(), upstream_client=upstream_client)
    body = b'{"model":"gpt-test","messages":[{"role":"user","content":"hello"}]}'
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions", content=body,
                headers={
                    "Authorization": "Bearer relay-test-token",
                    "Content-Type": "application/json",
                    "Connection": "close",
                    "X-Private-Caller-Header": "must-not-forward",
                },
            )

        assert response.status_code == 200
        assert len(calls) == 1
        assert calls[0].content == body
        assert calls[0].headers["authorization"] == "Bearer hermes-test-key"
        assert "x-private-caller-header" not in calls[0].headers
        assert calls[0].headers.get("connection") != "close"
    finally:
        import asyncio

        asyncio.run(upstream_client.aclose())


def test_oversized_request_is_rejected_before_upstream():
    calls: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_relay_app(relay_settings(), upstream_client=upstream_client)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions", content=b"x" * (1024 * 1024 + 1),
                headers={
                    "Authorization": "Bearer relay-test-token",
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 413
        assert calls == []
    finally:
        import asyncio

        asyncio.run(upstream_client.aclose())


@pytest.mark.parametrize(
    ("body", "content_type", "expected_status"),
    [
        (b"{\"x\":1}", "text/plain", 415),
        (b"{\"x\":1}", "application/jsonp", 415),
        (b"", "application/json", 400),
    ],
)
def test_chat_rejects_empty_or_non_json_body(body, content_type, expected_status):
    calls: list[httpx.Request] = []

    async def upstream(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_relay_app(relay_settings(), upstream_client=upstream_client)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions", content=body,
                headers={
                    "Authorization": "Bearer relay-test-token",
                    "Content-Type": content_type,
                },
            )
        assert response.status_code == expected_status
        assert calls == []
    finally:
        import asyncio

        asyncio.run(upstream_client.aclose())


@pytest.mark.parametrize(
    ("upstream_error", "expected_status"),
    [
        (httpx.ReadTimeout, 504),
        (httpx.ConnectError, 502),
    ],
)
def test_upstream_failure_returns_generic_response_without_exception_text(
    upstream_error, expected_status, caplog,
):
    async def upstream(request: httpx.Request) -> httpx.Response:
        raise upstream_error("secret diagnostic detail", request=request)

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    app = create_relay_app(relay_settings(), upstream_client=upstream_client)
    try:
        with TestClient(app) as client:
            response = client.get("/v1/toolsets", headers={"Authorization": "Bearer relay-test-token"})
        assert response.status_code == expected_status
        assert "secret diagnostic detail" not in response.text
        assert "hermes-test-key" not in response.text
        assert "secret diagnostic detail" not in caplog.text
        assert "relay-test-token" not in caplog.text
    finally:
        import asyncio

        asyncio.run(upstream_client.aclose())


def test_relay_launcher_binds_loopback_without_access_logging(monkeypatch):
    from scripts import run_hermes_relay

    observed = {}
    monkeypatch.setattr(run_hermes_relay, "load_settings", lambda: object())
    monkeypatch.setattr(run_hermes_relay, "create_relay_app", lambda settings: "relay-app")

    def fake_run(app, **kwargs):
        observed["app"] = app
        observed.update(kwargs)

    monkeypatch.setattr(run_hermes_relay.uvicorn, "run", fake_run)
    run_hermes_relay.main()

    assert observed == {
        "app": "relay-app",
        "host": "127.0.0.1",
        "port": 8766,
        "log_level": "warning",
        "access_log": False,
    }
