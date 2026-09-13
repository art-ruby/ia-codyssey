"""RADAR Decision Assistant — FastAPI 진입점.

역할: RADAR 가 찾은 후보를 저장·분석하고, AI 가 그 데이터를 근거로
MAKE / WATCH / SKIP 판단을 돕고, 확정분을 AutoMaker 가 읽을 형태로 넘긴다.
RADAR 를 다시 만들거나 AutoMaker 를 수정하지 않는다(명세 17절).
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .repositories.store import get_store
from .routers import chat, conversations, data, handoff

settings = get_settings()

app = FastAPI(
    title="RADAR Decision Assistant",
    version="1.0.0",
    description=(
        "RADAR → AutoMaker 사이의 판단·기록 계층. "
        "후보를 저장·요약하고 AI 판단을 돕되, 최종 확정은 사용자가 한다."
    ),
)

# 과제 7절: 배포 시 CORS 허용 도메인을 환경 변수로 넘긴다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,  # 토큰 인증이 없으므로 자격증명 전송을 켜지 않는다
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(handoff.router)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    """미처리 예외에 error_code 를 붙인다.

    AutoMaker 감사에서 본 실패 방식을 되풀이하지 않기 위해서다 — 모든 예외를
    문구 하나로 뭉치면 사용자도 개발자도 원인을 구분할 수 없다.
    """
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "internal_error",
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            "path": request.url.path,
        },
    )


@app.get("/", tags=["meta"], summary="서비스 개요")
def root() -> dict:
    return {
        "service": "RADAR Decision Assistant",
        "docs": "/docs",
        "health": "/api/health",
        "role": "RADAR 발견 → 판단·기록 → AutoMaker 인계",
    }


@app.get("/api/health", tags=["meta"], summary="구동 모드와 의존성 상태")
def health() -> dict:
    """지금 어떤 모드로 떠 있는지 분명히 알린다.

    키가 없어 메모리 저장·규칙 기반 응답으로 도는 상태를 '정상'처럼
    보여주면, 배포 후에도 그 사실을 모른 채 쓰게 된다.
    """
    store = get_store(settings)
    return {
        "ok": True,
        "store": store.backend_name,
        "store_is_persistent": store.backend_name == "firestore",
        "openai_configured": settings.openai_enabled,
        "openai_model": settings.openai_model if settings.openai_enabled else None,
        # 어느 엔드포인트로 나가는지 — 프록시 오설정을 조기에 드러낸다. 키는 넣지 않는다.
        "openai_endpoint": (settings.openai_base_url or "https://api.openai.com/v1")
        if settings.openai_enabled else None,
        "allowed_origins": settings.allowed_origins,
        "automaker_url": settings.automaker_url,
        "radar_root": settings.radar_root or None,
        "radar_decisions_write": settings.radar_decisions_write,
        "warnings": [
            w
            for w in (
                None if settings.firestore_enabled else "FIREBASE_SERVICE_ACCOUNT_JSON 없음 — 재시작하면 데이터가 사라집니다",
                None if settings.openai_enabled else "OPENAI_API_KEY 없음 — AI 답변 대신 규칙 기반 계산 결과를 반환합니다",
                None if (settings.radar_decisions_write or not settings.radar_root)
                else "RADAR_DECISIONS_WRITE 꺼짐 — 실측 후보의 결정이 RADAR decisions.jsonl 에 남지 않습니다",
            )
            if w
        ],
    }


@app.on_event("startup")
def _banner() -> None:
    print(f"[RADAR Decision Assistant] {settings.mode_banner()}")
