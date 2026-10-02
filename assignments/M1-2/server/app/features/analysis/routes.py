"""분석 API (PRD §13: POST /api/materials/{id}/analyze, T04.02).

202는 접수만 의미한다. 결과는 `GET /api/materials/{id}`의 `analysis_status`로 조회한다.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.analysis import service, usage

router = APIRouter(prefix="/api/materials", tags=["analysis"])
usage_router = APIRouter(prefix="/api/ai", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)


@router.post("/{material_id}/analyze", status_code=202,
             responses={200: {"description": "같은 입력의 완료 결과 재사용(reused) 또는 오늘 한도 도달(quota_waiting). Provider 호출 없음"},
                        409: {"description": "버전 충돌·분석 중·분석할 수 없는 자료"}})
def analyze_material(material_id: str, body: AnalyzeRequest, request: Request, background: BackgroundTasks,
                     ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)):
    jobs: list[service.Job] = []
    settings = request.app.state.settings

    def handler() -> Result:
        code, payload, job = service.start_analysis(store, ctx, material_id, body.expected_version,
                                                    settings.ai_timeout_seconds, settings.ai_daily_request_limit)
        if job:
            jobs.append(job)
        return Result(code, payload)

    result = run_idempotent(store, ctx, "POST", f"/api/materials/{material_id}/analyze", body.model_dump(), handler)
    # 같은 키를 다시 보낸 경우(재생)는 handler가 돌지 않으므로 작업도 다시 만들지 않는다.
    for job in jobs:
        background.add_task(service.run_job, store, ctx, job, request.app.state.analysis_adapter_factory)
    return JSONResponse(result.body, status_code=result.status_code)


# 오늘 한도 대기 자료 수는 이 개수까지만 센다. 넘으면 `pending_capped`로 알린다.
PENDING_COUNT_CAP = 100


@usage_router.get("/usage")
def ai_usage(request: Request, ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    """PRD 외 추가(T04.03). 오늘(서울) AI 요청 사용량. 개인·표본 모드를 합산한다. 대기 자료 수는 현재 모드 기준."""
    settings = request.app.state.settings
    waiting = store.find(ctx, "materials", "analysis_status", "quota_waiting", limit=PENDING_COUNT_CAP)
    return {
        **usage.summary(store, ctx.owner_id, settings.ai_daily_request_limit),
        "pending_count": len(waiting),
        "pending_capped": len(waiting) >= PENDING_COUNT_CAP,
        "max_output_tokens": settings.ai_max_output_tokens,
        "timeout_seconds": settings.ai_timeout_seconds,
    }
