"""자료 입력 검증(PRD §6.1).

길이 한도는 여기 한곳에서 관리한다. 넘치면 잘라서 저장하지 않고 422로 알린다.
저장 이유(`save_reason`)는 메모와 별도 필드다(Open Decision 2).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.features.materials.url_keys import check_url

# PRD §6.1 권장 길이. 저장 이유는 설명·메모와 같은 2,000자(Open Decision 2).
LIMITS = {
    "url": 2048,
    "title": 200,
    "description": 2000,
    "body": 20000,
    "save_reason": 2000,
    "memo": 2000,
}
MAX_RELATED_PROJECTS = 20
CONTENT_FIELDS = ("title", "description", "body")


class _Fields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(None, max_length=LIMITS["title"])
    description: str | None = Field(None, max_length=LIMITS["description"])
    body: str | None = Field(None, max_length=LIMITS["body"])
    save_reason: str | None = Field(None, max_length=LIMITS["save_reason"])
    memo: str | None = Field(None, max_length=LIMITS["memo"])
    primary_project_id: str | None = None
    related_project_ids: list[str] | None = Field(None, max_length=MAX_RELATED_PROJECTS)

    @field_validator("related_project_ids")
    @classmethod
    def unique_related(cls, ids):
        if ids is None:
            return ids
        cleaned = [i.strip() for i in ids if i and i.strip()]
        return list(dict.fromkeys(cleaned))


class MaterialCreate(_Fields):
    url: str | None = Field(None, max_length=LIMITS["url"])
    # 같은 URL 안내(409) 뒤 사용자의 선택(T03.02). 처음 접수할 때는 보내지 않는다.
    duplicate_action: Literal["save_separately", "add_memo"] | None = None
    target_id: str | None = None
    target_version: int | None = Field(None, ge=1)

    @field_validator("url")
    @classmethod
    def valid_url(cls, value):
        return check_url(value) if value else None

    @model_validator(mode="after")
    def has_content(self):
        if self.duplicate_action is not None and not self.url:
            raise ValueError("같은 URL 선택은 URL이 있는 접수에서만 쓸 수 있습니다")
        if self.duplicate_action == "add_memo":
            if not (self.target_id and self.target_version and self.memo):
                raise ValueError("메모 추가에는 대상 자료·버전과 메모가 필요합니다")
            return self
        # URL 또는 제목·설명·본문 중 하나 이상(PRD §6.1). 저장 이유·메모만으로는 자료가 아니다.
        if not self.url and not any(getattr(self, f) for f in CONTENT_FIELDS):
            raise ValueError("URL 또는 제목·설명·본문 중 하나 이상을 입력하세요")
        return self


class MaterialUpdate(_Fields):
    """원래 URL은 출처이므로 고칠 수 없다(url 필드를 보내면 422)."""

    expected_version: int = Field(ge=1)
