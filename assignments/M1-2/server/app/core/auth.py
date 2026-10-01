"""Firebase ID 토큰 검증과 단일 소유자 확인.

판정 순서: 토큰 없음·무효 401 → 인증 설정 누락 503 → 소유자 아님 403 → 모드 없음·허용 밖 422.
헤더는 FastAPI 매개변수 대신 직접 읽는다. 매개변수로 선언하면 FastAPI가 인증보다
먼저 422를 내서, 로그인하지 않은 요청이 401이 아닌 422를 받게 되기 때문이다.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Mapping

from fastapi import HTTPException, Request, status

from app.core.config import ConfigError, Settings
from app.core.context import MODES, RequestContext

# ID 토큰을 받아 디코딩된 클레임을 돌려준다. 무효하면 InvalidToken을 낸다.
TokenVerifier = Callable[[str], Mapping[str, Any]]

FIREBASE_APP_NAME = "ai-secretary"


class InvalidToken(Exception):
    """토큰이 없거나, 형식이 틀리거나, 만료·위조되었다."""


def firebase_verifier(settings: Settings) -> TokenVerifier:
    """서비스 계정으로 Admin SDK를 초기화한 검증 함수. 설정이 없거나 틀리면 ConfigError."""
    settings.require("firebase")
    try:
        account = json.loads(settings.get("FIREBASE_SERVICE_ACCOUNT_JSON"))
        if not isinstance(account, dict):
            raise ValueError
    except ValueError:
        # 서비스 계정 내용이 오류 메시지·로그에 남지 않게 변수 이름만 알린다.
        raise ConfigError("FIREBASE_SERVICE_ACCOUNT_JSON은 JSON 객체여야 합니다") from None

    import firebase_admin
    from firebase_admin import auth, credentials

    try:
        app = firebase_admin.get_app(FIREBASE_APP_NAME)
    except ValueError:
        try:
            app = firebase_admin.initialize_app(credentials.Certificate(account), name=FIREBASE_APP_NAME)
        except ValueError:
            raise ConfigError("FIREBASE_SERVICE_ACCOUNT_JSON이 서비스 계정 형식이 아닙니다") from None

    def verify(token: str) -> Mapping[str, Any]:
        try:
            return auth.verify_id_token(token, app=app)
        except (ValueError, auth.InvalidIdTokenError, auth.ExpiredIdTokenError,
                auth.RevokedIdTokenError, auth.CertificateFetchError) as exc:
            raise InvalidToken(type(exc).__name__) from None

    return verify


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "로그인이 필요합니다",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _verifier(request: Request) -> TokenVerifier:
    state = request.app.state
    if state.verify_token is None:
        try:
            state.verify_token = firebase_verifier(state.settings)
        except ConfigError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"인증 설정 오류: {exc}") from None
    return state.verify_token


def get_context(request: Request) -> RequestContext:
    """보호된 API의 공통 의존성."""
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized()

    verify = _verifier(request)
    try:
        claims = verify(token.strip())
    except InvalidToken:
        raise _unauthorized() from None

    owner_uid = request.app.state.settings.get("OWNER_UID")
    if not owner_uid:
        # 소유자가 정해지지 않았으면 아무도 허용하지 않는다.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "인증 설정 오류: OWNER_UID 누락")
    if claims.get("uid") != owner_uid:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "허용된 소유자 계정이 아닙니다")

    mode = request.headers.get("X-Data-Mode", "").strip()
    if mode not in MODES:
        raise HTTPException(
            422,  # Starlette 상수 이름이 버전마다 달라 숫자로 쓴다.
            f"X-Data-Mode 헤더는 {'|'.join(MODES)} 중 하나여야 합니다",
        )

    key = request.headers.get("Idempotency-Key", "").strip() or None
    return RequestContext(owner_id=owner_uid, mode=mode, request_id=key)
