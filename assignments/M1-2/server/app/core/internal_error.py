"""처리되지 않은 예외를 CORS 안쪽에서 JSON 500으로 바꾼다.

Starlette 기본 500 응답은 CORS 미들웨어 바깥에서 만들어져 허용 헤더가 없다. 브라우저는 그 응답을 읽지 못해
"서버에 연결하지 못했습니다"로 보여 준다. 응답을 시작하기 전의 예외만 바꾸고, traceback은 로그에 남긴다.
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger("ai_secretary.error")
BODY = json.dumps({"detail": "서버에서 오류가 났습니다. 잠시 뒤 다시 시도하세요", "reason": "internal_error"},
                  ensure_ascii=False).encode("utf-8")


class InternalErrorJSON:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:
            log.exception("unhandled error %s %s", scope.get("method"), scope.get("path"))
            if started:
                raise
            await send({"type": "http.response.start", "status": 500,
                        "headers": [(b"content-type", b"application/json"),
                                    (b"content-length", str(len(BODY)).encode("ascii"))]})
            await send({"type": "http.response.body", "body": BODY})
