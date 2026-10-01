import pytest
from fastapi.testclient import TestClient

from app.core.auth import InvalidToken, firebase_verifier
from app.core.config import ConfigError, load_settings
from app.main import create_app

OWNER = "owner-1"
TOKENS = {"owner-token": {"uid": OWNER}, "other-token": {"uid": "intruder"}}


def fake_verify(token):
    if token not in TOKENS:
        raise InvalidToken("bad")
    return TOKENS[token]


def client(owner_uid=OWNER):
    return TestClient(create_app(load_settings({"OWNER_UID": owner_uid}), verify_token=fake_verify))


def get_me(c, token=None, mode="personal", key=None):
    headers = {}
    if token is not None:
        headers["Authorization"] = token
    if mode is not None:
        headers["X-Data-Mode"] = mode
    if key is not None:
        headers["Idempotency-Key"] = key
    return c.get("/api/me", headers=headers)


@pytest.mark.parametrize("auth", [None, "", "Bearer ", "Basic owner-token", "owner-token", "Bearer nope"])
def test_missing_or_invalid_token_is_401(auth):
    res = get_me(client(), auth)

    assert res.status_code == 401
    assert res.headers["WWW-Authenticate"] == "Bearer"


def test_auth_is_checked_before_mode():
    # 로그인하지 않은 요청은 모드가 없어도 422가 아니라 401이다.
    assert get_me(client(), None, mode=None).status_code == 401


def test_authenticated_non_owner_is_403():
    assert get_me(client(), "Bearer other-token").status_code == 403


def test_no_owner_configured_allows_nobody():
    res = get_me(client(owner_uid=""), "Bearer owner-token")

    assert res.status_code == 503
    assert "OWNER_UID" in res.json()["detail"]


@pytest.mark.parametrize("mode", [None, "", "Personal", "admin"])
def test_owner_with_missing_or_unknown_mode_is_422(mode):
    assert get_me(client(), "Bearer owner-token", mode=mode).status_code == 422


@pytest.mark.parametrize("mode", ["personal", "sample"])
def test_owner_passes_with_mode(mode):
    res = get_me(client(), "Bearer owner-token", mode=mode, key="req-1")

    assert res.status_code == 200
    assert res.json() == {"owner_id": OWNER, "mode": mode}


def test_missing_firebase_config_is_503_not_open():
    # 검증 함수를 주입하지 않으면 실제 Firebase 설정이 필요하다. 없으면 통과시키지 않는다.
    c = TestClient(create_app(load_settings({})))

    res = get_me(c, "Bearer owner-token")

    assert res.status_code == 503


def test_service_account_errors_do_not_echo_content():
    secret = '"private_key": "SECRET-MATERIAL"'
    settings = load_settings({"OWNER_UID": OWNER, "FIREBASE_SERVICE_ACCOUNT_JSON": "{" + secret})

    with pytest.raises(ConfigError) as err:
        firebase_verifier(settings)

    assert "FIREBASE_SERVICE_ACCOUNT_JSON" in str(err.value)
    assert "SECRET-MATERIAL" not in str(err.value)
