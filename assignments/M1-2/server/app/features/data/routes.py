"""숫자 기록 API (PRD §13: POST/GET /api/data, GET/PUT/DELETE /api/data/{id}). T06.01.

`GET /api/data/summary`(T06.02)는 `/{record_id}`보다 먼저 등록해야 'summary'가 기록 ID로 해석되지 않는다.
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
from app.features.data import service, summary
from app.features.data.schemas import DataCreate, DataUpdate, Metric, check_date

router = APIRouter(prefix="/api/data", tags=["data"])
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"


def _check_range(date_from: str | None, date_to: str | None) -> None:
    for value in (date_from, date_to):
        if value:
            try:
                check_date(value)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
    if date_from and date_to and date.fromisoformat(date_from) > date.fromisoformat(date_to):
        raise HTTPException(422, "시작 날짜가 끝 날짜보다 늦습니다")


@router.post("", status_code=201)
def create_record(body: DataCreate, ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)):
    payload = body.model_dump()
    result = run_idempotent(store, ctx, "POST", "/api/data", payload,
                            lambda: Result(201, service.create_record(store, ctx, payload)))
    return JSONResponse(result.body, status_code=result.status_code)


@router.get("")
def list_records(metric_type: Metric | None = None,
                 date_from: str | None = Query(None, pattern=DATE_PATTERN),
                 date_to: str | None = Query(None, pattern=DATE_PATTERN),
                 limit: int = Query(50, ge=1, le=100), cursor: str | None = None,
                 ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    _check_range(date_from, date_to)
    return service.list_records(store, ctx, metric_type, date_from, date_to, limit, cursor)


@router.get("/summary")
def summary_view(source: Literal["actual", "manual", "sample"] | None = None,
                 metric_type: Literal["received_count", "kept_count", "all"] = "kept_count",
                 start_date: str | None = Query(None, pattern=DATE_PATTERN),
                 end_date: str | None = Query(None, pattern=DATE_PATTERN),
                 ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    """PRD §11.2. `/{record_id}`보다 먼저 등록해 'summary'가 기록 ID로 해석되지 않게 한다(T06.02)."""
    _check_range(start_date, end_date)
    return summary.summarize_data(store, ctx, source, metric_type, start_date, end_date)


@router.get("/{record_id}")
def get_record(record_id: str, ctx: RequestContext = Depends(get_context), store: Store = Depends(get_store)) -> dict:
    return service.get_record(store, ctx, record_id)


@router.put("/{record_id}")
def update_record(record_id: str, body: DataUpdate, ctx: RequestContext = Depends(get_context),
                  store: Store = Depends(get_store)) -> dict:
    payload = body.model_dump(exclude_unset=True)
    changes = {k: v for k, v in payload.items() if k != "expected_version"}
    return run_idempotent(store, ctx, "PUT", f"/api/data/{record_id}", payload, lambda: Result(
        200, service.update_record(store, ctx, record_id, body.expected_version, changes))).body


@router.delete("/{record_id}")
def delete_record(record_id: str, expected_version: int = Query(ge=1), ctx: RequestContext = Depends(get_context),
                  store: Store = Depends(get_store)) -> dict:
    payload = {"expected_version": expected_version}
    return run_idempotent(store, ctx, "DELETE", f"/api/data/{record_id}", payload, lambda: Result(
        200, service.delete_record(store, ctx, record_id, expected_version))).body
