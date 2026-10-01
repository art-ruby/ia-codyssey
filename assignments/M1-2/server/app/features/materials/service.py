"""자료(URL·텍스트) 접수·조회·수정 — T03.01, PRD §6.1·§9.

- 자료와 접수 기록(`intake_records`, 접수 건수 집계용)을 한 번의 원자적 쓰기로 함께 만든다.
- 입력만으로 AI를 호출하지 않는다. 첫 분석 상태는 URL만 있으면 `link_only`(본문 미확인),
  제목·설명·본문 중 하나라도 있으면 `awaiting_start`(사용자가 분석을 시작하기 전)다.
- 원래 URL은 출처로 보존하며 고칠 수 없다. 비교용 키(`url_key`)는 호스트 대소문자·기본 포트만
  정규화한다(T03.02의 같은 URL 확인에 쓴다).
- 제목이 없으면 화면용 임시 제목을 만들지만 저장하지 않고, `title_source`로 출처를 밝힌다.
"""
from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.core.context import RequestContext
from app.core.firestore import Page, Store, now_utc
from app.features.materials.schemas import CONTENT_FIELDS
from app.features.projects import service as projects

COLLECTION = "materials"
INTAKE = "intake_records"
DEFAULT_PORTS = {"http": 80, "https": 443}
TEXT_FIELDS = ("title", "description", "body", "save_reason", "memo")
EDITABLE = TEXT_FIELDS + ("primary_project_id", "related_project_ids")
PUBLIC_FIELDS = (
    "id", "source_type", "url", "title", "description", "body", "save_reason", "memo",
    "primary_project_id", "related_project_ids", "review_status", "analysis_status", "copy_status",
    "lifecycle", "ai_excluded", "registered_at", "storage_approved_at", "trashed_at",
    "version", "created_at", "updated_at",
)


class InvalidProjectReference(Exception):
    """연결하려는 프로젝트가 없거나 비활성이다(422)."""


class NoContent(Exception):
    """수정 결과 URL과 제목·설명·본문이 모두 비게 된다(422)."""


def url_key(url: str) -> str:
    """안전한 정규화만 한다: 스킴·호스트 소문자, 기본 포트 제거. 경로·쿼리·조각은 그대로 둔다."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if parts.port and parts.port != DEFAULT_PORTS.get(scheme):
        host = f"{host}:{parts.port}"
    userinfo = parts.netloc.rpartition("@")[0]
    netloc = f"{userinfo}@{host}" if userinfo else host
    return urlunsplit((scheme, netloc, parts.path, parts.query, parts.fragment))


def _has_content(doc: dict) -> bool:
    return any(doc.get(field) for field in CONTENT_FIELDS)


def display_title(doc: dict) -> tuple[str, str]:
    """(화면 제목, 출처). 출처: user(입력한 제목) | url(도메인) | text(설명·본문 앞부분)."""
    if doc.get("title"):
        return doc["title"], "user"
    if doc.get("url"):
        return urlsplit(doc["url"]).hostname or doc["url"], "url"
    lines = (doc.get("description") or doc.get("body") or "").strip().splitlines()
    first = lines[0] if lines else ""
    return (first[:40] + "…" if len(first) > 40 else first), "text"


def public(doc: dict) -> dict:
    out = {field: doc.get(field) for field in PUBLIC_FIELDS}
    out["display_title"], out["title_source"] = display_title(doc)
    return out


def _check_projects(store: Store, ctx: RequestContext, primary: str | None, related: list[str] | None) -> None:
    for project_id in ([primary] if primary else []) + list(related or []):
        if projects.get_active(store, ctx, project_id) is None:
            raise InvalidProjectReference()


def create_material(store: Store, ctx: RequestContext, data: dict[str, Any]) -> dict:
    _check_projects(store, ctx, data.get("primary_project_id"), data.get("related_project_ids"))
    url = data.get("url")
    now = now_utc()
    fields = {name: data.get(name) or "" for name in TEXT_FIELDS}
    doc = {
        "source_type": "url" if url else "text",
        "url": url,
        "url_key": url_key(url) if url else None,
        **fields,
        "primary_project_id": data.get("primary_project_id"),
        "related_project_ids": data.get("related_project_ids") or [],
        "review_status": "unreviewed",
        "analysis_status": "awaiting_start" if _has_content(fields) else "link_only",
        "copy_status": "not_applicable",  # 웹 자료는 원본 사본이 없다(확장 단계 파일만 해당)
        "lifecycle": "active",
        "ai_excluded": False,
        "registered_at": now,
        "storage_approved_at": None,
        "trashed_at": None,
    }
    material_id = uuid.uuid4().hex
    material, _ = store.create_many(ctx, [
        (COLLECTION, doc, material_id),
        (INTAKE, {"material_id": material_id, "received_at": now}, material_id),
    ])
    return public(material)


def list_materials(store: Store, ctx: RequestContext, limit: int = 20, cursor: str | None = None) -> dict:
    page: Page = store.list(ctx, COLLECTION, limit=limit, cursor=cursor, descending=True)
    return {"items": [public(d) for d in page.items], "next_cursor": page.next_cursor}


def get_material(store: Store, ctx: RequestContext, material_id: str) -> dict:
    return public(store.get(ctx, COLLECTION, material_id))


def update_material(store: Store, ctx: RequestContext, material_id: str, expected_version: int,
                    changes: dict[str, Any]) -> dict:
    current = store.get(ctx, COLLECTION, material_id)  # 남의 자료·없는 자료는 404
    changes = {k: v for k, v in changes.items() if k in EDITABLE}
    for name in TEXT_FIELDS:
        if name in changes and changes[name] is None:
            changes[name] = ""
    if "related_project_ids" in changes and changes["related_project_ids"] is None:
        changes["related_project_ids"] = []
    _check_projects(store, ctx, changes.get("primary_project_id"), changes.get("related_project_ids"))

    merged = {**current, **changes}
    if not merged.get("url") and not _has_content(merged):
        raise NoContent()
    if any(name in changes for name in CONTENT_FIELDS) and current.get("analysis_status") in (
            "link_only", "awaiting_start"):
        # 아직 분석하지 않은 자료는 내용에 맞춰 상태만 맞춘다. 분석 결과가 있는 자료의 재분석은 T04.02가 맡는다.
        changes["analysis_status"] = "awaiting_start" if _has_content(merged) else "link_only"
    return public(store.update(ctx, COLLECTION, material_id, expected_version, changes))
