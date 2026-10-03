from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.analysis.provider import TextResult
from app.features.materials.service import COLLECTION as MATERIALS
from app.main import create_app

OWNER = "owner-1"
SECRET = "telegram-secret"
CHAT_ID = 123456
ME = RequestContext(OWNER, "personal", None)


class FakeAdapter:
    def __init__(self):
        self.calls = []

    def answer_question(self, messages):
        self.calls.append(messages)
        return TextResult(
            text=json.dumps({
                "from_materials": "자료 1에 따르면 회의는 금요일입니다.",
                "interpretation": "일정 전에 준비 목록을 확인하세요.",
                "sources": [1],
            }, ensure_ascii=False),
            model="fake-model",
            total_tokens=10,
        )


def make_client(*, allowed_chat=str(CHAT_ID)):
    store = MemoryStore()
    store.create(ME, MATERIALS, {
        "source_type": "text", "title": "회의 일정", "description": "", "body": "회의는 금요일입니다.",
        "save_reason": "", "memo": "", "url": None, "review_status": "approved",
        "copy_status": "not_applicable", "lifecycle": "active", "ai_excluded": False,
        "registered_at": "2026-10-01T00:00:00+00:00",
        "storage_approved_at": "2026-10-01T00:00:00+00:00",
    }, doc_id="meeting")
    adapter = FakeAdapter()
    settings = load_settings({
        "OWNER_UID": OWNER,
        "AI_DAILY_REQUEST_LIMIT": "10",
        "TELEGRAM_BOT_TOKEN": "bot-token",
        "TELEGRAM_ALLOWED_CHAT_ID": allowed_chat,
        "TELEGRAM_WEBHOOK_SECRET": SECRET,
    })
    app = create_app(settings, verify_token=lambda t: {"uid": OWNER}, store=store,
                     analysis_adapter_factory=lambda: adapter)
    sent = []
    app.state.telegram_send_message = lambda chat_id, text: sent.append((chat_id, text))
    return TestClient(app, raise_server_exceptions=False), sent, adapter, store


def update(text="회의 일정 알려줘", update_id=100, chat_id=CHAT_ID):
    return {"update_id": update_id, "message": {"chat": {"id": chat_id}, "text": text}}


def headers(secret=SECRET):
    return {"X-Telegram-Bot-Api-Secret-Token": secret}


def test_webhook_secret_is_required():
    client, sent, adapter, _ = make_client()
    res = client.post("/api/telegram/webhook", json=update(), headers=headers("wrong"))
    assert res.status_code == 403
    assert sent == [] and adapter.calls == []


def test_start_replies_with_connection_message():
    client, sent, adapter, _ = make_client()
    res = client.post("/api/telegram/webhook", json=update("/start"), headers=headers())
    assert res.status_code == 200, res.text
    assert sent == [(CHAT_ID, "AI Secretary와 연결되었습니다. 이제 질문을 보내면 비서가 답합니다.")]
    assert adapter.calls == []


def test_question_uses_chat_flow_and_sends_answer_once_for_duplicate_update():
    client, sent, adapter, store = make_client()
    body = update()
    res = client.post("/api/telegram/webhook", json=body, headers=headers())
    assert res.status_code == 200, res.text
    assert len(sent) == 1 and sent[0][0] == CHAT_ID
    assert "회의는 금요일" in sent[0][1]
    assert len(adapter.calls) == 1
    assert len(store.list(ME, "conversations").items) == 1

    replay = client.post("/api/telegram/webhook", json=body, headers=headers())
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert len(sent) == 1 and len(adapter.calls) == 1


def test_other_chat_is_ignored_without_ai_call():
    client, sent, adapter, _ = make_client()
    res = client.post("/api/telegram/webhook", json=update(chat_id=999), headers=headers())
    assert res.status_code == 200
    assert res.json()["reason"] == "chat_not_allowed"
    assert sent == [] and adapter.calls == []


def test_missing_allowed_chat_only_allows_start_guidance():
    client, sent, adapter, _ = make_client(allowed_chat="")
    res = client.post("/api/telegram/webhook", json=update("/start"), headers=headers())
    assert res.status_code == 200
    assert "TELEGRAM_ALLOWED_CHAT_ID" in sent[0][1]
    res = client.post("/api/telegram/webhook", json=update("질문", update_id=101), headers=headers())
    assert res.status_code == 200
    assert "아직 연결 설정" in sent[1][1]
    assert adapter.calls == []
