"""자료(URL·텍스트) 접수·조회·수정 — T03.01·T03.02, PRD §6.1·§9.

- 자료와 접수 기록(`intake_records`, 접수 건수 집계용)을 한 번의 원자적 쓰기로 함께 만든다.
- 입력만으로 AI를 호출하지 않는다. 첫 분석 상태는 URL만 있으면 `link_only`(본문 미확인),
  제목·설명·본문 중 하나라도 있으면 `awaiting_start`(사용자가 분석을 시작하기 전)다.
- 원래 URL은 출처로 보존하며 고칠 수 없다. 같은 URL 판정은 비교 키(`url_key`)로 한다(url_keys.py).
- 제목이 없으면 화면용 임시 제목을 만들지만 저장하지 않고, `title_source`로 출처를 밝힌다.

같은 URL(T03.02, docs/decisions.md):
- 같은 소유자·모드에 같은 비교 키의 자료가 있으면 만들지 않고 DuplicateUrl(409)로 기존 자료를 알린다.
- 사용자가 고른 뒤 다시 보낸다: `save_separately`는 새 자료(접수 기록 +1), `add_memo`는 기존 자료의
  메모 끝에 날짜와 함께 덧붙인다(본문은 그대로, 접수 기록 없음). `기존 자료 열기`는 서버 요청이 없다.
- 동시에 같은 URL을 처음 등록하면 URL별 예약 문서(`url_index`)를 자료와 같은 일괄 쓰기로 만들어 하나만
  성공시킨다. 예약은 동시 등록 방지용일 뿐이며 판정은 자료 검색으로 한다. 예약이 가리키는 자료가 없으면
  (영구 삭제 뒤 정리되지 않은 경우) 예약을 지우고 한 번 다시 시도한다. 영구 삭제(T05.03)는 그 자료를
  가리키는 예약도 함께 지운다. 예약이 없는 기존 자료(T03.01에 만든 것)는 자료 검색으로 판정되므로
  따로 채울 필요가 없다.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from app.core.context import RequestContext
from app.core.errors import NoChange
from app.core.firestore import NotFound, Page, Store, VersionConflict, now_utc
from app.features.analysis.prompts import PROMPT_VERSION
from app.features.analysis.schemas import AI_FIELDS, content_hash
from app.features.materials.schemas import CONTENT_FIELDS, LIMITS
from app.features.materials.url_keys import url_index_id, url_key  # noqa: F401  (url_key: 기존 import 호환)
from app.features.projects import service as projects

COLLECTION = "materials"
INTAKE = "intake_records"
URL_INDEX = "url_index"
SEOUL = timezone(timedelta(hours=9))
TEXT_FIELDS = ("title", "description", "body", "save_reason", "memo")
EDITABLE = TEXT_FIELDS + ("primary_project_id", "related_project_ids", "user_importance", "ai_excluded")
PUBLIC_FIELDS = (
    "id", "source_type", "url", "title", "description", "body", "save_reason", "memo",
    "primary_project_id", "related_project_ids", "user_importance", "review_status",
    "review_requested", "review_requested_at", "analysis_status", "copy_status",
    "lifecycle", "ai_excluded", "revisit_on", "registered_at", "storage_approved_at", "trashed_at",
    "version", "created_at", "updated_at",
    # 분석(T04.02). AI 제안값은 사용자 최종값과 다른 `ai_` 필드다.
    "analysis_error", "analysis_started_at", "analysis_deadline_at", "analysis_finished_at", *AI_FIELDS,
)
# 목록 보기(T03.03, docs/api-contract.md). 받은 자료와 승인 요청 목록은 겹치지 않는다.
# 같음 조건만 쓰므로 두 보기가 같은 복합 색인을 쓴다(firestore.indexes.json).
VIEWS = {
    "all": None,
    "inbox": {"lifecycle": "active", "review_requested": False, "review_status": "unreviewed"},
    "review": {"lifecycle": "active", "review_requested": True, "review_status": "unreviewed"},
    # 나중에 보기(T03.04). 다시 볼 날짜가 지나도 상태는 그대로이며 `revisit_due`로만 표시한다.
    "later": {"lifecycle": "active", "review_requested": False, "review_status": "later"},
}
DUPLICATE_FIELDS = ("id", "display_title", "title_source", "registered_at", "review_status",
                    "analysis_status", "lifecycle", "version")


class InvalidProjectReference(NoChange):
    """연결하려는 프로젝트가 없거나 비활성이다(422)."""


class NoContent(NoChange):
    """수정 결과 URL과 제목·설명·본문이 모두 비게 된다(422)."""


class DuplicateUrl(NoChange):
    """같은 URL의 자료가 이미 있다(409). existing: 화면에 보여줄 기존 자료 요약."""

    def __init__(self, existing: list[dict]):
        super().__init__("duplicate_url")
        self.existing = existing


class InvalidDuplicateTarget(NoChange):
    """메모를 더할 대상이 없거나 같은 URL의 자료가 아니다(422)."""


class MissingSeparateTarget(NoChange):
    """별도 저장을 골랐지만 같은 URL의 기존 자료가 없다(422)."""


class TrashedTarget(NoChange):
    """휴지통에 있는 자료에는 메모를 더할 수 없다(409, 복원 후 가능)."""


class MemoTooLong(NoChange):
    """덧붙인 뒤 메모가 한도를 넘는다(422)."""


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


def today_seoul() -> str:
    return datetime.now(SEOUL).date().isoformat()


def revisit_due(doc: dict, today: str | None = None) -> bool:
    """나중에 보기 자료의 다시 볼 날짜가 오늘(서울)이거나 지났는가. 저장하지 않고 볼 때마다 계산한다.

    날짜가 지나도 승인·삭제·상태 변경을 하지 않는다(PRD §8). 화면이 정리 후보로 표시할 뿐이다.
    """
    revisit_on = doc.get("revisit_on")
    return (doc.get("review_status") == "later" and isinstance(revisit_on, str)
            and revisit_on <= (today or today_seoul()))


def analysis_stale(doc: dict, now: datetime | None = None) -> bool:
    """분석 중으로 남았지만 기한이 지났다(서버 재시작 등으로 작업이 사라졌을 수 있다). 볼 때마다 계산한다.

    결과 확인 필요로 표시하고 사용자가 다시 시작하게 한다. 저절로 다시 호출하지 않는다(T04.02).
    """
    deadline = doc.get("analysis_deadline_at")
    return (doc.get("analysis_status") == "analyzing" and isinstance(deadline, str)
            and datetime.fromisoformat(deadline) < (now or datetime.now(timezone.utc)))


def analysis_prompt_outdated(doc: dict) -> bool:
    """완료된 결과가 이전 분석 기준(프롬프트·출력 계약)으로 만들어졌다. 결과는 계속 쓰되 '다시 분석 가능'으로 알린다.

    자동으로 다시 호출하지 않는다. 사용자가 시작하면 입력 지문의 버전이 달라 새 분석이 된다(T04.04 코드 리뷰).
    """
    return doc.get("analysis_status") == "done" and doc.get("analysis_prompt_version") != PROMPT_VERSION


def analysis_outdated(doc: dict) -> bool:
    """저장된 AI 결과가 지금 내용 기준이 아니다(결과 뒤에 내용을 고쳤다). 화면은 '다시 분석 필요'로 표시한다."""
    return bool(doc.get("ai_content_hash")) and doc["ai_content_hash"] != content_hash(doc)


def public(doc: dict) -> dict:
    out = {field: doc.get(field) for field in PUBLIC_FIELDS}
    out["ai_excluded"] = bool(doc.get("ai_excluded"))
    out["display_title"], out["title_source"] = display_title(doc)
    out["revisit_due"] = revisit_due(doc)
    out["analysis_stale"] = analysis_stale(doc)
    out["analysis_outdated"] = analysis_outdated(doc)
    out["analysis_prompt_outdated"] = analysis_prompt_outdated(doc)
    return out


def _check_projects(store: Store, ctx: RequestContext, primary: str | None, related: list[str] | None) -> None:
    for project_id in ([primary] if primary else []) + list(related or []):
        if projects.get_active(store, ctx, project_id) is None:
            raise InvalidProjectReference()


def _same_url(store: Store, ctx: RequestContext, key: str) -> list[dict]:
    return store.find(ctx, COLLECTION, "url_key", key, limit=10)


def _summaries(docs: list[dict]) -> list[dict]:
    return [{k: v for k, v in public(d).items() if k in DUPLICATE_FIELDS} for d in docs]


def _new_material_doc(data: dict[str, Any], now: str) -> dict:
    url = data.get("url")
    fields = {name: data.get(name) or "" for name in TEXT_FIELDS}
    return {
        "source_type": "url" if url else "text",
        "url": url,
        "url_key": url_key(url) if url else None,
        **fields,
        "primary_project_id": data.get("primary_project_id"),
        "related_project_ids": data.get("related_project_ids") or [],
        "user_importance": data.get("user_importance"),
        "review_status": "unreviewed",
        "review_requested": False,  # '검토로 이동'하면 True(승인 요청 목록). 검토 상태와는 별도 축이다.
        "review_requested_at": None,
        "analysis_status": "awaiting_start" if _has_content(fields) else "link_only",
        "copy_status": "not_applicable",  # 웹 자료는 원본 사본이 없다(확장 단계 파일만 해당)
        "lifecycle": "active",
        "ai_excluded": bool(data.get("ai_excluded")),
        "revisit_on": None,  # 나중에 보기의 다시 볼 날짜(YYYY-MM-DD, 서울 기준)
        "registered_at": now,
        "storage_approved_at": None,
        "trashed_at": None,
    }


def _insert(store: Store, ctx: RequestContext, doc: dict, reserve_key: str | None) -> dict:
    """자료 + 접수 기록(+ 처음 등록이면 URL 예약)을 한 번에 만든다. 예약 충돌이면 VersionConflict."""
    material_id = uuid.uuid4().hex
    items = [
        (COLLECTION, doc, material_id),
        (INTAKE, {"material_id": material_id, "received_at": doc["registered_at"]}, material_id),
    ]
    if reserve_key:
        items.append((URL_INDEX, {"url_key": reserve_key, "material_id": material_id},
                      url_index_id(ctx.owner_id, ctx.mode, reserve_key)))
    return store.create_many(ctx, items)[0]


def _create_first(store: Store, ctx: RequestContext, doc: dict, key: str) -> dict:
    for _ in range(2):
        existing = _same_url(store, ctx, key)
        if existing:
            raise DuplicateUrl(_summaries(existing))
        try:
            return _insert(store, ctx, doc, key)
        except VersionConflict:
            # 동시에 같은 URL이 먼저 예약됐다. 자료가 보이면 중복으로 알리고,
            # 예약만 남아 있으면(가리키는 자료가 영구 삭제됨) 예약을 지우고 한 번 다시 시도한다.
            existing = _same_url(store, ctx, key)
            if existing:
                raise DuplicateUrl(_summaries(existing)) from None
            try:
                store.delete(ctx, URL_INDEX, url_index_id(ctx.owner_id, ctx.mode, key))
            except NotFound:
                pass
    raise DuplicateUrl(_summaries(_same_url(store, ctx, key)))


def _add_memo(store: Store, ctx: RequestContext, key: str, data: dict[str, Any]) -> dict:
    try:
        target = store.get(ctx, COLLECTION, data["target_id"])
    except NotFound:
        raise InvalidDuplicateTarget() from None
    if target.get("url_key") != key:
        raise InvalidDuplicateTarget()
    if target.get("lifecycle") != "active":
        raise TrashedTarget()
    stamp = datetime.now(SEOUL).date().isoformat()
    line = f"[{stamp} 추가] {data['memo']}"
    memo = f"{target['memo']}\n\n{line}" if target.get("memo") else line
    if len(memo) > LIMITS["memo"]:
        raise MemoTooLong()
    # 기존 본문·설명은 그대로 둔다. 메모만 덧붙이며 새 접수 기록은 만들지 않는다.
    return store.update(ctx, COLLECTION, target["id"], data["target_version"], {"memo": memo})


def create_material(store: Store, ctx: RequestContext, data: dict[str, Any]) -> tuple[int, dict]:
    """(HTTP 상태, 응답 본문). 새 자료는 201, 기존 자료에 메모를 더하면 200."""
    action = data.get("duplicate_action")
    url = data.get("url")
    key = url_key(url) if url else None
    if action == "add_memo":
        updated = _add_memo(store, ctx, key, data)
        return 200, {**public(updated), "duplicate_action": "add_memo"}

    _check_projects(store, ctx, data.get("primary_project_id"), data.get("related_project_ids"))
    doc = _new_material_doc(data, now_utc())
    if not key:
        return 201, public(_insert(store, ctx, doc, None))
    if action == "save_separately":
        # 첫 접수에 이 값을 직접 보내 예약을 건너뛰지 못하게 한다.
        if not _same_url(store, ctx, key):
            raise MissingSeparateTarget()
        return 201, {**public(_insert(store, ctx, doc, None)), "duplicate_action": "save_separately"}
    return 201, public(_create_first(store, ctx, doc, key))


def is_kept(doc: dict) -> bool:
    """보관 완료 판정(T03.03). 웹 자료는 보관 승인과 동시에 보관 완료다(PRD §9.1).

    T03.04·T05(보관함)·T07(채팅 대상)·보관 건수 집계가 이 조건을 함께 쓴다.
    """
    return (doc.get("review_status") == "approved" and doc.get("copy_status") == "not_applicable"
            and doc.get("lifecycle") == "active")


def ai_allowed(doc: dict) -> bool:
    """자료 내용을 AI Provider에 보내도 되는가(T04 분석·T07 채팅이 보내기 직전에 확인한다)."""
    return not doc.get("ai_excluded")


def chat_eligible(doc: dict) -> bool:
    """채팅 근거로 쓸 수 있는가(PRD §9.1: 보관 승인·보관 완료·활성, A13).

    AI 분석 제외 자료는 Open Decision 5가 정해지기 전까지 제목 같은 메타데이터도 쓰지 않는다(엄격한 쪽).
    소유자·모드 일치는 저장소가 보장한다.
    """
    return is_kept(doc) and ai_allowed(doc)


def list_materials(store: Store, ctx: RequestContext, limit: int = 20, cursor: str | None = None,
                   view: str = "all") -> dict:
    page: Page = store.list(ctx, COLLECTION, limit=limit, cursor=cursor, descending=True, where=VIEWS[view])
    return {"items": [public(d) for d in page.items], "next_cursor": page.next_cursor}


def get_material(store: Store, ctx: RequestContext, material_id: str) -> dict:
    return public(store.get(ctx, COLLECTION, material_id))


def update_material(store: Store, ctx: RequestContext, material_id: str, expected_version: int,
                    changes: dict[str, Any]) -> dict:
    current = store.get(ctx, COLLECTION, material_id)  # 남의 자료·없는 자료는 404
    changes = prepare_changes(store, ctx, current, changes)
    return public(store.update(ctx, COLLECTION, material_id, expected_version, changes))


def prepare_changes(store: Store, ctx: RequestContext, current: dict, changes: dict[str, Any]) -> dict:
    """사용자 수정값을 검사·정리한다(수정 API와 보관 승인이 함께 쓴다). 쓰지는 않는다.

    프로젝트가 없거나 비활성이면 InvalidProjectReference, 내용이 모두 비게 되면 NoContent.
    """
    changes = {k: v for k, v in changes.items() if k in EDITABLE}
    if changes.get("ai_excluded", False) is None:
        del changes["ai_excluded"]  # 켜고 끄는 값이라 비울 수 없다. null은 '바꾸지 않음'으로 본다.
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
            "link_only", "awaiting_start", "failed"):
        # 분석 전·실패 자료는 내용에 맞춰 상태만 맞춘다. 완료 자료는 상태를 두고 `analysis_outdated`로 알리며,
        # 분석 중인 자료는 작업이 끝날 때 내용 변경을 확인해 결과를 버린다(T04.02).
        changes["analysis_status"] = "awaiting_start" if _has_content(merged) else "link_only"
        changes["analysis_error"] = None
    return changes
