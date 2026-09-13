"""AI Chat — 컨텍스트 주입 후 GPT 호출, 대화 자동 저장.

과제 요구 흐름(요약 조회 → 프롬프트 주입 → GPT → conversations 저장)을
한 엔드포인트 안에서 끝낸다. 저장은 '대화가 끝난 뒤 따로 눌러야 하는 일'이
아니라 답변 생성의 일부여야, 사용자가 저장을 잊어 기록이 비지 않는다.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..config import Settings
from ..deps import config_dep, store_dep
from ..models.schemas import ChatRequest, ChatResponse
from ..repositories.store import Store
from ..services.chat import (
    SYSTEM_RULES,
    build_candidate_refs,
    build_context_block,
    default_title,
    generate_reply,
    select_candidates,
)
from ..services.summary import build_summary

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post(
    "/preview",
    summary="[DEBUG 전용] 주입될 System Prompt 확인 (모델 호출 없음)",
    include_in_schema=False,  # 꺼져 있을 때 Swagger 에 존재를 알리지 않는다
)
def preview(
    payload: ChatRequest,
    store: Store = Depends(store_dep),
    settings: Settings = Depends(config_dep),
) -> dict:
    """모델을 부르지 않고 '무엇이 주입되는지'만 보여준다.

    컨텍스트 주입이 실제로 일어나는지는 답변 문장으로는 증명되지 않는다.
    (모델이 우연히 맞게 답할 수도 있다.) 그래서 주입 직전의 문자열 자체를
    돌려주는 경로를 둔다. 과금이 없으므로 개발·채점에 쓸 수 있다.

    ⚠️ 이 응답에는 내부 지시문 전문과 후보 데이터가 들어 있다. 운영에 열어 두면
    프롬프트와 데이터가 그대로 공개되므로 **DEBUG=true 일 때만** 동작한다.
    꺼져 있으면 403 이 아니라 404 로 답한다 — 403 은 '여기 뭔가 있다'를
    알려 주기 때문이다.
    """
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not Found")

    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="질문이 비어 있습니다")

    candidates = store.list_candidates()
    summary = build_summary(candidates)
    selected, basis = select_candidates(question, candidates)
    context = build_context_block(summary, selected, basis)

    return {
        "question": question,
        "model": settings.openai_model if settings.openai_enabled else "rule-based (no API key)",
        "summary_injected": summary.model_dump(mode="json"),
        "candidates_injected": len(selected),
        "selection_basis": basis,
        "total_candidates_in_store": len(candidates),
        "system_prompt": SYSTEM_RULES + "\n\n" + context,
        "system_prompt_chars": len(SYSTEM_RULES) + len(context) + 2,
    }


def _channel_context(selected: list[dict], settings: Settings) -> tuple[list[str], dict[str, dict]]:
    """선별된 후보들의 채널 Identity 요약과 저장된 assessment 를 모은다. 없으면 없는 대로."""
    from ..services.assessment import AssessmentStore
    from ..services.identity import IdentityStore, summary_line

    if not settings.radar_root:
        return [], {}
    istore, astore = IdentityStore(settings.radar_root), AssessmentStore(settings.radar_root)
    lines: list[str] = []
    seen: set[str] = set()
    assessments: dict[str, dict] = {}
    for item in selected:
        ch = str(item.get("channel") or "")
        vid = str(item.get("radar_id") or "")
        if ch and ch not in seen:
            seen.add(ch)
            doc = istore.load(ch)
            lines.append(f"- {ch}: " + (summary_line(doc) if doc else "Identity 없음 — 모든 후보는 REVIEW_REQUIRED"))
        if ch and vid:
            a = astore.load(ch, vid)
            if a:
                assessments[str(item.get("id"))] = a
    return lines, assessments


@router.post("", response_model=ChatResponse, summary="데이터 기반 AI 대화")
def chat(
    payload: ChatRequest,
    store: Store = Depends(store_dep),
    settings: Settings = Depends(config_dep),
) -> ChatResponse:
    question = payload.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="질문이 비어 있습니다")

    # ① 요약 조회 ② 관련 후보 선별
    candidates = store.list_candidates()
    summary = build_summary(candidates)
    selected, basis = select_candidates(question, candidates)

    # ③ 이어가는 대화면 기존 기록을 불러온다
    # stored   — 저장돼 있던 원본(refs 포함). 다시 저장할 때 이것을 그대로 잇는다.
    # history  — 모델에 넘기는 role/content 만. refs 를 모델에 보낼 이유가 없다.
    # 둘을 나누지 않으면 두 번째 질문부터 이전 답변의 refs 가 저장에서 사라진다.
    stored: list[dict] = []
    history: list[dict[str, str]] = []
    conversation = None
    if payload.conversation_id:
        conversation = store.get_conversation(payload.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="이어갈 대화를 찾을 수 없습니다")
        stored = list(conversation.get("messages") or [])
        history = [
            {"role": m.get("role", ""), "content": m.get("content", "")} for m in stored
        ]

    # ④ 프롬프트 주입 + 모델 호출 — 채널 운영 기준과 후보별 판정을 함께 넣는다
    identity_lines, assessments = _channel_context(selected, settings)
    reply, model_name, answer_source = generate_reply(
        question=question,
        summary=summary,
        candidates=selected,
        history=history,
        settings=settings,
        basis=basis,
        identity_lines=identity_lines,
        assessments=assessments,
    )

    # ⑤ 자동 저장 — assistant 메시지에 번호↔후보 대응표를 함께 남긴다.
    #    이것이 없으면 대화를 다시 열었을 때 «#3» 이 어느 행인지 복원할 수 없다.
    refs = build_candidate_refs(selected)
    messages = stored + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": reply, "refs": refs},
    ]
    if conversation is None:
        saved = store.create_conversation({"title": default_title(question), "messages": messages})
    else:
        saved = store.replace_conversation(conversation["id"], {"messages": messages})
        if saved is None:  # 응답 생성 사이에 지워진 경우
            saved = store.create_conversation(
                {"title": default_title(question), "messages": messages}
            )

    return ChatResponse(
        conversation_id=saved["id"],
        reply=reply,
        summary_used=summary,
        candidates_used=len(selected),
        model=model_name,
        answer_source=answer_source,
        selection_basis=basis,
        candidate_refs=refs,
    )
