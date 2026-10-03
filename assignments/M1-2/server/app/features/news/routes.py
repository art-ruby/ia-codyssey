"""새 소식 API(설계 §7). 모두 로그인·소유자 확인을 거치고 개인 모드에서만 동작한다."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.materials.url_keys import check_url
from app.features.news import service
from app.features.news.sources import NAME_LIMIT

router = APIRouter(prefix="/api/news", tags=["news"])


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=NAME_LIMIT)
    feed_url: str = Field(min_length=1, max_length=2048)

    @field_validator("feed_url")
    @classmethod
    def valid_url(cls, value):
        return check_url(value)


class SourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    expected_version: int = Field(ge=1)


def _request(request: Request):
    # 테스트는 app.state.news_request에 가짜 요청 함수를 넣어 외부에 접속하지 않는다.
    return getattr(request.app.state, "news_request", None)


def _view(request: Request, background: BackgroundTasks, ctx: RequestContext, store: Store,
          manual: bool, cursor: str | None) -> dict:
    service.require_personal(ctx)
    started = service.claim_refresh(store, ctx, manual=manual)
    if started:
        background.add_task(service.run_refresh, store, ctx, _request(request))
    return service.news_view(store, ctx, cursor, refreshing=started)


@router.get("")
def news(request: Request, background: BackgroundTasks, cursor: str | None = Query(None, max_length=10),
         ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    """저장된 새 소식. 수집할 때가 됐으면 뒤에서 수집을 시작하고 `state.refreshing`을 참으로 돌려준다."""
    return _view(request, background, ctx, store, manual=False, cursor=cursor)


@router.post("/refresh")
def refresh(request: Request, background: BackgroundTasks, ctx: RequestContext = Depends(get_context),
            store: Store = Depends(get_store)) -> dict:
    """지금 새로고침. 수집 중이거나 5분 안에 시도했으면 수집하지 않고 현재 목록만 돌려준다."""
    return _view(request, background, ctx, store, manual=True, cursor=None)


@router.get("/sources")
def sources(ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    return service.list_sources(store, ctx)


@router.post("/sources", status_code=201)
def add_source(body: SourceCreate, request: Request, ctx: RequestContext = Depends(get_context),
               store: Store = Depends(get_store)) -> dict:
    service.require_personal(ctx)
    return run_idempotent(store, ctx, "POST", "/api/news/sources", body.model_dump(), lambda: Result(
        201, service.add_source(store, ctx, body.name, body.feed_url, _request(request)))).body


@router.put("/sources/{source_id}")
def update_source(source_id: str, body: SourceUpdate, ctx: RequestContext = Depends(get_context),
                  store: Store = Depends(get_store)) -> dict:
    service.require_personal(ctx)
    return run_idempotent(store, ctx, "PUT", f"/api/news/sources/{source_id}", body.model_dump(), lambda: Result(
        200, service.set_source_enabled(store, ctx, source_id, body.expected_version, body.enabled))).body


@router.delete("/sources/{source_id}")
def delete_source(source_id: str, ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    service.require_personal(ctx)
    return run_idempotent(store, ctx, "DELETE", f"/api/news/sources/{source_id}", {}, lambda: Result(
        200, service.delete_source(store, ctx, source_id))).body


@router.post("/{news_id}/save")
def save(news_id: str, ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    """받은 자료로 저장. 같은 URL 자료가 있으면 연결만 하고 `created: false`."""
    service.require_personal(ctx)
    return run_idempotent(store, ctx, "POST", f"/api/news/{news_id}/save", {}, lambda: Result(
        200, service.save_item(store, ctx, news_id))).body


@router.post("/{news_id}/hide")
def hide(news_id: str, ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    service.require_personal(ctx)
    return run_idempotent(store, ctx, "POST", f"/api/news/{news_id}/hide", {}, lambda: Result(
        200, service.set_hidden(store, ctx, news_id, True))).body


@router.post("/{news_id}/unhide")
def unhide(news_id: str, ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    service.require_personal(ctx)
    return run_idempotent(store, ctx, "POST", f"/api/news/{news_id}/unhide", {}, lambda: Result(
        200, service.set_hidden(store, ctx, news_id, False))).body
