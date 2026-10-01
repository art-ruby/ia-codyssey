"""프로젝트 API (PRD §13: GET/POST /api/projects, PUT /api/projects/{id})."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.projects import service

router = APIRouter(prefix="/api/projects", tags=["projects"])

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    description: Description = ""


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    name: Name | None = None
    description: Description | None = None
    active: bool | None = None


@router.get("")
def list_projects(include_inactive: bool = Query(False), ctx: RequestContext = Depends(get_context),
                  store: Store = Depends(get_store)) -> dict:
    return {"items": service.list_projects(store, ctx, include_inactive)}


@router.post("", status_code=201)
def create_project(body: ProjectCreate, ctx: RequestContext = Depends(get_context),
                   store: Store = Depends(get_store)) -> dict:
    payload = body.model_dump()
    return run_idempotent(
        store, ctx, "POST", "/api/projects", payload,
        lambda: Result(201, service.create_project(store, ctx, body.name, body.description)),
    ).body


@router.put("/{project_id}")
def update_project(project_id: str, body: ProjectUpdate, ctx: RequestContext = Depends(get_context),
                   store: Store = Depends(get_store)) -> dict:
    payload = body.model_dump(exclude_none=True)
    changes = {k: v for k, v in payload.items() if k != "expected_version"}
    return run_idempotent(
        store, ctx, "PUT", f"/api/projects/{project_id}", payload,
        lambda: Result(200, service.update_project(store, ctx, project_id, body.expected_version, changes)),
    ).body
