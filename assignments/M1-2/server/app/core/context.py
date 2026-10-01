"""인증된 요청의 공통 문맥. 모든 기능은 소유자·모드를 이 객체에서만 얻는다."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

Mode = Literal["personal", "sample"]
MODES: tuple[str, ...] = get_args(Mode)


@dataclass(frozen=True)
class RequestContext:
    # 인증 토큰에서 얻는다. 브라우저가 보낸 owner_id는 신뢰하지 않는다.
    owner_id: str
    # `X-Data-Mode` 헤더. 요청에 담긴 모드가 그 요청의 기준이다.
    mode: Mode
    # `Idempotency-Key` 헤더. 조회 요청에는 없을 수 있다.
    request_id: str | None
