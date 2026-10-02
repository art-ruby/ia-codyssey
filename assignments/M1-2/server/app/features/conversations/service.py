"""대화 저장·불러오기·삭제(T07.03, PRD §10, A17, docs/decisions.md).

- 구조: `conversations` 문서 하나에 `messages[]`(질문·답변·검증 출처·당시 숫자 요약·request_id)를 둔다.
  대화를 지우면 메시지도 같은 문서와 함께 원자적으로 사라진다. 대화당 메시지 `MAX_MESSAGES`개(문서 1MB 보호).
- 덧붙이기는 트랜잭션으로 한다. 같은 대화에 동시에 질문해도 서로 덮어쓰지 않고, 이미 있는 메시지 ID는 다시 넣지 않는다.
- 저장 실패: 채팅이 AI 답을 받은 뒤 대화 저장에 실패하면 검증된 질문·답을 `chat_pending`에 서버가 보관한다.
  재시도(`save_pending`)는 서버가 보관한 답만 대화로 옮기므로 AI를 다시 부르지 않고, 클라이언트가 답·출처를
  지어 넣을 수 없다. 옮기기와 보관본 삭제는 한 트랜잭션이라 두 번 저장되지 않는다. 원래 대화가 사라졌거나
  가득 찼으면 새 대화로 저장하고 `moved_to_new`로 알린다.
- 불러오기: 대화 상세는 답변 출처마다 지금 자료 상태(`current_status`)를 붙인다. 기록은 고치지 않는다.
- 삭제: 대화·그 대화의 저장 대기 답변을 지우고, 요청 기록(Idempotency)에 남은 응답 본문 중 이 대화를 담은 것을 가린다.
"""
from __future__ import annotations

import uuid

from app.core.context import RequestContext
from app.core.errors import NoChange
from app.core.firestore import NotFound, Store
from app.features.materials.eligibility import exclusion_reason
from app.features.materials.service import COLLECTION as MATERIALS

COLLECTION = "conversations"
PENDING = "chat_pending"
MAX_MESSAGES = 200
MAX_PENDING_SHOWN = 100
SUMMARY_FIELDS = ("id", "title", "message_count", "last_message_at", "created_at", "updated_at", "version")
# exclusion_reason → 화면용 현재 상태
STATUS = {None: "available", "not_found": "deleted", "trashed": "trashed", "unapproved": "unapproved",
          "not_kept": "not_kept", "ai_excluded": "ai_excluded"}


class ConversationFull(NoChange):
    """대화의 메시지가 한도에 도달했다(409)."""


class Gone(Exception):
    """덧붙이려던 대화가 그사이 사라졌다."""


def summary(doc: dict) -> dict:
    return {key: doc.get(key) for key in SUMMARY_FIELDS}


def _pending_view(doc: dict) -> dict:
    user = next((m for m in doc.get("messages", []) if m["role"] == "user"), {})
    return {"id": doc["id"], "conversation_id": doc.get("conversation_id"), "question": user.get("content", ""),
            "created_at": doc.get("created_at")}


def append_messages(store: Store, ctx: RequestContext, conversation_id: str | None, title: str,
                    messages: list[dict]) -> str:
    """메시지를 대화에 덧붙이고 대화 ID를 돌려준다. conversation_id가 없으면 새 대화를 만든다."""
    cid = conversation_id or uuid.uuid4().hex
    ids = {m["id"] for m in messages}

    def fn(docs):
        doc = docs[(COLLECTION, cid)]
        if conversation_id and doc is None:
            raise Gone()
        current = (doc or {}).get("messages", [])
        if ids & {m["id"] for m in current}:
            return [], cid  # 이미 저장됨
        if len(current) + len(messages) > MAX_MESSAGES:
            raise ConversationFull()
        merged = [*current, *messages]
        data = {"messages": merged, "message_count": len(merged), "last_message_at": messages[-1]["created_at"]}
        if doc is None:
            data["title"] = title
        return [(COLLECTION, cid, data)], cid

    result, _ = store.run_transaction(ctx, [(COLLECTION, cid)], fn)
    return result


def keep_pending(store: Store, ctx: RequestContext, conversation_id: str | None, title: str,
                 messages: list[dict]) -> str:
    """저장하지 못한 질문·답을 서버에 보관한다. ID는 답변 메시지 ID(같은 답을 두 번 보관하지 않음)."""
    pending_id = messages[-1]["id"]
    store.create(ctx, PENDING, {"conversation_id": conversation_id, "title": title, "messages": messages,
                                "state": "pending"}, doc_id=pending_id)
    return pending_id


