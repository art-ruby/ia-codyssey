"""요청 본문 전체 크기 제한.

필드별 길이 제한(schemas.py)은 본문을 모두 읽은 뒤에야 적용되므로, 아주 큰 본문이 메모리를 먼저 차지하지 못하게
ASGI 단계에서 막는다. Content-Length가 없는 분할 전송도 읽은 바이트를 세어 끊는다.
"""
from __future__ import annotations

import json

# 자료 본문 2만 자(한글 3바이트 기준 약 60KB)와 나머지 필드를 합쳐도 여유가 있는 값.
MAX_REQUEST_BYTES = 256 * 1024


class _BodyTooLarge(Exception):
    pass


class BodySizeLimit:
    def __init__(self, app, max_bytes: int = MAX_REQUEST_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope["headers"]:
            if name == b"content-length":
                try:
                    too_large = int(value) > self.max_bytes
                except ValueError:
                    await self._reject(send, 400, "요청을 처리할 수 없습니다")
                    return
                if too_large:
                    await self._reject(send, 413, "요청 본문이 너무 큽니다")
                    return

        received = 0
        started = False

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _BodyTooLarge
            return message

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not started:
                await self._reject(send, 413, "요청 본문이 너무 큽니다")

    @staticmethod
    async def _reject(send, status: int, detail: str) -> None:
        body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode("ascii"))]})
        await send({"type": "http.response.body", "body": body})
