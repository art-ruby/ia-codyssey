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
from app.features.analysis import service

router = APIRouter(prefix="/api/materials", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)


@router.post("/{material_id}/analyze", status_code=202,
             responses={200: {"description": "같은 입력의 완료된 결과를 재사용(Provider 호출 없음)"},
                        409: {"description": "버전 충돌·분석 중·분석할 수 없는 자료"}})
def analyze_material(material_id: str, body: AnalyzeRequest, request: Request, background: BackgroundTasks,
                     ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)):
    jobs: list[service.Job] = []
    timeout = request.app.state.settings.ai_timeout_seconds

    def handler() -> Result:
        code, payload, job = service.start_analysis(store, ctx, material_id, body.expected_version, timeout)
        if job:
            jobs.append(job)
        return Result(code, payload)

    result = run_idempotent(store, ctx, "POST", f"/api/materials/{material_id}/analyze", body.model_dump(), handler)
    # 같은 키를 다시 보낸 경우(재생)는 handler가 돌지 않으므로 작업도 다시 만들지 않는다.
    for job in jobs:
        background.add_task(service.run_job, store, ctx, job, request.app.state.analysis_adapter_factory)
    return JSONResponse(result.body, status_code=result.status_code)