def save_pending(store: Store, ctx: RequestContext, pending_id: str) -> dict:
    """보관한 답을 대화로 옮긴다. 원래 대화가 없거나 가득 찼으면 새 대화(ID = 보관 ID)로."""
    pending = store.get(ctx, PENDING, pending_id)  # 없거나 다른 모드·소유자는 404
    target, moved = pending.get("conversation_id"), False
    if target:
        try:
            doc = store.get(ctx, COLLECTION, target)
            if doc.get("message_count", 0) + len(pending["messages"]) > MAX_MESSAGES:
                target, moved = None, True
        except NotFound:
            target, moved = None, True
    cid = target or pending_id
    ids = {m["id"] for m in pending["messages"]}

    def fn(docs):
        if docs[(PENDING, pending_id)] is None:
            raise NotFound(PENDING)  # 그사이 저장했거나 버렸다
        doc = docs[(COLLECTION, cid)]
        if target and doc is None:
            raise NotFound(COLLECTION)  # 확인 직후 대화가 사라졌다. 다시 시도하면 새 대화로 간다
        current = (doc or {}).get("messages", [])
        writes = [(PENDING, pending_id, None)]
        if not ids & {m["id"] for m in current}:
            merged = [*current, *pending["messages"]]
            data = {"messages": merged, "message_count": len(merged),
                    "last_message_at": pending["messages"][-1]["created_at"]}
            if doc is None:
                data["title"] = pending.get("title") or ""
            writes.append((COLLECTION, cid, data))
        return writes, cid

    store.run_transaction(ctx, [(PENDING, pending_id), (COLLECTION, cid)], fn)
    messages = pending["messages"]
    return {"conversation_id": cid, "moved_to_new": moved, "saved": True,
            "message_ids": {"user": messages[0]["id"], "assistant": messages[-1]["id"]}}


def discard_pending(store: Store, ctx: RequestContext, pending_id: str) -> dict:
    store.delete(ctx, PENDING, pending_id)
    store.redact_requests(ctx.owner_id, pending_id)  # 503 응답 본문에 남은 답도 가린다
    return {"deleted": True, "id": pending_id}


def create_conversation(store: Store, ctx: RequestContext, title: str) -> dict:
    doc = store.create(ctx, COLLECTION, {"title": title, "messages": [], "message_count": 0, "last_message_at": None})
    return summary(doc)


def list_conversations(store: Store, ctx: RequestContext, limit: int, cursor: str | None) -> dict:
    page = store.list(ctx, COLLECTION, limit=limit, cursor=cursor, descending=True)  # 최근 만든 대화부터
    pending = store.find(ctx, PENDING, "state", "pending", limit=MAX_PENDING_SHOWN)
    return {"items": [summary(d) for d in page.items], "next_cursor": page.next_cursor,
            "pending": [_pending_view(d) for d in pending]}


def get_conversation(store: Store, ctx: RequestContext, conversation_id: str) -> dict:
    doc = store.get(ctx, COLLECTION, conversation_id)
    cache: dict[str, str] = {}

    def status(material_id: str) -> str:
        if material_id not in cache:
            try:
                material = store.get(ctx, MATERIALS, material_id)
            except NotFound:
                material = None
            cache[material_id] = STATUS[exclusion_reason(material, ctx)]
        return cache[material_id]

    messages = []
    for message in doc.get("messages", []):
        if message.get("role") == "assistant" and message.get("sources"):
            message = {**message, "sources": [{**s, "current_status": status(s["material_id"])}
                                              for s in message["sources"]]}
        messages.append(message)
    pending = store.find(ctx, PENDING, "conversation_id", conversation_id, limit=MAX_PENDING_SHOWN)
    return {**summary(doc), "messages": messages, "pending": [_pending_view(d) for d in pending]}


def delete_conversation(store: Store, ctx: RequestContext, conversation_id: str) -> dict:
    store.get(ctx, COLLECTION, conversation_id)  # 없거나 다른 모드·소유자는 404
    pending = store.find(ctx, PENDING, "conversation_id", conversation_id, limit=MAX_PENDING_SHOWN)
    reads = [(COLLECTION, conversation_id), *[(PENDING, d["id"]) for d in pending]]

    def fn(docs):
        doc = docs[(COLLECTION, conversation_id)]
        if doc is None:
            raise NotFound(COLLECTION)
        return [(c, i, None) for c, i in reads if docs[(c, i)] is not None], len(doc.get("messages", []))

    count, _ = store.run_transaction(ctx, reads, fn)
    # 같은 키 재전송이 지운 답변을 다시 내주지 않게 요청 기록의 응답 본문을 가린다(기록 자체는 남김).
    store.redact_requests(ctx.owner_id, conversation_id)
    for doc in pending:
        store.redact_requests(ctx.owner_id, doc["id"])
    return {"deleted": True, "id": conversation_id, "messages_deleted": count}
