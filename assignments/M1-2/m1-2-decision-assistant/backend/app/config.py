"""환경 변수 한 곳. 키를 코드에 박지 않는다(과제 7절 제약).

Firestore 자격증명이나 OpenAI 키가 없어도 서버는 뜬다. 대신 어떤 모드로
떠 있는지를 /api/health 와 기동 로그가 분명히 말한다 — '키가 없어서 조용히
가짜 응답을 준다'가 가장 나쁜 상태이기 때문이다.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")


class Settings:
    def __init__(self) -> None:
        # 개발·채점용 진단 경로를 열지 여부. 기본은 꺼짐이다.
        # system prompt 전문을 돌려주는 /api/chat/preview 가 이 값에 걸려 있어,
        # 배포에서 켜면 내부 지시문과 데이터가 그대로 공개된다.
        self.debug: bool = os.getenv("DEBUG", "").strip().lower() in ("1", "true", "yes", "on")

        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
        # OpenAI 호환 프록시를 쓸 수 있게 한다. 과정에서 제공하는
        # Codyssey 게이트웨이(https://copa.codyssey.kr/v1)가 그 경우다.
        # 비워 두면 SDK 기본값(api.openai.com)으로 간다 — virtual-key 는
        # 거기서 401 이 나므로 프록시를 쓸 때는 반드시 지정해야 한다.
        self.openai_base_url: str = os.getenv("OPENAI_BASE_URL", "").strip()
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()
        # 과제 7절: 개발 중 토큰 상한을 둔다.
        self.openai_max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "800"))

        self.firebase_service_account_json: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        self.firestore_collection_data: str = os.getenv("FIRESTORE_COLLECTION_DATA", "data")
        self.firestore_collection_conversations: str = os.getenv(
            "FIRESTORE_COLLECTION_CONVERSATIONS", "conversations"
        )

        raw_origins = os.getenv("ALLOWED_ORIGINS", "*").strip()
        self.allowed_origins: list[str] = (
            ["*"] if raw_origins == "*" else [o.strip() for o in raw_origins.split(",") if o.strip()]
        )

        # 인계는 RADAR automaker_intake 를 부른다(DA 자체 handoff 파일은 폐기 — 읽는 쪽이 없었다).
        self.automaker_url: str = os.getenv("AUTOMAKER_URL", "http://127.0.0.1:5300").strip()
        # RADAR 코드를 돌릴 인터프리터. RADAR.cmd 가 쓰는 것과 같아야 한다(pandas 등).
        self.radar_python: str = os.getenv("RADAR_PYTHON", "python").strip() or "python"
        self.sample_data_path: Path = Path(
            os.getenv("SAMPLE_DATA_PATH", str(PROJECT_DIR / "sample_data" / "candidates.json"))
        )
        # 실제 RADAR 저장소. 없으면 sample 어댑터만 쓴다. 읽기 전용으로만 접근한다.
        self.radar_root: str = os.getenv("RADAR_ROOT", "").strip()
        # 예외 하나: 결정은 RADAR data/decisions.jsonl 에 쓴다(단일 정본). 그 외는 여전히 읽기 전용.
        # 명시적으로 켜야만 쓴다 — 남의 저장소에 조용히 쓰지 않는다.
        self.radar_decisions_write: bool = (
            os.getenv("RADAR_DECISIONS_WRITE", "").strip().lower() in ("1", "true", "yes")
        )

    @property
    def firestore_enabled(self) -> bool:
        return bool(self.firebase_service_account_json)

    @property
    def openai_enabled(self) -> bool:
        return bool(self.openai_api_key)

    def mode_banner(self) -> str:
        store = "Firestore" if self.firestore_enabled else "in-memory (개발용, 재시작 시 소멸)"
        if self.openai_enabled:
            where = self.openai_base_url or "api.openai.com (기본)"
            brain = f"{self.openai_model} @ {where}"
        else:
            brain = "규칙 기반 응답(키 없음)"
        return f"store={store} | chat={brain}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
