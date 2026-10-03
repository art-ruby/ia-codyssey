"""처리되지 않은 예외는 CORS 헤더가 붙은 JSON 500이 되어야 한다(브라우저가 연결 실패로 오인하지 않게)."""
import logging

from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.firestore import MemoryStore
from app.main import create_app

OWNER = "owner-1"
WEB = "https://web.example"


class BrokenStore(MemoryStore):
    def list(self, *args, **kwargs):
        raise RuntimeError("index not ready")


def make_client(store):
    settings = load_settings({"OWNER_UID": OWNER, "ALLOWED_ORIGINS": WEB})
    app = create_app(settings, verify_token=lambda t: {"uid": OWNER}, store=store)
    return TestClient(app)


def headers():
    return {"Authorization": "Bearer t", "X-Data-Mode": "personal", "Origin": WEB}


def test_unhandled_error_is_json_500_with_cors_header(caplog):
    c = make_client(BrokenStore())

    with caplog.at_level(logging.ERROR, logger="ai_secretary.error"):
        res = c.get("/api/news", headers=headers())

    assert res.status_code == 500
    assert res.headers["access-control-allow-origin"] == WEB
    assert res.json() == {"detail": "서버에서 오류가 났습니다. 잠시 뒤 다시 시도하세요", "reason": "internal_error"}
    assert "index not ready" not in res.text  # 내부 오류 내용은 응답에 넣지 않는다
    assert any("unhandled error GET /api/news" in r.getMessage() and r.exc_info for r in caplog.records)


def test_handled_errors_are_unchanged():
    c = make_client(MemoryStore())

    assert c.get("/api/news", headers={**headers(), "X-Data-Mode": "sample"}).json()["reason"] == "personal_only"
    assert c.get("/api/news", headers={"Origin": WEB}).status_code == 401
