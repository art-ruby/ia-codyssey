"""변경 요청의 중복 처리(`Idempotency-Key`).

규칙(docs/api-contract.md):
- 변경 요청에 키가 없으면 422.
- 같은 키·같은 내용이면 처음 응답을 그대로 돌려준다(작업은 한 번만 실행).
- 같은 키·다른 내용이면 409. 같은 키의 첫 요청이 아직 처리 중이어도 409.
- 키는 소유자 단위다. 내용 비교값에는 모드·메서드·경로·요청 본문을 넣는다.
- 기록은 Firestore `idempotency`에 남아 서버를 다시 시작해도 유지된다. `expire_at`이 지나면 새 요청으로 본다.

처리 중에 서버가 죽으면 기록이 `processing`으로 남아 같은 키는 계속 409다.
실제로 작업이 끝났는지 모르므로 몰래 다시 실행하지 않고, 사용자가 새 키로 다시 요청하게 한다.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.core.context import RequestContext
from app.core.firestore import Store

IDEMPOTENCY_TTL = timedelta(days=1)
MAX_KEY_LENGTH = 200


class IdempotencyKeyRequired(Exception):
    """변경 요청에 `Idempotency-Key`가 없거나 형식이 틀렸다(422)."""


class IdempotencyConflict(Exception):
    """같은 키로 다른 내용을 보냈거나(`different_request`), 첫 요청이 처리 중이다(`in_progress`). 409."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Result:
    status_code: int
    body: Any
    replayed: bool = False


def fingerprint(ctx: RequestContext, method: str, path: str, body: Any) -> str:
    raw = json.dumps(
        {"mode": ctx.mode, "method": method.upper(), "path": path, "body": body},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def record_id(owner_id: str, key: str) -> str:
    # 클라이언트가 고른 키를 문서 ID로 쓰지 않는다(허용 문자·길이 문제, 소유자 간 충돌 방지).
    return hashlib.sha256(f"{owner_id}\n{key}".encode()).hexdigest()


def run_idempotent(store: Store, ctx: RequestContext, method: str, path: str, body: Any,
                   handler: Callable[[], Result], now: Callable[[], datetime] | None = None) -> Result:
    """handler(실제 변경 작업)를 같은 키에 대해 한 번만 실행한다.

    handler가 예외를 내면 기록을 지워 같은 키로 다시 시도할 수 있게 한다
    (검증 실패 등은 아무것도 바꾸지 않았기 때문이다). AI 호출처럼 비용이 드는 작업은
    handler 안에서 트랜잭션 밖에 둔다.
    """
    key = (ctx.request_id or "").strip()
    if not key or len(key) > MAX_KEY_LENGTH:
        raise IdempotencyKeyRequired()

    clock = now or (lambda: datetime.now(timezone.utc))
    current = clock()
    fp = fingerprint(ctx, method, path, body)
    rid = record_id(ctx.owner_id, key)
    record = {
        "owner_id": ctx.owner_id,
        "fingerprint": fp,
        "state": "processing",
        "created_at": current.isoformat(),
        "expire_at": (current + IDEMPOTENCY_TTL).isoformat(),
    }

    # 만료된 기록은 저장소가 같은 원자적 단계에서 새 요청으로 덮어쓴다.
    existing = store.claim_key(rid, record, current.isoformat())
    if existing is not None:
        if existing.get("fingerprint") != fp:
            raise IdempotencyConflict("different_request")
        if existing.get("state") == "done":
            return Result(existing["status_code"], existing["body"], replayed=True)
        raise IdempotencyConflict("in_progress")

    try:
        result = handler()
    except BaseException:
        store.release_key(rid)
        raise
    store.finish_key(rid, {
        "state": "done",
        "status_code": result.status_code,
        "body": result.body,
        "finished_at": clock().isoformat(),
    })
    return result
