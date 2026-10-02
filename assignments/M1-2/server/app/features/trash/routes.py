"""휴지통 API (PRD §13: GET /api/trash, POST /api/trash/{id}/restore, DELETE /api/trash/{id}). T05.03."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.trash import service

router = APIRouter(prefix="/api/trash", tags=["trash"])


class RestoreBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)


@router.get("")
def list_trash(ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    return service.list_trash(store, ctx)


@router.post("/{material_id}/restore")
def restore(material_id: str, body: RestoreBody, ctx: RequestContext = Depends(get_context),
            store: Store = Depends(get_store)) -> dict:
    payload = body.model_dump()
    return run_idempotent(store, ctx, "POST", f"/api/trash/{material_id}/restore", payload,
                          lambda: Result(200, service.restore(store, ctx, material_id, body.expected_version))).body


@router.delete("/{material_id}")
def permanent_delete(material_id: str, expected_version: int = Query(ge=1),
                     confirm: Literal["permanent"] = Query(description="별도 확인. 'permanent'일 때만 지운다"),
                     ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    """영구 삭제. 일부 단계가 실패하면 200 `partial`이며 같은 API를 다시 부르면 이어서 지운다."""
    payload = {"expected_version": expected_version, "confirm": confirm}
    return run_idempotent(store, ctx, "DELETE", f"/api/trash/{material_id}", payload,
                          lambda: Result(200, service.permanent_delete(store, ctx, material_id, expected_version))).body
