"""채팅 답변(T07.02, PRD §4E·§10, A14, docs/decisions.md).

순서: 대화 확인 → 문맥 구성(검색·자격 필터·숫자 요약) → 사용량 예약 → Provider 호출 → 답변 검증 → 대화 저장 → 성공.

- 실패를 구분한다. 문맥을 만들다 저장소가 실패하면 `search_failed`(503, 사용량을 쓰지 않음), 오늘 한도에
  도달하면 `quota_exceeded`(429), Provider가 실패하거나 답이 JSON이 아니면 `provider_failed`(502, `kind`).
  검색 결과가 없는 것은 실패가 아니다. 답변에 '근거가 되는 보관 자료를 찾지 못했다'는 한계를 서버가 붙인다.
- 출처: 모델은 자료 번호만 안다. 번호를 실제 전달한 자료 ID로 바꾸고, 전달하지 않은 번호는 버린 뒤
  `rejected_source_numbers`로 알린다. 출처를 새로 만들지 않는다. 본문이 '자료 N'으로 언급한 번호도 같은 규칙.
- URL만 있는 자료는 `basis: link_only`로 표시하고 본문을 확인하지 않았다는 한계를 붙인다.
- 답변은 원문에서 확인한 내용(`from_materials`)과 비서의 해석·제안(`interpretation`)을 나눠 받는다.
- 관련 자료: 전달한 자료끼리 사용자가 확정한 연결은 `user_confirmed`, 모델이 관련 있다고 본 나머지는 `ai_suggested`.
- 숫자: 서버 Summary를 그대로 `numbers`로 돌려주고 `virtual`(가상 기록 여부)을 붙인다. 답변에 질문·요약·자료에
  없는 숫자가 나오면 `unverified_numbers`로 알린다(답을 막지는 않는다).
- 모델 응답의 정의 밖 필드(예: 승인·삭제 지시)는 버린다. 이 서비스가 쓰는 곳은 사용량과 대화 기록뿐이다.
- 성공 응답은 대화 저장이 끝난 뒤에 돌려준다(`saved: true`). 같은 Idempotency-Key로 다시 보내면 저장된 응답을 재생한다.
- AI 답을 받은 뒤 대화 저장에 실패하면 답을 서버에 보관하고 503 `save_failed`(답 본문·`pending_id` 포함)를 돌려준다.
  이 응답도 요청 기록에 남아 같은 키 재전송은 AI를 다시 부르지 않는다. 재저장은 `POST /api/conversations
  {pending_id}`(T07.03). 보관마저 실패하면 `pending_id: null`, `retryable: false`.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Callable

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from app.core.config import ConfigError
from app.core.context import RequestContext
from app.core.errors import NoChange
from app.core.firestore import Store
from app.features.analysis import usage
from app.features.analysis.provider import ProviderError, _parse_json
from app.features.analysis.schemas import numbers
from app.features.chat.context import ChatContext, QuestionTooLong, build_context
from app.features.conversations import service as conversations
from app.features.conversations.service import MAX_MESSAGES, ConversationFull
from app.features.materials.eligibility import ai_payload
from app.features.materials.service import display_title

MAX_LIMITATIONS = 5
MAX_TEXT = 4000
NO_MATERIALS = "근거가 되는 보관 자료를 찾지 못했습니다."
_MENTION = re.compile(r"자료\s*(\d+)")
SAVE_FAILED = "답변은 받았지만 대화에 저장하지 못했습니다. 저장을 다시 시도하세요"
SAVE_LOST = "답변은 받았지만 저장하지 못했고 보관도 실패했습니다. 이 답은 다시 불러올 수 없으니 필요하면 다시 질문하세요"
log = logging.getLogger("ai_secretary.chat")


class ChatFailed(NoChange):
    """답변을 만들지 못했다. 대화는 저장하지 않았다(사용량 기록은 남을 수 있다)."""

    def __init__(self, status: int, reason: str, kind: str | None = None) -> None:
        self.status, self.reason, self.kind = status, reason, kind
        super().__init__(reason)


class ModelAnswer(BaseModel):
    """모델이 내는 답. 정의 밖 필드는 버린다(자료 속 지시로 생긴 '작업' 필드가 효력을 갖지 않게)."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    from_materials: str = ""
    interpretation: str = ""
    sources: list = []
    related_suggestions: list = []
    limitations: list[str] = []

    # 실제 모델은 빈 값을 null로, 한계 한 줄을 문자열로 내기도 한다(2026-10-03 확인). 답 문장이 문자열이 아니면
    # 여전히 invalid_output이다. 출처 번호는 뒤에서 전달 자료와 대조하므로 여기서는 목록인지만 맞춘다.
    @field_validator("from_materials", "interpretation", mode="before")
    @classmethod
    def _null_text(cls, value):
        return "" if value is None else value

    @field_validator("sources", "related_suggestions", mode="before")
    @classmethod
    def _null_list(cls, value):
        return value if isinstance(value, list) else []

    @field_validator("limitations", mode="before")
    @classmethod
    def _notes(cls, value):
        if isinstance(value, str):
            return [value]
        return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _norm_numbers(text: str) -> set[str]:
    """'자료 N' 표기를 뺀 숫자. 앞자리 0은 지운다(날짜 '01'과 '1일'을 같게)."""
    return {n.lstrip("0") or "0" for n in numbers(_MENTION.sub(" ", text))}


