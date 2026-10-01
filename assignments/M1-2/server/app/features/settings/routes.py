"""사용자 설정 API (PRD 외 추가, T02.04: GET/PUT /api/settings)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.settings import service

router = APIRouter(prefix="/api/settings", tags=["settings"])

Item = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        key = " ".join(item.split()).casefold()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)
    interests: list[Item] = Field(default_factory=list, max_length=20)
    activities: list[Item] = Field(default_factory=list, max_length=20)
    default_project_id: str | None = None

    @field_validator("interests", "activities")
    @classmethod
    def unique(cls, items: list[str]) -> list[str]:
        return _dedupe(items)


@router.get("")
def get_settings(ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    return service.get_settings(store, ctx)


@router.put("")
def put_settings(body: SettingsUpdate, ctx: RequestContext = Depends(get_context),
                 store: Store = Depends(get_store)) -> dict:
    payload = body.model_dump()
    return run_idempotent(
        store, ctx, "PUT", "/api/settings", payload,
        lambda: Result(200, service.put_settings(
            store, ctx, body.expected_version, body.interests, body.activities, body.default_project_id)),
    ).body
