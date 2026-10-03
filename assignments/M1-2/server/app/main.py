"""AI Secretary API 진입점.

실행: `M1-2` 폴더에서 `python -m uvicorn app.main:app --app-dir server --reload`
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.auth import TokenVerifier, get_context
from app.core.config import Settings, load_settings
from app.core.context import RequestContext
from app.core.deps import get_store  # noqa: F401  (기존 테스트가 app.main에서 가져온다)
from app.core.firestore import InvalidCursor, NotFound, Store, VersionConflict
from app.core.internal_error import InternalErrorJSON
from app.core.limits import BodySizeLimit
from app.core.requests import IdempotencyConflict, IdempotencyKeyRequired
from app.features.materials.routes import router as materials_router
from app.features.materials.schemas import LIMITS
from app.features.analysis.provider import AnalysisAdapter, HermesProvider
from app.features.analysis.routes import router as analysis_router
from app.features.analysis.routes import usage_router as ai_usage_router
from app.features.analysis.service import AnalysisInProgress, AnalysisRefused
from app.features.chat.context import QuestionTooLong
from app.features.chat.routes import router as chat_router
from app.features.chat.service import ChatFailed
from app.features.conversations.routes import router as conversations_router
from app.features.news.routes import router as news_router
from app.features.news.service import NewsError
from app.features.conversations.service import ConversationFull
from app.features.materials.service import (DuplicateUrl, InvalidDuplicateTarget, InvalidProjectReference,
                                            MemoTooLong, MissingSeparateTarget, NoContent, TrashedTarget, MaterialDeleting)
from app.features.projects.routes import router as projects_router
from app.features.projects.service import DuplicateProjectName, TooManyProjects
from app.features.reviews.routes import router as reviews_router
from app.features.reviews.service import PastRevisitDate
from app.features.settings.routes import router as settings_router
from app.features.trash.routes import router as trash_router
from app.features.telegram.routes import router as telegram_router
from app.features.data.routes import router as data_router
from app.features.data.summary import SourceNotAllowed
from app.features.trash.service import NotInTrash
from app.features.settings.service import InvalidDefaultProject

# 요청 로그: 메서드·경로 템플릿·상태·소요 시간·요청 ID만 남긴다. 본문·토큰·쿼리 값은 남기지 않는다(PRD §14).
request_log = logging.getLogger("ai_secretary.request")
if not request_log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    request_log.addHandler(_handler)
    request_log.setLevel(logging.INFO)


FIELD_NAMES = {
    "url": "URL", "title": "제목", "description": "설명", "body": "본문", "save_reason": "저장 이유",
    "memo": "메모", "name": "이름", "interests": "관심 분야", "activities": "활동 분야",
    "expected_version": "버전", "related_project_ids": "관련 프로젝트",
    "user_importance": "중요도", "items": "검토 항목", "material_id": "자료", "action": "작업",
    "view": "목록 보기", "revisit_on": "다시 볼 날짜", "ai_excluded": "AI 분석 제외",
    "question": "질문", "pending_id": "저장 대기 답변", "conversation_id": "대화",
}


def _validation_message(errors: list[dict]) -> str:
    """첫 오류를 한국어 안내로 바꾼다. 길이 초과는 한도를 함께 알린다(PRD §6.1: 조용히 자르지 않는다)."""
    if not errors:
        return "입력 내용을 확인하세요"
    first = errors[0]
    field = next((str(p) for p in reversed(first.get("loc", ())) if isinstance(p, str) and p != "body"), "")
    label = FIELD_NAMES.get(field, field or "입력")
    kind = first.get("type", "")
    limit = (first.get("ctx") or {}).get("max_length")
    if kind == "string_too_long":
        return f"{label}은(는) {limit or LIMITS.get(field, '')}자까지 입력할 수 있습니다"
    if kind == "too_long":
        return f"{label}은(는) {limit}개까지 넣을 수 있습니다"
    if kind == "too_short":
        return f"{label}을(를) 하나 이상 넣으세요"
    if kind == "extra_forbidden":
        return f"{label}은(는) 보낼 수 없는 항목입니다"
    if kind == "value_error":
        return str(first.get("msg", "")).removeprefix("Value error, ") or "입력 내용을 확인하세요"
    return f"{label} 입력 형식을 확인하세요"


ANALYSIS_REFUSED = {
    "trashed": "휴지통에 있는 자료는 분석할 수 없습니다. 복원한 뒤 다시 시도하세요",
    "ai_excluded": "AI 분석 제외 자료입니다. 제외를 해제해야 분석할 수 있습니다",
    "no_content": "링크만 저장된 자료라 분석할 내용이 없습니다. 제목·설명·본문을 입력하세요",
}


CHAT_FAILED = {
    "search_failed": "자료를 검색하지 못했습니다. 저장한 자료가 없다는 뜻이 아닙니다. 잠시 뒤 다시 시도하세요",
    "quota_exceeded": "오늘 AI 요청 한도에 도달했습니다. 서울 시간 자정 이후 다시 질문하세요",
    "provider_failed": "AI 답변을 받지 못했습니다. 대화는 저장하지 않았습니다. 다시 시도하세요",
}


def _error(code: int, detail: str, **extra) -> JSONResponse:
    return JSONResponse({"detail": detail, **extra}, status_code=code)


def create_app(settings: Settings | None = None, verify_token: TokenVerifier | None = None,
               store: Store | None = None,
               analysis_adapter_factory: Callable[[], AnalysisAdapter] | None = None) -> FastAPI:
    """테스트는 settings·verify_token·store를 직접 넘겨 실제 키·Firebase 없이 앱을 만든다.

    verify_token·store가 없으면 처음 필요할 때 Firebase Admin SDK로 만든다.
    그래서 Firebase 설정이 없어도 서버와 /health는 켜진다.
    """
    settings = settings or load_settings()
    # API 구조(/docs·/redoc·/openapi.json)는 인증 없이 보이므로 기본은 끈다. 과제 제출처럼 Swagger를 공개해야 하는
    # 배포에서만 ENABLE_API_DOCS=true로 켠다. 문서에는 데이터가 없고 모든 /api 호출은 여전히 로그인이 필요하다.
    docs_on = settings.get("ENABLE_API_DOCS").lower() == "true"
    app = FastAPI(title="AI Secretary API", version="0.1.0",
                  docs_url="/docs" if docs_on else None, redoc_url="/redoc" if docs_on else None,
                  openapi_url="/openapi.json" if docs_on else None)
    app.state.settings = settings
    app.state.verify_token = verify_token
    app.state.store = store
    # 분석 작업마다 Adapter를 만든다. 설정이 비어 있으면 그 작업만 `missing_ai_settings`로 실패한다(T04.02).
    app.state.analysis_adapter_factory = analysis_adapter_factory or (
        lambda: AnalysisAdapter(HermesProvider(settings)))
    app.state.telegram_send_message = None

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

    @app.exception_handler(DuplicateProjectName)
    async def duplicate_project(_, __):
        return _error(409, "같은 이름의 프로젝트가 이미 있습니다", reason="duplicate_name")

    @app.exception_handler(TooManyProjects)
    async def too_many_projects(_, __):
        return _error(422, "프로젝트는 100개까지 만들 수 있습니다")

    @app.exception_handler(InvalidDefaultProject)
    async def invalid_default_project(_, __):
        return _error(422, "기본 프로젝트는 활성 상태인 내 프로젝트여야 합니다")

    @app.exception_handler(InvalidProjectReference)
    async def invalid_project_reference(_, __):
        return _error(422, "연결할 프로젝트는 활성 상태인 내 프로젝트여야 합니다")

    @app.exception_handler(NewsError)
    async def news_error(_, exc: NewsError):
        return _error(exc.status, exc.message, reason=exc.reason)

    @app.exception_handler(NoContent)
    async def no_content(_, __):
        return _error(422, "URL 또는 제목·설명·본문 중 하나 이상이 남아 있어야 합니다")

    @app.exception_handler(DuplicateUrl)
    async def duplicate_url(_, exc: DuplicateUrl):
        return _error(409, "같은 URL의 자료가 이미 있습니다. 기존 자료 열기·메모 추가·별도 저장 중에서 고르세요",
                      reason="duplicate_url", existing=exc.existing)

    @app.exception_handler(TrashedTarget)
    async def trashed_target(_, __):
        return _error(409, "휴지통에 있는 자료에는 메모를 더할 수 없습니다. 복원한 뒤 다시 시도하세요",
                      reason="trashed")

    @app.exception_handler(InvalidDuplicateTarget)
    async def invalid_duplicate_target(_, __):
        return _error(422, "메모를 더할 자료가 없거나 같은 URL의 자료가 아닙니다")

    @app.exception_handler(MissingSeparateTarget)
    async def missing_separate_target(_, __):
        return _error(422, "같은 URL의 기존 자료가 없습니다. 일반 접수로 다시 시도하세요")

    @app.exception_handler(MemoTooLong)
    async def memo_too_long(_, __):
        return _error(422, "메모를 더하면 2000자를 넘습니다. 기존 메모를 줄이거나 별도로 저장하세요")

    @app.exception_handler(PastRevisitDate)
    async def past_revisit_date(_, __):
        return _error(422, "다시 볼 날짜는 오늘(서울 기준) 이후여야 합니다")

    @app.exception_handler(SourceNotAllowed)
    async def source_not_allowed(_, __):
        return _error(422, "이 모드에서 쓸 수 없는 출처입니다. 개인 모드는 actual·manual, 표본 모드는 sample·actual입니다",
                      reason="source_not_allowed")

    @app.exception_handler(NotInTrash)
    async def not_in_trash(_, __):
        return _error(409, "휴지통에 있는 자료만 복원하거나 영구 삭제할 수 있습니다", reason="not_in_trash")

    @app.exception_handler(MaterialDeleting)
    async def material_deleting(_, __):
        return _error(409, "영구 삭제가 진행 중이거나 일부 실패한 자료입니다. 휴지통에서 삭제를 다시 시도하세요",
                      reason="deleting")

    @app.exception_handler(AnalysisRefused)
    async def analysis_refused(_, exc: AnalysisRefused):
        return _error(409, ANALYSIS_REFUSED[exc.reason], reason=exc.reason)

    @app.exception_handler(AnalysisInProgress)
    async def analysis_in_progress(_, __):
        return _error(409, "이미 분석 중입니다. 끝나면 결과가 표시됩니다", reason="analysis_in_progress")

    @app.exception_handler(ChatFailed)
    async def chat_failed(_, exc: ChatFailed):
        extra = {"kind": exc.kind} if exc.kind else {}
        return _error(exc.status, CHAT_FAILED[exc.reason], reason=exc.reason, **extra)

    @app.exception_handler(QuestionTooLong)
    async def question_too_long(_, __):
        return _error(422, "질문은 2000자까지 입력할 수 있습니다")

    @app.exception_handler(ConversationFull)
    async def conversation_full(_, __):
        return _error(409, "이 대화는 메시지 한도에 도달했습니다. 새 대화를 시작하세요", reason="conversation_full")

    @app.exception_handler(RequestValidationError)
    async def validation_error(_, exc: RequestValidationError):
        # 사용자가 이해할 수 있는 안내를 detail로 준다. 입력값(input)은 응답에 되돌려 보내지 않는다.
        errors = [{"loc": [str(p) for p in e.get("loc", ())], "type": e.get("type")} for e in exc.errors()]
        return _error(422, _validation_message(exc.errors()), errors=errors)

    app.include_router(projects_router)
    app.include_router(settings_router)
    app.include_router(materials_router)
    app.include_router(reviews_router)
    app.include_router(analysis_router)
    app.include_router(ai_usage_router)
    app.include_router(trash_router)
    app.include_router(data_router)
    app.include_router(chat_router)
    app.include_router(conversations_router)
    app.include_router(news_router)
    app.include_router(telegram_router)

    # CORS보다 안쪽에 둬서 413 응답에도 CORS 헤더가 붙게 한다(브라우저가 원인을 볼 수 있다).
    app.add_middleware(BodySizeLimit)
    # 처리되지 않은 예외도 CORS 안쪽에서 JSON 500으로 바꿔, 브라우저가 연결 실패가 아닌 서버 오류로 보게 한다.
    app.add_middleware(InternalErrorJSON)

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