def _history_content(message: dict) -> str:
    """과거 답은 답 형식(JSON)으로 보낸다. 문장으로 보내면 모델이 그 형식을 따라 JSON이 아닌 답을 낸다(2026-10-03 확인)."""
    if message["role"] != "assistant" or not isinstance(message.get("answer"), dict):
        return message["content"]
    answer = message["answer"]
    return json.dumps({"from_materials": answer.get("from_materials", ""),
                       "interpretation": answer.get("interpretation", "")}, ensure_ascii=False)


def _call(adapter_factory: Callable, store: Store, ctx: RequestContext, day: str, messages: list[dict]):
    """Provider를 한 번 부르고 답을 형식 검증한다. 사용량: 보내기 전 실패는 환불, 보낸 뒤는 결과·토큰 기록."""
    tokens = None
    try:
        reply = adapter_factory().answer_question(messages)
        tokens = reply.total_tokens
        try:
            answer = ModelAnswer.model_validate(_parse_json(reply.text))
        except ValidationError as exc:
            raise ProviderError("invalid_output") from exc
    except ConfigError:
        usage.refund(store, ctx.owner_id, day, "chat")
        raise ChatFailed(502, "provider_failed", "missing_ai_settings")
    except ProviderError as exc:
        if exc.request_sent:
            usage.record_sent(store, ctx.owner_id, day, failed=True, tokens=tokens or exc.total_tokens)
        else:
            usage.refund(store, ctx.owner_id, day, "chat")
        raise ChatFailed(502, "provider_failed", exc.kind)
    usage.record_sent(store, ctx.owner_id, day, failed=False, tokens=tokens)
    return answer, reply.model


def _related(answer: ModelAnswer, built: ChatContext) -> list[dict]:
    ids, count = built.source_ids, len(built.source_ids)
    out, seen = [], set()

    def add(first: int, second: int, status: str) -> None:
        pair = frozenset((ids[first - 1], ids[second - 1]))
        if first == second or pair in seen:
            return
        seen.add(pair)
        low, high = sorted((first, second))
        out.append({"material_ids": [ids[low - 1], ids[high - 1]], "numbers": [low, high], "status": status})

    for pair in built.confirmed_pairs:  # 모델이 언급하지 않아도 사용자 확정 연결은 보여 준다
        a, b = sorted(ids.index(m) + 1 for m in pair)
        add(a, b, "user_confirmed")
    for item in answer.related_suggestions:
        if isinstance(item, list) and len(item) == 2 and all(_is_int(n) and 1 <= n <= count for n in item):
            add(item[0], item[1], "ai_suggested")
    return sorted(out, key=lambda r: (r["status"] != "user_confirmed", r["numbers"]))


