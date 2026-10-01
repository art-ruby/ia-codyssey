"""AI Secretary API 진입점.

실행: `M1-2` 폴더에서 `python -m uvicorn app.main:app --app-dir server --reload`
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, load_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """테스트는 settings를 직접 넘겨 실제 키 없이 앱을 만든다."""
    settings = settings or load_settings()
    app = FastAPI(title="AI Secretary API", version="0.1.0")
    app.state.settings = settings

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

    return app


app = create_app()
