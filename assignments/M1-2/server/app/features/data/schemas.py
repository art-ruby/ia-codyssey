"""숫자 기록 입력 검증(T06.01, PRD §11.1).

값은 0 이상 정수만 받는다. 소수(2.0 포함)·문자열·참거짓은 422다. 날짜는 실제로 있는 `YYYY-MM-DD`만 받는다.
출처(`origin`)는 모드에서 정하므로 요청으로 보낼 수 없다(개인=manual, 표본=sample).
"""
from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

Metric = Literal["received_count", "kept_count"]
MIN_DATE, MAX_DATE = date(2000, 1, 1), date(2100, 12, 31)
MAX_VALUE = 1_000_000
MEMO_LIMIT = 500
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check_date(value: str) -> str:
    if not isinstance(value, str) or not _DATE.match(value):
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다")
    try:
        day = date.fromisoformat(value)
    except ValueError:
        raise ValueError("존재하지 않는 날짜입니다") from None
    if not MIN_DATE <= day <= MAX_DATE:
        raise ValueError("날짜는 2000-01-01부터 2100-12-31 사이여야 합니다")
    return value


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DataCreate(_Strict):
    date: str
    metric_type: Metric
    value: StrictInt = Field(ge=0, le=MAX_VALUE)
    memo: str = Field("", max_length=MEMO_LIMIT)

    @field_validator("date")
    @classmethod
    def valid_date(cls, v):
        return check_date(v)


class DataUpdate(_Strict):
    """보낸 필드만 바꾼다. 바꿀 필드가 없으면 422. 날짜·지표·값은 비울 수 없고, 메모는 null이면 비운다."""

    expected_version: int = Field(ge=1)
    date: str | None = None
    metric_type: Metric | None = None
    value: StrictInt | None = Field(None, ge=0, le=MAX_VALUE)
    memo: str | None = Field(None, max_length=MEMO_LIMIT)

    @field_validator("date")
    @classmethod
    def valid_date(cls, v):
        return None if v is None else check_date(v)

    @model_validator(mode="after")
    def not_blank(self):
        if not self.model_fields_set - {"expected_version"}:
            raise ValueError("바꿀 필드가 하나 이상 있어야 합니다")  # 빈 PUT으로 버전만 오르지 않게
        for name in ("date", "metric_type", "value"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name}은(는) 비울 수 없습니다")
        return self
