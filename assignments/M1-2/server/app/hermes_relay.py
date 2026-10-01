"""Narrow, loopback-only authenticated relay for the local Hermes API."""

from __future__ import annotations

import hmac
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from app.core.config import ConfigError, Settings

HERMES_BASE_URL = "http://127.0.0.1:8642/v1"
MAX_REQUEST_BYTES = 1024 * 1024
MAX_UPSTREAM_TIMEOUT_SECONDS = 120
ALLOWED_OPERATIONS = {
    ("GET", "/v1/toolsets"),
    ("POST", "/v1/chat/completions"),
}


def create_relay_app(
    settings: Settings,
    upstream_client: httpx.AsyncClient | None = None,
) -> FastAPI:
    """Create the restricted relay; missing or reused credentials fail closed."""
    relay_token = settings.get("HERMES_RELAY_TOKEN")
    hermes_api_key = settings.get("OPENAI_API_KEY")
    if (not relay_token or not hermes_api_key
            or hmac.compare_digest(relay_token.encode("utf-8"), hermes_api_key.encode("utf-8"))):
        raise ConfigError("Hermes 중계 설정이 없거나 키가 분리되지 않았습니다")

    timeout = min(settings.ai_timeout_seconds, MAX_UPSTREAM_TIMEOUT_SECONDS)
    app = FastAPI(title="Hermes Relay", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.upstream_client = upstream_client

    @app.middleware("http")
    async def validate_request(request: Request, call_next):
        authorization = request.headers.get("authorization", "")
        scheme, separator, supplied_token = authorization.partition(" ")
        if (not separator or scheme.lower() != "bearer" or not supplied_token
                or not hmac.compare_digest(supplied_token.encode("utf-8"), relay_token.encode("utf-8"))):
            return JSONResponse({"detail": "인증이 필요합니다"}, status_code=401)

        raw_path = request.scope.get("raw_path", b"").decode("ascii", errors="ignore")
        if request.scope.get("query_string"):
            return JSONResponse({"detail": "요청을 처리할 수 없습니다"}, status_code=404)
        operation = (request.method.upper(), raw_path)
        if operation not in ALLOWED_OPERATIONS:
            code = 405 if any(path == raw_path for _, path in ALLOWED_OPERATIONS) else 404
            return JSONResponse({"detail": "요청을 처리할 수 없습니다"}, status_code=code)
        return await call_next(request)

    async def forward(request: Request, method: str, path: str, body: bytes = b"") -> Response:
        request_headers = {"Authorization": f"Bearer {hermes_api_key}"}
        content_type = request.headers.get("content-type", "")
        if method == "POST":
            media_type = content_type.split(";", 1)[0].strip().lower()
            if media_type != "application/json":
                return JSONResponse({"detail": "JSON 요청만 허용합니다"}, status_code=415)
            if not body:
                return JSONResponse({"detail": "요청 본문이 비어 있습니다"}, status_code=400)
            request_headers["Content-Type"] = "application/json"
        url = f"{HERMES_BASE_URL}{path.removeprefix('/v1')}"
        client = app.state.upstream_client
        try:
            if client is None:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as temporary_client:
                    upstream_response = await temporary_client.request(
                        method, url, content=body or None, headers=request_headers,
                    )
            else:
                upstream_response = await client.request(
                    method, url, content=body or None, headers=request_headers,
                    timeout=timeout, follow_redirects=False,
                )
        except httpx.TimeoutException:
            return JSONResponse({"detail": "Hermes 응답 시간이 초과되었습니다"}, status_code=504)
        except httpx.RequestError:
            return JSONResponse({"detail": "Hermes에 연결할 수 없습니다"}, status_code=502)

        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers={"Content-Type": "application/json"},
        )

    async def read_limited_body(request: Request) -> bytes | JSONResponse:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    return JSONResponse({"detail": "요청 본문이 너무 큽니다"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "요청을 처리할 수 없습니다"}, status_code=400)

        chunks: list[bytes] = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > MAX_REQUEST_BYTES:
                return JSONResponse({"detail": "요청 본문이 너무 큽니다"}, status_code=413)
            chunks.append(chunk)
        return b"".join(chunks)

    @app.get("/v1/toolsets")
    async def toolsets(request: Request) -> Response:
        return await forward(request, "GET", "/v1/toolsets")

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Response:
        body = await read_limited_body(request)
        if isinstance(body, JSONResponse):
            return body
        return await forward(request, "POST", "/v1/chat/completions", body)

    return app
