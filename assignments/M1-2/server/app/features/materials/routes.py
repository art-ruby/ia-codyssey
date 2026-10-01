"""자료 API (PRD §13: POST/GET /api/materials, GET/PUT /api/materials/{id})."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.materials import service
from app.features.materials.schemas import MaterialCreate, MaterialUpdate

router = APIRouter(prefix="/api/materials", tags=["materials"])


@router.post("", status_code=201)
def create_material(body: MaterialCreate, ctx: RequestContext = Depends(get_context),
                    store: Store = Depends(get_store)) -> dict:
    payload = body.model_dump()
    return run_idempotent(
        store, ctx, "POST", "/api/materials", payload,
        lambda: Result(201, service.create_material(store, ctx, payload)),
    ).body


@router.get("")
def list_materials(limit: int = Query(20, ge=1, le=100), cursor: str | None = None,
                   ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    return service.list_materials(store, ctx, limit, cursor)


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
