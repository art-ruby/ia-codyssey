"""프로젝트: 자료의 주 프로젝트·관련 프로젝트로 연결되는 대상(Open Decision 1).

- 소유자·모드별로 따로 관리한다(표본 모드에는 표본 프로젝트).
- 지우지 않고 `active=False`로 비활성 처리해, 기존 자료의 참조가 깨지지 않게 한다.
- 이름은 같은 소유자·모드 안에서 대소문자·공백 차이를 무시하고 겹치지 않는다(비활성 포함).
"""
from __future__ import annotations

from typing import Any

from app.core.context import RequestContext
from app.core.firestore import NotFound, Store
from app.features.projects.atomic import DuplicateProjectName, TooManyProjects, change_project

COLLECTION = "projects"
PUBLIC_FIELDS = ("id", "name", "description", "active", "version", "created_at", "updated_at")


def public(doc: dict) -> dict:
    return {field: doc.get(field) for field in PUBLIC_FIELDS}


def _all(store: Store, ctx: RequestContext) -> list[dict]:
    docs, cursor = [], None
    while True:
        page = store.list(ctx, COLLECTION, limit=100, cursor=cursor)
        docs += page.items
        if not page.next_cursor:
            return docs
        cursor = page.next_cursor


def list_projects(store: Store, ctx: RequestContext, include_inactive: bool = False) -> list[dict]:
    docs = _all(store, ctx)
    return [public(d) for d in docs if include_inactive or d.get("active", True)]


def get_active(store: Store, ctx: RequestContext, project_id: str) -> dict | None:
    """활성 프로젝트면 문서, 없거나 비활성이면 None."""
    try:
        doc = store.get(ctx, COLLECTION, project_id)
    except NotFound:
        return None
    return doc if doc.get("active", True) else None


def create_project(store: Store, ctx: RequestContext, name: str, description: str) -> dict:
    return public(change_project(store, ctx, None, None, {"name": name, "description": description}))


def update_project(store: Store, ctx: RequestContext, project_id: str, expected_version: int,
                   changes: dict[str, Any]) -> dict:
    return public(change_project(store, ctx, project_id, expected_version, changes))
