"""T08.02 배포 설정: 허용 Origin 검증과 CORS 동작, render.yaml·vercel.json·.env.example의 일관성.

실제 배포·네트워크 호출은 하지 않는다. 배포 결과(HTTPS 웹·Swagger·잘못된 Origin)는 docs/verification.md에 따로 기록한다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import ConfigError, load_settings
from app.main import create_app

ROOT = Path(__file__).parents[2]
WEB = "https://ai-secretary.vercel.app"
EVIL = "https://evil.example"


def client(origins=WEB):
    settings = load_settings({"OWNER_UID": "o", "ALLOWED_ORIGINS": origins})
    return TestClient(create_app(settings, verify_token=lambda t: {"uid": "o"}))


def preflight(c, origin):
    return c.options("/api/me", headers={"Origin": origin, "Access-Control-Request-Method": "GET",
                                          "Access-Control-Request-Headers": "authorization,x-data-mode"})


# ── 허용 Origin 형식 ──────────────────────────────────────────────

@pytest.mark.parametrize("origin", [
    "*", "https://*.vercel.app", f"{WEB}/", f"{WEB}/app", "http://ai-secretary.vercel.app", "ai-secretary.vercel.app",
    "https://", "ftp://x.example", "https://a b.example", "null",
])
def test_unsafe_or_malformed_origins_are_rejected_at_startup(origin):
    with pytest.raises(ConfigError) as error:
        load_settings({"ALLOWED_ORIGINS": f"https://ok.example,{origin}"})
    assert "ALLOWED_ORIGINS" in str(error.value)


@pytest.mark.parametrize("origin", [WEB, "https://x.example:8443", "http://localhost:5500", "http://127.0.0.1:5511",
                                    "http://[::1]:5500"])
def test_exact_https_and_local_http_origins_are_accepted(origin):
    assert load_settings({"ALLOWED_ORIGINS": origin}).allowed_origins == (origin,)


def test_empty_origins_are_allowed_and_mean_no_browser_origin():
    assert load_settings({"ALLOWED_ORIGINS": ""}).allowed_origins == ()


# ── CORS 동작 ─────────────────────────────────────────────────────

def test_allowed_origin_preflight_and_response_headers():
    c = client()
    res = preflight(c, WEB)
    assert res.status_code == 200 and res.headers["access-control-allow-origin"] == WEB
    assert "authorization" in res.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in res.headers  # 쿠키가 아니라 Bearer 토큰을 쓴다
    assert c.get("/health", headers={"Origin": WEB}).headers["access-control-allow-origin"] == WEB


@pytest.mark.parametrize("origin", [EVIL, "https://ai-secretary.vercel.app.evil.example", "http://ai-secretary.vercel.app",
                                    "https://AI-SECRETARY.vercel.app.", "null"])
def test_other_origins_get_no_cors_permission(origin):
    c = client()
    res = preflight(c, origin)
    assert res.status_code == 400 and "access-control-allow-origin" not in res.headers
    assert "access-control-allow-origin" not in c.get("/health", headers={"Origin": origin}).headers


def test_without_configured_origins_no_origin_is_allowed():
    c = client("")
    assert "access-control-allow-origin" not in c.get("/health", headers={"Origin": WEB}).headers
    assert "access-control-allow-origin" not in preflight(c, WEB).headers


def test_cors_does_not_replace_authentication():
    # 허용 Origin이어도 로그인 없이는 데이터에 접근할 수 없다.
    assert client().get("/api/materials", headers={"Origin": WEB, "X-Data-Mode": "personal"}).status_code == 401


# ── 배포 파일 ─────────────────────────────────────────────────────

def env_example_names() -> set[str]:
    return set(re.findall(r"^([A-Z][A-Z0-9_]*)=", (ROOT / ".env.example").read_text(encoding="utf-8"), re.M))


def render_text() -> str:
    return (ROOT / "render.yaml").read_text(encoding="utf-8")


def render_env_blocks() -> dict[str, str]:
    """render.yaml의 envVars 항목을 {key: 그 항목 텍스트}로(PyYAML 없이, 단순 블록 형식만 지원)."""
    blocks = re.split(r"\n\s*- key: ", "\n" + render_text().split("envVars:", 1)[1])[1:]
    return {block.split("\n", 1)[0].strip(): block for block in blocks}


def test_render_blueprint_points_at_server_folder_with_health_check_and_port():
    text = render_text()
    assert re.search(r"^\s*rootDir:\s*assignments/M1-2/server\s*$", text, re.M)
    assert re.search(r"^\s*healthCheckPath:\s*/health\s*$", text, re.M)
    assert "pip install -r requirements.txt" in text
    assert re.search(r"uvicorn app\.main:app\b.*--host 0\.0\.0\.0.*--port \$PORT", text)
    assert re.search(r"^\s*runtime:\s*python\s*$", text, re.M)


def test_render_secrets_are_never_written_in_the_file():
    blocks = render_env_blocks()
    secrets = {"OPENAI_API_KEY", "FIREBASE_SERVICE_ACCOUNT_JSON", "OWNER_UID", "AI_PROVIDER_BASE_URL", "ALLOWED_ORIGINS",
               "TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_CHAT_ID", "TELEGRAM_WEBHOOK_SECRET"}
    assert secrets <= set(blocks)
    for name in secrets:
        assert re.search(r"sync:\s*false", blocks[name]), f"{name}은 대시보드에서 직접 입력(sync: false)해야 한다"
        assert not re.search(r"\bvalue:", blocks[name]), f"{name}에 값이 적혀 있다"


def test_render_env_names_are_known_to_the_server_and_documented():
    from app.core.config import OPTIONAL, REQUIRED

    server_names = {n for names in REQUIRED.values() for n in names} | set(OPTIONAL) | {
        "ALLOWED_ORIGINS", "AI_DAILY_REQUEST_LIMIT", "AI_MAX_OUTPUT_TOKENS", "AI_TIMEOUT_SECONDS"}
    names = set(render_env_blocks()) - {"PYTHON_VERSION"}
    assert names <= server_names and names <= env_example_names()
    # Render에는 중계 토큰을 OPENAI_API_KEY로 넣는다. 이 PC의 중계 서버용 변수는 Render에 두지 않는다.
    assert "HERMES_RELAY_TOKEN" not in names


def test_render_ai_values_match_verified_hermes_route():
    blocks = render_env_blocks()
    assert re.search(r"value:\s*gpt-5.5", blocks["AI_PROVIDER_MODEL"])
    assert re.search(r"value:\s*openai-codex", blocks["AI_PROVIDER_ROUTE"])


def test_render_enables_swagger_for_submission_verification():
    blocks = render_env_blocks()
    assert re.search(r"value:\s*\"?true\"?", blocks["ENABLE_API_DOCS"])


def test_vercel_config_builds_public_config_only():
    config = json.loads((ROOT / "web" / "vercel.json").read_text(encoding="utf-8"))
    assert "build-config.mjs" in config["buildCommand"]
    assert config.get("outputDirectory") in (".", None)
    blob = json.dumps(config)
    for secret_name in ("OPENAI_API_KEY", "FIREBASE_SERVICE_ACCOUNT_JSON", "HERMES_RELAY_TOKEN", "OWNER_UID"):
        assert secret_name not in blob
    # 정적 사이트: 로그인 화면과 앱이 같은 폴더에 있으므로 별도 라우팅 규칙이 필요 없다.
    assert not config.get("rewrites") and not config.get("redirects")


def test_vercel_headers_block_framing_and_sniffing():
    headers = json.loads((ROOT / "web" / "vercel.json").read_text(encoding="utf-8"))["headers"]
    flat = {h["key"].lower(): h["value"] for rule in headers for h in rule["headers"]}
    assert flat["x-content-type-options"] == "nosniff"
    assert flat["x-frame-options"] == "DENY"
    assert flat["referrer-policy"] == "no-referrer"


def test_vercel_csp_blocks_inline_scripts_and_framing():
    headers = json.loads((ROOT / "web" / "vercel.json").read_text(encoding="utf-8"))["headers"]
    flat = {h["key"].lower(): h["value"] for rule in headers for h in rule["headers"]}
    directives = {part.split()[0]: part.split()[1:] for part in flat["content-security-policy"].split("; ")}
    assert directives["frame-ancestors"] == ["'none'"]
    assert directives["object-src"] == ["'none'"]
    assert "'unsafe-inline'" not in directives["script-src"] + directives["style-src"]
    assert "*" not in directives["script-src"] + directives["connect-src"]


def test_web_pages_have_no_inline_script_or_style():
    import re

    for page in ("index.html", "login.html"):
        html = (ROOT / "web" / page).read_text(encoding="utf-8")
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html), page
        assert "<style" not in html and ' style="' not in html, page
