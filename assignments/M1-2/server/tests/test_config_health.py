import pytest
from fastapi.testclient import TestClient

from app.core.config import ConfigError, load_settings
from app.main import create_app

FULL = {
    "OPENAI_API_KEY": "secret-ai-key",
    "AI_PROVIDER_BASE_URL": "https://proxy.example/v1",
    "AI_PROVIDER_MODEL": "gpt-test",
    "AI_PROVIDER_ROUTE": "openai-codex",
    "FIREBASE_SERVICE_ACCOUNT_JSON": "secret-service-account",
    "OWNER_UID": "owner-1",
}


def test_server_starts_without_keys_and_reports_missing_groups():
    client = TestClient(create_app(load_settings({})))

    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["config"] == {"ai": "missing", "firebase": "missing"}
    assert "OPENAI_API_KEY" in body["missing"]["ai"]


def test_health_never_exposes_values():
    client = TestClient(create_app(load_settings(FULL)))

    text = client.get("/health").text

    assert '"ai":"ready"' in text and '"firebase":"ready"' in text
    for value in FULL.values():
        assert value not in text


def test_require_distinguishes_missing_config_by_name_only():
    settings = load_settings({**FULL, "AI_PROVIDER_MODEL": ""})

    with pytest.raises(ConfigError) as err:
        settings.require("ai")

    assert "AI_PROVIDER_MODEL" in str(err.value)
    settings.require("firebase")  # 채워진 묶음은 통과


@pytest.mark.parametrize("raw", ["abc", "0", "-5"])
def test_invalid_limits_are_rejected_without_echoing_value(raw):
    with pytest.raises(ConfigError) as err:
        load_settings({"AI_DAILY_REQUEST_LIMIT": raw})

    assert "AI_DAILY_REQUEST_LIMIT" in str(err.value)
    assert raw not in str(err.value)


def test_defaults_and_origins():
    settings = load_settings({"ALLOWED_ORIGINS": " https://a.example , ,https://b.example"})

    assert settings.allowed_origins == ("https://a.example", "https://b.example")
    assert (settings.ai_daily_request_limit, settings.ai_max_output_tokens, settings.ai_timeout_seconds) == (50, 1500, 60)
