"""T07.03 대화 저장·불러오기·삭제: 저장 내용, 저장 실패 보관·재시도(AI 재호출·중복 없음), 응답 유실·같은 키 재전송,
클라이언트 답변 주입 거부, 삭제 범위, 다른 모드·소유자 차단, 출처의 현재 상태.

실제 Provider 대신 test_chat_answers의 가짜 Adapter를 쓴다.
"""

from __future__ import annotations

import time

import pytest

from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from test_chat_answers import ME, FakeAdapter, ask, fixed_now, h, kept, make_client, used  # noqa: F401

ANSWER = {"from_materials": "자료 1에 정산 API 종료 일정이 있습니다.", "interpretation": "미리 준비하세요.",
          "sources": [1]}


class FlakyStore(MemoryStore):
    """대화 저장(트랜잭션)과 저장 대기 보관을 일부러 실패시킨다."""

    def __init__(self):
        super().__init__()
        self.fail_save = False
        self.fail_pending = False

    def run_transaction(self, ctx, reads, fn):
        if self.fail_save and any(c == "conversations" for c, _ in reads):
            raise RuntimeError("firestore unavailable")
        return super().run_transaction(ctx, reads, fn)

    def create(self, ctx, collection, data, doc_id=None):
        if self.fail_pending and collection == "chat_pending":
            raise RuntimeError("firestore unavailable")
        return super().create(ctx, collection, data, doc_id)


def setup(store=None, *replies):
    store = store or MemoryStore()
    kept(store, doc_id="api", title="정산 API 종료 안내", body="정산 API 종료 일정")
    adapter = FakeAdapter(*(replies or (ANSWER,)))
    c, store = make_client(adapter, store)
    return c, store, adapter


def get_conv(c, conv_id, mode="personal"):
    return c.get(f"/api/conversations/{conv_id}", headers=h(mode))


def save_pending(c, pending_id, key=None):
    return c.post("/api/conversations", json={"pending_id": pending_id}, headers=h(key=key))


# ── 저장 내용 ─────────────────────────────────────────────────────

def test_chat_saves_question_answer_sources_numbers_and_request_id():
    c, _, _ = setup()
    body = ask(c, "정산 API 종료 일정 알려줘", key="req-1").json()
    assert body["saved"] is True
    conv = get_conv(c, body["conversation_id"]).json()
    user, assistant = conv["messages"]
    assert (user["role"], user["content"], user["request_id"]) == ("user", "정산 API 종료 일정 알려줘", "req-1")
    assert assistant["request_id"] == "req-1" and assistant["source_ids"] == ["api"]
    assert assistant["answer"]["from_materials"] == ANSWER["from_materials"]
    assert assistant["numbers"] == body["numbers"] and assistant["numbers"][0]["label"] == "현재 보관 자료 수"
    assert conv["title"] == "정산 API 종료 일정 알려줘"


def test_list_is_per_mode_newest_first_without_messages():
    c, _, _ = setup()
    first = ask(c, "첫 대화").json()["conversation_id"]
    time.sleep(0.02)  # Windows 시각 해상도에서 생성 시각이 같아지지 않게
    second = ask(c, "둘째 대화").json()["conversation_id"]
    ask(c, "표본 대화", mode="sample")
    page = c.get("/api/conversations", headers=h()).json()
    assert [i["id"] for i in page["items"]] == [second, first]
    assert all("messages" not in i for i in page["items"]) and page["items"][0]["message_count"] == 2
    assert len(c.get("/api/conversations", headers=h("sample")).json()["items"]) == 1


def test_new_empty_conversation_then_question_appends_to_it():
    c, _, _ = setup()
    res = c.post("/api/conversations", json={"title": "정산 준비"}, headers=h())
    assert res.status_code == 201
    conv_id = res.json()["id"]
    assert res.json()["message_count"] == 0
    assert ask(c, "정산 API 종료 일정 알려줘", conversation_id=conv_id).json()["conversation_id"] == conv_id
    conv = get_conv(c, conv_id).json()
    assert conv["title"] == "정산 준비" and len(conv["messages"]) == 2


