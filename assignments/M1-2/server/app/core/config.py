"""서버 설정을 환경변수에서 읽는다.

로컬에서는 `assignments/M1-2/.env`를, 배포(Render)에서는 서비스 환경변수를 쓴다.
키가 없어도 서버는 켜진다. 어떤 설정이 비었는지는 `missing()`으로 알리고,
키가 필요한 기능이 호출될 때 그 기능이 오류를 낸다. 값은 어디에도 출력하지 않는다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

# server/app/core/config.py → parents[3] = assignments/M1-2
M1_2_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = M1_2_ROOT / ".env"

# PRD §14 [초기 가설] — 실제 Provider 제한을 확인한 뒤 환경변수로 조정한다.
DEFAULT_AI_DAILY_REQUEST_LIMIT = 50
DEFAULT_AI_MAX_OUTPUT_TOKENS = 1500
DEFAULT_AI_TIMEOUT_SECONDS = 60

# 기능 묶음별로 반드시 있어야 하는 변수. /health와 기능별 오류에서 함께 쓴다.
REQUIRED = {
    "ai": ("OPENAI_API_KEY", "AI_PROVIDER_BASE_URL", "AI_PROVIDER_MODEL", "AI_PROVIDER_ROUTE"),
    "firebase": ("FIREBASE_SERVICE_ACCOUNT_JSON", "OWNER_UID"),
}
OPTIONAL = ("HERMES_RELAY_TOKEN",)


class ConfigError(ValueError):
    """설정 값의 형식이 잘못되었다. 메시지에는 변수 이름만 담는다."""


@dataclass(frozen=True)
class Settings:
    values: Mapping[str, str]
    allowed_origins: tuple[str, ...]
    ai_daily_request_limit: int
    ai_max_output_tokens: int
    ai_timeout_seconds: int

    def get(self, name: str) -> str:
        return self.values.get(name, "")

    def missing(self) -> dict[str, list[str]]:
        """묶음별로 비어 있는 변수 이름. 모두 채워졌으면 빈 목록이다."""
        return {group: [n for n in names if not self.get(n)] for group, names in REQUIRED.items()}

    def require(self, group: str) -> None:
        """키가 필요한 기능의 입구에서 부른다. 누락과 Provider 호출 실패를 구분하기 위해서다."""
        absent = self.missing()[group]
        if absent:
            raise ConfigError(f"{group} 설정 누락: {', '.join(absent)}")


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        value = -1
    if value <= 0:
        raise ConfigError(f"{name}은 양의 정수여야 합니다")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """env를 넘기면 그 값만 쓴다(테스트용). 없으면 .env를 읽은 뒤 os.environ을 쓴다.

    이미 설정된 환경변수가 .env보다 우선한다(배포 환경변수를 로컬 파일이 덮지 않게).
    """
    if env is None:
        load_dotenv(ENV_FILE, override=False)
        env = os.environ
    names = [n for group in REQUIRED.values() for n in group] + list(OPTIONAL)
    values = {n: env.get(n, "").strip() for n in names}
    origins = tuple(o.strip() for o in env.get("ALLOWED_ORIGINS", "").split(",") if o.strip())
    return Settings(
        values=values,
        allowed_origins=origins,
        ai_daily_request_limit=_positive_int(env, "AI_DAILY_REQUEST_LIMIT", DEFAULT_AI_DAILY_REQUEST_LIMIT),
        ai_max_output_tokens=_positive_int(env, "AI_MAX_OUTPUT_TOKENS", DEFAULT_AI_MAX_OUTPUT_TOKENS),
        ai_timeout_seconds=_positive_int(env, "AI_TIMEOUT_SECONDS", DEFAULT_AI_TIMEOUT_SECONDS),
    )
