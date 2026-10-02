"""자료 API (PRD §13: POST/GET /api/materials, GET/PUT /api/materials/{id}).

PRD 외 추가: GET /api/materials/search(T05.01), GET /api/materials/priority(T04.04).
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.analysis.schemas import KINDS
from app.features.materials import priority, search, service
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


@router.get("/search")
def search_materials(
    q: str = Query("", max_length=200),
    date_from: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    date_to: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    kind: Literal[KINDS] | None = None,
    source_type: Literal["url", "text"] | None = None,
    project_id: str | None = Query(None, max_length=200),
    limit: int = Query(20, ge=1, le=search.MAX_PAGE_SIZE),
    cursor: str | None = None,
    ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store),
) -> dict:
    """PRD 외 추가(T05.01). 보관 완료 자료 검색. 기간은 서울 날짜(양 끝 포함)."""
    for value in (date_from, date_to):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError:
                raise HTTPException(422, "날짜가 올바르지 않습니다") from None
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "시작 날짜가 끝 날짜보다 늦습니다")
    page = search.search_materials(store, ctx, q, search.SearchFilters(date_from, date_to, kind, source_type, project_id),
                                   cursor, limit)
    return {"items": page.items, "next_cursor": page.next_cursor, "total_matches": page.total_matches,
            "scope": page.scope}


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
