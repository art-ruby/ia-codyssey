"""보안 점검 보완(보안취약점.md 10·22·25번) 회귀 테스트."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core import auth as auth_module
from app.core.auth import InvalidToken
from app.core.config import load_settings
from app.core.limits import MAX_REQUEST_BYTES, BodySizeLimit
from app.main import create_app

OWNER = "owner-1"


def make_client(**env):
    return TestClient(create_app(load_settings({"OWNER_UID": OWNER, **env}), verify_token=lambda t: {"uid": OWNER}))


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_are_not_exposed(path):
    assert make_client().get(path).status_code == 404


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_can_be_enabled_for_submission(path):
    assert make_client(ENABLE_API_DOCS="true").get(path).status_code == 200


def test_oversized_body_is_rejected_before_auth_or_validation():
    res = make_client().post("/api/projects", content=b"x" * (MAX_REQUEST_BYTES + 1),
                             headers={"Content-Type": "application/json"})

    assert res.status_code == 413


def test_body_within_limit_still_reaches_the_route():
    res = make_client().post("/api/projects", content=b"{}", headers={"Content-Type": "application/json"})

    assert res.status_code != 413


def _run_asgi(middleware, chunks, headers):
    sent = []

    async def downstream(scope, receive, send):
        while True:
            message = await receive()
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    app = middleware(downstream)
    queue = [{"type": "http.request", "body": c, "more_body": i < len(chunks) - 1} for i, c in enumerate(chunks)]

    async def receive():
        return queue.pop(0)

    async def send(message):
        sent.append(message)

    asyncio.run(app({"type": "http", "headers": headers}, receive, send))
    return sent


def test_chunked_body_without_content_length_is_cut_off():
    sent = _run_asgi(lambda a: BodySizeLimit(a, max_bytes=10), [b"123456", b"789012"], headers=[])

    assert sent[0]["status"] == 413


def test_chunked_body_within_limit_passes():
    sent = _run_asgi(lambda a: BodySizeLimit(a, max_bytes=10), [b"123", b"456"], headers=[])

    assert sent[0]["status"] == 200


def test_invalid_content_length_header_is_400():
    sent = _run_asgi(lambda a: BodySizeLimit(a, max_bytes=10), [b"1"], headers=[(b"content-length", b"abc")])

    assert sent[0]["status"] == 400


def test_token_verification_checks_revocation(monkeypatch):
    from firebase_admin import auth

    calls = []

    def fake_verify_id_token(token, app=None, check_revoked=False):
        calls.append(check_revoked)
        return {"uid": OWNER}

    monkeypatch.setattr(auth_module, "firebase_app", lambda settings: object())
    monkeypatch.setattr(auth, "verify_id_token", fake_verify_id_token)

    verify = auth_module.firebase_verifier(load_settings({}))
    assert verify("token") == {"uid": OWNER}
    assert calls == [True]


@pytest.mark.parametrize("error_name", ["RevokedIdTokenError", "UserDisabledError"])
def test_revoked_or_disabled_account_is_invalid_token(monkeypatch, error_name):
    from firebase_admin import auth

    def fake_verify_id_token(token, app=None, check_revoked=False):
        raise getattr(auth, error_name)("blocked")

    monkeypatch.setattr(auth_module, "firebase_app", lambda settings: object())
    monkeypatch.setattr(auth, "verify_id_token", fake_verify_id_token)

    verify = auth_module.firebase_verifier(load_settings({}))
    with pytest.raises(InvalidToken):
        verify("token")
