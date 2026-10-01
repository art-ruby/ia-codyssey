"""AI Secretary API 진입점.

실행: `M1-2` 폴더에서 `python -m uvicorn app.main:app --app-dir server --reload`
"""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.auth import TokenVerifier, get_context
from app.core.config import ConfigError, Settings, load_settings
from app.core.context import RequestContext
from app.core.firestore import FirestoreStore, InvalidCursor, NotFound, Store, VersionConflict
from app.core.requests import IdempotencyConflict, IdempotencyKeyRequired

# 요청 로그: 메서드·경로 템플릿·상태·소요 시간·요청 ID만 남긴다. 본문·토큰·쿼리 값은 남기지 않는다(PRD §14).
request_log = logging.getLogger("ai_secretary.request")
if not request_log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    request_log.addHandler(_handler)
    request_log.setLevel(logging.INFO)


def get_store(request: Request) -> Store:
    """기능 라우터의 저장소 의존성. 첫 사용 때 Firestore에 연결한다."""
    state = request.app.state
    if state.store is None:
        try:
            state.store = FirestoreStore.from_settings(state.settings)
        except ConfigError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"저장소 설정 오류: {exc}") from None
    return state.store


def _error(code: int, detail: str, **extra) -> JSONResponse:
    return JSONResponse({"detail": detail, **extra}, status_code=code)


def create_app(settings: Settings | None = None, verify_token: TokenVerifier | None = None,
               store: Store | None = None) -> FastAPI:
    """테스트는 settings·verify_token·store를 직접 넘겨 실제 키·Firebase 없이 앱을 만든다.

    verify_token·store가 없으면 처음 필요할 때 Firebase Admin SDK로 만든다.
    그래서 Firebase 설정이 없어도 서버와 /health는 켜진다.
    """
    settings = settings or load_settings()
    app = FastAPI(title="AI Secretary API", version="0.1.0")
    app.state.settings = settings
    app.state.verify_token = verify_token
    app.state.store = store

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        request_log.info(
            "%s %s %s %.0fms id=%s", request.method, getattr(route, "path", "-"),
            response.status_code, (time.perf_counter() - started) * 1000, request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    # 저장소·중복 요청 규칙의 오류를 HTTP 코드로 바꾼다(docs/api-contract.md).
    @app.exception_handler(NotFound)
    async def not_found(_, __):
        return _error(404, "찾을 수 없습니다")

    @app.exception_handler(VersionConflict)
    async def version_conflict(_, exc: VersionConflict):
        return _error(409, "다른 곳에서 먼저 바뀌었습니다. 새로 불러온 뒤 다시 시도하세요",
                      current_version=exc.current_version)

    @app.exception_handler(IdempotencyConflict)
    async def idempotency_conflict(_, exc: IdempotencyConflict):
        detail = ("같은 요청 키로 다른 내용을 보냈습니다" if exc.reason == "different_request"
                  else "같은 요청을 처리하는 중입니다")
        return _error(409, detail, reason=exc.reason)

    @app.exception_handler(IdempotencyKeyRequired)
    async def key_required(_, __):
        return _error(422, "변경 요청에는 Idempotency-Key 헤더가 필요합니다(1~200자)")

    @app.exception_handler(InvalidCursor)
    async def invalid_cursor(_, __):
        return _error(422, "페이지 커서가 올바르지 않습니다")

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
