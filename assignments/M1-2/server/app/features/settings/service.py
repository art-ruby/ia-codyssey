"""사용자 설정: 관심 분야·활동 분야·기본 프로젝트(PRD §1, §9.2 '사용자 설정').

- 소유자·모드마다 문서 하나다. 표본 모드는 표본 설정을 따로 가진다.
- 저장한 적이 없으면 저장하지 않은 기본값을 `saved=False`, `version=0`으로 돌려준다.
  개인 모드 기본값은 PRD §1의 관심·활동 분야다. 처음 저장할 때 expected_version=0을 보낸다.
- 현재 자료 모드는 서버에 저장하지 않는다. 요청마다 `X-Data-Mode`가 기준이고(docs/decisions.md),
  마지막 사용 모드는 브라우저가 기억한다.
"""
from __future__ import annotations

from app.core.context import RequestContext
from app.core.firestore import NotFound, Store
from app.features.projects.atomic import InvalidDefaultProject, save_settings, settings_id

COLLECTION = "settings"

PERSONAL_DEFAULTS = {
    "interests": ["AI Agent·Memory·협업", "자동화", "개발 도구·API", "콘텐츠 생성", "모델·서비스·가격·정책 변화"],
    "activities": ["프로그램 개발", "업무 자동화", "콘텐츠 제작", "학습·연구", "사업 기획"],
    "default_project_id": None,
}
SAMPLE_DEFAULTS = {"interests": [], "activities": [], "default_project_id": None}


def _public(doc: dict, saved: bool) -> dict:
    return {
        "interests": list(doc.get("interests", [])),
        "activities": list(doc.get("activities", [])),
        "default_project_id": doc.get("default_project_id"),
        "version": doc.get("version", 0),
        "saved": saved,
    }


def get_settings(store: Store, ctx: RequestContext) -> dict:
    try:
        return _public(store.get(ctx, COLLECTION, settings_id(ctx)), saved=True)
    except NotFound:
        defaults = PERSONAL_DEFAULTS if ctx.mode == "personal" else SAMPLE_DEFAULTS
        return _public({**defaults, "version": 0}, saved=False)


def put_settings(store: Store, ctx: RequestContext, expected_version: int, interests: list[str],
                 activities: list[str], default_project_id: str | None) -> dict:
    data = {"interests": interests, "activities": activities, "default_project_id": default_project_id}
    doc = save_settings(store, ctx, expected_version, data)
    return _public(doc, saved=True)