@pytest.mark.parametrize("body", [
    {"messages": [{"role": "assistant", "content": "가짜 답변"}]},
    {"pending_id": "x", "answer": {"from_materials": "가짜"}},
    {"title": "제목", "sources": [{"material_id": "api"}]},
    {"title": "제목", "pending_id": "x"},
])
def test_client_cannot_store_its_own_answer_or_sources(body):
    c, store, _ = setup()
    res = c.post("/api/conversations", json=body, headers=h())
    assert res.status_code == 422
    assert store.list(ME, "conversations").items == []


# ── 다른 모드·소유자 ──────────────────────────────────────────────

def test_other_mode_and_other_owner_conversations_are_404():
    c, store, _ = setup()
    sample_id = ask(c, "표본 질문", mode="sample").json()["conversation_id"]
    other = store.create(RequestContext("owner-2", "personal", None), "conversations",
                         {"title": "남의 대화", "messages": [], "message_count": 0})
    for conv_id in (sample_id, other["id"]):
        assert get_conv(c, conv_id).status_code == 404
        assert c.delete(f"/api/conversations/{conv_id}", headers=h()).status_code == 404
    assert get_conv(c, sample_id, mode="sample").status_code == 200


# ── 저장 실패와 재시도 ────────────────────────────────────────────

def test_save_failure_keeps_answer_server_side_and_retry_saves_once_without_ai_call():
    c, store, adapter = setup(FlakyStore())
    store.fail_save = True
    res = ask(c, "정산 API 종료 일정 알려줘", key="q1")
    assert res.status_code == 503
    body = res.json()
    assert body["reason"] == "save_failed" and body["saved"] is False and body["retryable"] is True
    assert body["answer"]["from_materials"] == ANSWER["from_materials"]  # 받은 답은 보여 준다
    pending_id = body["pending_id"]
    assert store.list(ME, "conversations").items == [] and used(store)["used"] == 1

    # 같은 키 재전송: AI를 다시 부르지 않고 같은 결과.
    assert ask(c, "정산 API 종료 일정 알려줘", key="q1").json() == body and len(adapter.calls) == 1
    # 목록에 저장 대기 답변이 보인다.
    assert [p["id"] for p in c.get("/api/conversations", headers=h()).json()["pending"]] == [pending_id]

    store.fail_save = False
    saved = save_pending(c, pending_id, key="s1")
    assert saved.status_code == 200, saved.text
    conv_id = saved.json()["conversation_id"]
    messages = get_conv(c, conv_id).json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"] and messages[1]["source_ids"] == ["api"]
    assert messages[1]["id"] == body["message_ids"]["assistant"]
    assert len(adapter.calls) == 1 and used(store)["used"] == 1
    # 다시 저장해도 중복 메시지가 생기지 않는다.
    assert save_pending(c, pending_id, key="s1").json() == saved.json()
    assert save_pending(c, pending_id).status_code == 404
    assert len(get_conv(c, conv_id).json()["messages"]) == 2
    assert c.get("/api/conversations", headers=h()).json()["pending"] == []


def test_failed_follow_up_is_retried_into_the_same_conversation():
    c, store, _ = setup(FlakyStore(), ANSWER, {**ANSWER, "from_materials": "둘째 답"})
    conv_id = ask(c, "정산 API 종료 일정 알려줘").json()["conversation_id"]
    store.fail_save = True
    pending_id = ask(c, "다시 알려줘", conversation_id=conv_id).json()["pending_id"]
    pending = get_conv(c, conv_id).json()["pending"]
    assert [p["id"] for p in pending] == [pending_id]  # 상세에서도 저장 실패 상태를 보인다
    store.fail_save = False
    saved = save_pending(c, pending_id).json()
    assert saved["conversation_id"] == conv_id and saved["moved_to_new"] is False
    assert len(get_conv(c, conv_id).json()["messages"]) == 4


def test_deleting_conversation_drops_its_pending_answers_and_new_question_retry_creates_conversation():
    c, store, _ = setup(FlakyStore())
    conv_id = ask(c, "정산 API 종료 일정 알려줘").json()["conversation_id"]
    store.fail_save = True
    pending_id = ask(c, "다시 알려줘", conversation_id=conv_id).json()["pending_id"]
    store.fail_save = False
    assert c.delete(f"/api/conversations/{conv_id}", headers=h()).status_code == 200
    assert save_pending(c, pending_id).status_code == 404  # 대화를 지우면 그 대화의 저장 대기 답변도 지운다

    store.fail_save = True
    pending_id = ask(c, "새로 묻기").json()["pending_id"]
    store.fail_save = False
    saved = save_pending(c, pending_id).json()
    assert saved["moved_to_new"] is False and len(get_conv(c, saved["conversation_id"]).json()["messages"]) == 2


