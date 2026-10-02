"""검토·승인 API. `POST /api/reviews/approve`는 PRD §13, `POST /api/reviews/request`는 PRD 외 추가(T03.03)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_context
from app.core.context import RequestContext
from app.core.deps import get_store
from app.core.firestore import Store
from app.core.requests import Result, run_idempotent
from app.features.reviews import service
from app.features.reviews.schemas import ApproveRequest, ReviewRequestBody

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("/approve")
def approve(body: ApproveRequest, ctx: RequestContext = Depends(get_context),
            store: Store = Depends(get_store)) -> dict:
    # 보낸 changes 필드만 바꾼다. 항목별 결과는 일부가 충돌해도 200으로 돌려준다.
    payload = body.model_dump(exclude_unset=True)
    return run_idempotent(store, ctx, "POST", "/api/reviews/approve", payload,
                          lambda: Result(200, service.approve(store, ctx, payload["items"]))).body


@router.post("/request")
def request_review(body: ReviewRequestBody, ctx: RequestContext = Depends(get_context),
                   store: Store = Depends(get_store)) -> dict:
    payload = body.model_dump()
    return run_idempotent(
        store, ctx, "POST", "/api/reviews/request", payload,
        lambda: Result(200, service.request_review(store, ctx, payload["items"], payload["requested"])),
    ).body
