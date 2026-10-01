"""AI Secretary API 진입점.

실행: `M1-2` 폴더에서 `python -m uvicorn app.main:app --app-dir server --reload`
"""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import TokenVerifier, get_context
from app.core.config import Settings, load_settings
from app.core.context import RequestContext


def create_app(settings: Settings | None = None, verify_token: TokenVerifier | None = None) -> FastAPI:
    """테스트는 settings와 verify_token을 직접 넘겨 실제 키·Firebase 없이 앱을 만든다.

    verify_token이 없으면 첫 인증 요청 때 Firebase Admin SDK 검증 함수를 만든다.
    그래서 Firebase 설정이 없어도 서버와 /health는 켜진다.
    """
    settings = settings or load_settings()
    app = FastAPI(title="AI Secretary API", version="0.1.0")
    app.state.settings = settings
    app.state.verify_token = verify_token

    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.allowed_origins),
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health")
    def health() -> dict:
        """서버가 켜졌는지와 설정 묶음의 준비 상태. 값은 내보내지 않는다."""
        missing = settings.missing()
        return {
            "status": "ok",
            "config": {group: ("ready" if not names else "missing") for group, names in missing.items()},
            "missing": missing,
        }

    @app.get("/api/me")
    def me(ctx: RequestContext = Depends(get_context)) -> dict:
        """로그인·소유자·모드 확인용(PRD 외 추가 API, docs/api-contract.md)."""
        return {"owner_id": ctx.owner_id, "mode": ctx.mode}

    return app


app = create_app()