def _verify(answer: ModelAnswer, built: ChatContext, question: str) -> dict:
    """모델 답을 전달한 자료·요약과 대조해 응답 본문으로 만든다."""
    docs, count = built.docs, len(built.docs)
    text = f"{answer.from_materials}\n{answer.interpretation}"
    mentions = [int(m) for m in _MENTION.findall(text)]
    valid = sorted({n for n in [*filter(_is_int, answer.sources), *mentions] if 1 <= n <= count})
    rejected = list(dict.fromkeys(n for n in answer.sources if _is_int(n) and not 1 <= n <= count))
    mentioned_bad = sorted({n for n in mentions if not 1 <= n <= count})

    sources = [{"number": n, "material_id": docs[n - 1]["id"], "display_title": display_title(docs[n - 1])[0],
                "url": docs[n - 1].get("url"), "registered_at": docs[n - 1].get("registered_at"),
                "basis": "link_only" if docs[n - 1]["id"] in built.link_only else "content"} for n in valid]

    allowed = _norm_numbers(question + json.dumps(built.summaries, ensure_ascii=False)
                            + json.dumps([ai_payload(d) for d in docs], ensure_ascii=False))
    unverified = sorted(_norm_numbers(text) - allowed, key=lambda n: (len(n), n))

    limits = [NO_MATERIALS] if built.omitted.get("no_materials") else []
    limits += [f"답변이 전달하지 않은 자료 {n}을(를) 언급했습니다. 출처로 인정하지 않았습니다." for n in mentioned_bad]
    limits += [f"자료 {s['number']}은(는) 링크만 저장돼 본문을 확인하지 않은 자료입니다. 링크와 사용자가 쓴 정보만 근거로 했습니다."
               for s in sources if s["basis"] == "link_only"]
    if unverified:
        limits.append(f"요약·자료에서 확인되지 않은 숫자가 있습니다: {', '.join(unverified)}")
    if built.omitted.get("materials_over_limit"):
        limits.append(f"관련 자료 중 {built.omitted['materials_over_limit']}건은 한도(5건)로 빠졌습니다.")
    if built.omitted.get("body_truncated"):
        limits.append("본문 합계 한도(20,000자)로 일부 본문만 확인했습니다.")
    if built.omitted.get("scan_truncated"):
        limits.append("최근 자료 일부만 검색했습니다(일부 자료 기준).")
    limits += [note[:300] for note in answer.limitations if note][:MAX_LIMITATIONS]

    return {
        "answer": {"from_materials": answer.from_materials[:MAX_TEXT],
                   "interpretation": answer.interpretation[:MAX_TEXT], "limitations": limits},
        "sources": sources,
        "rejected_source_numbers": rejected,
        "related": _related(answer, built),
        # 첫 요약은 현재 모드의 기본 요약(default), 나머지는 질문이 정한 조건의 요약(question, T07.04 화면 구분용).
        "numbers": [{**s, "virtual": s.get("source") == "sample", "role": "default" if i == 0 else "question"}
                    for i, s in enumerate(built.summaries)],
        "unverified_numbers": unverified,
        "omitted": built.omitted,
    }


def handle_chat(store: Store, ctx: RequestContext, conversation_id: str | None, question: str,
                adapter_factory: Callable, daily_limit: int) -> tuple[int, dict]:
    """(HTTP 상태, 응답 본문). 200은 저장 완료, 503은 답을 받았지만 저장 실패(`save_failed`)."""
    question = question.strip()
    conversation = store.get(ctx, conversations.COLLECTION, conversation_id) if conversation_id else None
    past = (conversation or {}).get("messages", [])  # 다른 모드·소유자의 대화는 위에서 404
    if len(past) + 2 > MAX_MESSAGES:
        raise ConversationFull()
    history = [{"role": m["role"], "content": _history_content(m), "source_ids": m.get("source_ids", [])} for m in past]

    try:
        built = build_context(store, ctx, question, history)
    except QuestionTooLong:
        raise
    except Exception as exc:  # 검색 실패를 '결과 없음'으로 바꾸지 않는다
        raise ChatFailed(503, "search_failed") from exc

    day = usage.reserve(store, ctx.owner_id, "chat", daily_limit)
    if day is None:
        raise ChatFailed(429, "quota_exceeded")
    answer, model = _call(adapter_factory, store, ctx, day, built.messages)
    result = _verify(answer, built, question)

    at = _now().isoformat()
    user_msg = {"id": uuid.uuid4().hex, "role": "user", "content": question, "request_id": ctx.request_id,
                "created_at": at}
    parts = (result["answer"]["from_materials"], result["answer"]["interpretation"])
    assistant_msg = {"id": uuid.uuid4().hex, "role": "assistant", "content": "\n\n".join(p for p in parts if p),
                     "source_ids": [s["material_id"] for s in result["sources"]], "model": model,
                     "request_id": ctx.request_id, "created_at": at,
                     **{k: result[k] for k in ("answer", "sources", "rejected_source_numbers", "related", "numbers",
                                               "unverified_numbers")}}
    turn = [user_msg, assistant_msg]
    body = {"message_ids": {"user": user_msg["id"], "assistant": assistant_msg["id"]}, **result, "model": model}
    title = question[:40]
    try:
        saved_id = conversations.append_messages(store, ctx, conversation_id, title, turn)
    except Exception as exc:  # 저장 실패: 답을 버리지 않고 서버에 보관한다
        log.warning("chat save failed: %s", type(exc).__name__)
        try:
            pending_id = conversations.keep_pending(store, ctx, conversation_id, title, turn)
        except Exception as keep_exc:
            log.warning("chat pending keep failed: %s", type(keep_exc).__name__)
            pending_id = None
        return 503, {"conversation_id": conversation_id, **body, "saved": False, "reason": "save_failed",
                     "pending_id": pending_id, "retryable": pending_id is not None,
                     "detail": SAVE_FAILED if pending_id else SAVE_LOST}
    return 200, {"conversation_id": saved_id, **body, "saved": True}
