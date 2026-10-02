"""자료 API (PRD §13: POST/GET /api/materials, GET/PUT /api/materials/{id})."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.materials import priority, service
from app.features.materials.schemas import MaterialCreate, MaterialUpdate

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.post("", status_code=201, responses={200: {"description": "같은 URL 자료에 메모를 더함"}, 409: {"description": "같은 URL 자료가 있음"}})
def create_material(body: MaterialCreate, ctx: RequestContext = Depends(get_context),
                    store: Store = Depends(get_store)):
    payload = body.model_dump()
    # 새 자료는 201, 같은 URL 자료에 메모를 더하면 200이다. 다시 보낸 요청도 처음 상태 코드를 그대로 쓴다.
    result = run_idempotent(store, ctx, "POST", "/api/materials", payload,
                            lambda: Result(*service.create_material(store, ctx, payload)))
    return JSONResponse(result.body, status_code=result.status_code)


@router.get("")
def list_materials(limit: int = Query(20, ge=1, le=100), cursor: str | None = None,
                   view: Literal["all", "inbox", "review", "later"] = "all",
                   ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    # view(PRD 외 추가, T03.03·T03.04): inbox=받은 자료, review=승인 요청 목록, later=나중에 보기. 커서는 같은 view로만 이어 쓴다.
    return service.list_materials(store, ctx, limit, cursor, view)


@router.get("/priority")
def material_priority(ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    # PRD 외 추가(T04.04). 오늘·AI 동향용 우선순위. `/{material_id}`보다 먼저 선언해야 경로가 겹치지 않는다.
    return priority.priority_view(store, ctx)


@router.get("/{material_id}")
def get_material(material_id: str, ctx: RequestContext = Depends(get_context),
                 store: Store = Depends(get_store)) -> dict:
    return service.get_material(store, ctx, material_id)


@router.put("/{material_id}")
def update_material(material_id: str, body: MaterialUpdate, ctx: RequestContext = Depends(get_context),
                    store: Store = Depends(get_store)) -> dict:
    # 보낸 필드만 바꾼다. null을 보내면 그 필드를 비운다.
    payload = body.model_dump(exclude_unset=True)
    changes = {k: v for k, v in payload.items() if k != "expected_version"}
    return run_idempotent(
        store, ctx, "PUT", f"/api/materials/{material_id}", payload,
        lambda: Result(200, service.update_material(store, ctx, material_id, body.expected_version, changes)),
    ).body