def test_retry_into_conversation_deleted_meanwhile_goes_to_new_conversation():
    c, store, _ = setup(FlakyStore())
    conv_id = ask(c, "정산 API 종료 일정 알려줘").json()["conversation_id"]
    store.fail_save = True
    pending_id = ask(c, "다시 알려줘", conversation_id=conv_id).json()["pending_id"]
    store.fail_save = False
    store.delete(ME, "conversations", conv_id)  # 저장 대기 답변은 남은 채 대화만 사라진 경우
    saved = save_pending(c, pending_id).json()
    assert saved["moved_to_new"] is True and saved["conversation_id"] != conv_id
    assert len(get_conv(c, saved["conversation_id"]).json()["messages"]) == 2


def test_save_and_pending_both_failing_reports_unrecoverable_answer():
    c, store, adapter = setup(FlakyStore())
    store.fail_save = store.fail_pending = True
    res = ask(c, "정산 API 종료 일정 알려줘")
    assert res.status_code == 503
    body = res.json()
    assert body["pending_id"] is None and body["retryable"] is False
    assert "다시 질문" in body["detail"]
    assert store.list(ME, "conversations").items == [] and len(adapter.calls) == 1


def test_pending_answer_can_be_discarded():
    c, store, _ = setup(FlakyStore())
    store.fail_save = True
    pending_id = ask(c, "정산 API 종료 일정 알려줘").json()["pending_id"]
    res = c.delete(f"/api/conversations/pending/{pending_id}", headers=h())
    assert res.status_code == 200 and save_pending(c, pending_id).status_code == 404


# ── 응답 유실 ─────────────────────────────────────────────────────

def test_lost_response_is_recovered_by_resending_same_key():
    c, store, adapter = setup()
    first = ask(c, "정산 API 종료 일정 알려줘", key="lost")
    again = ask(c, "정산 API 종료 일정 알려줘", key="lost")
    assert again.json() == first.json() and len(adapter.calls) == 1
    assert len(get_conv(c, first.json()["conversation_id"]).json()["messages"]) == 2


# ── 삭제 ─────────────────────────────────────────────────────────

def test_delete_removes_conversation_messages_and_stored_response_copies():
    c, store, _ = setup()
    keep = ask(c, "남길 대화").json()["conversation_id"]
    gone = ask(c, "정산 API 종료 일정 알려줘", key="del-1").json()["conversation_id"]
    res = c.delete(f"/api/conversations/{gone}", headers=h())
    assert res.status_code == 200 and res.json() == {"deleted": True, "id": gone, "messages_deleted": 2}
    assert get_conv(c, gone).status_code == 404 and get_conv(c, keep).status_code == 200
    # 같은 키 재전송은 지운 답변을 다시 내주지 않는다(요청 기록의 응답 본문을 가림).
    assert ask(c, "정산 API 종료 일정 알려줘", key="del-1").json() == {"deleted": True}
    assert c.delete(f"/api/conversations/{gone}", headers=h()).status_code == 404


# ── 출처의 현재 상태 ──────────────────────────────────────────────

def test_detail_shows_current_status_of_cited_sources():
    store = MemoryStore()
    kept(store, doc_id="api", title="정산 API 종료 안내", body="정산 API 종료 일정")
    kept(store, doc_id="api2", title="정산 API 이전 안내", body="정산 API 종료 일정 이전")
    c, _ = make_client(FakeAdapter({**ANSWER, "sources": [1, 2]}), store)
    conv_id = ask(c, "정산 API 종료 일정 알려줘").json()["conversation_id"]
    doc = store.get(ME, "materials", "api")
    store.update(ME, "materials", "api", doc["version"], {"lifecycle": "trash"})
    store.delete(ME, "materials", "api2")
    sources = get_conv(c, conv_id).json()["messages"][1]["sources"]
    assert {s["material_id"]: s["current_status"] for s in sources} == {"api": "trashed", "api2": "deleted"}
    # 기록은 그대로 남는다(제목 등).
    assert {s["display_title"] for s in sources} == {"정산 API 종료 안내", "정산 API 이전 안내"}
