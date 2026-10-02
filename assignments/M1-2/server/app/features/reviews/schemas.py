"""검토·승인 요청 형식(T03.03, PRD §13 `POST /api/reviews/approve`).

요청 전체가 잘못되면(항목 0개·상한 초과·같은 자료 중복·아직 지원하지 않는 작업) 422로 거부한다.
그 밖에는 항목별 결과를 돌려주며, 일부 항목의 충돌로 전체를 실패시키지 않는다.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.features.materials.schemas import LIMITS, MAX_RELATED_PROJECTS, Importance, clean_ids

MAX_BATCH = 50


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class KeepChanges(_Strict):
    """승인하면서 함께 고치는 값. 보낸 필드만 바꾸고, null은 비운다(중요도 null = 판단 보류)."""

    title: str | None = Field(None, max_length=LIMITS["title"])
    user_importance: Importance | None = None
    primary_project_id: str | None = None
    related_project_ids: list[str] | None = Field(None, max_length=MAX_RELATED_PROJECTS)

    @field_validator("related_project_ids")
    @classmethod
    def unique_related(cls, ids):
        return clean_ids(ids)


class ApproveItem(_Strict):
    material_id: str = Field(min_length=1)
    expected_version: int = Field(ge=1)
    # link·trash는 Phase 05에서 같은 API에 붙인다. 요청 형식은 지금과 같다.
    action: Literal["keep", "link", "trash"] = "keep"
    changes: KeepChanges | None = None

    @model_validator(mode="after")
    def supported(self):
        if self.action != "keep":
            raise ValueError("지금은 보관 승인(keep)만 할 수 있습니다. 연결·휴지통 이동은 이후 단계에서 지원합니다")
        return self


class _Batch(_Strict):
    @model_validator(mode="after")
    def unique_ids(self):
        ids = [item.material_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("같은 자료를 한 요청에 두 번 넣을 수 없습니다")
        return self


class ApproveRequest(_Batch):
    items: list[ApproveItem] = Field(min_length=1, max_length=MAX_BATCH)


class RequestItem(_Strict):
    material_id: str = Field(min_length=1)
    expected_version: int = Field(ge=1)


class ReviewRequestBody(_Batch):
    """받은 자료 → 승인 요청 목록(requested=true), 또는 되돌리기(false). PRD 외 추가."""

    items: list[RequestItem] = Field(min_length=1, max_length=MAX_BATCH)
    requested: bool = True


class LaterBody(_Batch):
    """나중에 보기로 남기거나(later=true, 다시 볼 날짜 선택) 미검토로 되돌린다(false). PRD 외 추가(T03.04)."""

    items: list[RequestItem] = Field(min_length=1, max_length=MAX_BATCH)
    later: bool = True
    revisit_on: date | None = None

    @model_validator(mode="after")
    def valid_date(self):
        if not self.later and self.revisit_on is not None:
            raise ValueError("되돌릴 때는 다시 볼 날짜를 보내지 않습니다")
        return self

