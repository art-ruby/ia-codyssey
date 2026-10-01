"""기능 라우터가 함께 쓰는 FastAPI 의존성."""
from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.core.config import ConfigError
from app.core.firestore import FirestoreStore, Store


def get_store(request: Request) -> Store:
    """저장소 의존성. 첫 사용 때 Firestore에 연결한다(테스트는 create_app(store=...)로 주입)."""
    state = request.app.state
    if state.store is None:
        try:
            state.store = FirestoreStore.from_settings(state.settings)
        except ConfigError as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"저장소 설정 오류: {exc}") from None
    return state.store
