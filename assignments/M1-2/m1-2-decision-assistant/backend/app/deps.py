"""FastAPI 의존성. 라우터가 설정·저장소를 직접 만들지 않게 한다."""
from __future__ import annotations

from .config import Settings, get_settings
from .repositories.store import Store, get_store


def config_dep() -> Settings:
    return get_settings()


def store_dep() -> Store:
    return get_store(get_settings())
