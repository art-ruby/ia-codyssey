"""AI Decision Assistant.

명세 5절의 흐름을 그대로 구현한다:
  질문 → Summary 조회 → 관련 후보 조회 → System Prompt 주입 → GPT 호출 → 저장

가장 중요한 제약은 '데이터에 없는 사실을 RADAR 데이터인 것처럼 만들지 않는다'
이다. 이를 프롬프트 문구 하나에 맡기지 않고 세 겹으로 막는다.

  1) 후보를 번호가 붙은 목록으로 주고, 답변에서 그 번호를 인용하게 한다.
  2) 표본(sample)과 실측(radar)을 행마다 표시해, AI 가 둘을 섞어 말하지 못하게 한다.
  3) 키가 없을 때 그럴듯한 문장을 지어내는 대신 계산 결과만 돌려주는
     규칙 기반 응답으로 떨어진다. '조용히 가짜 답'이 최악이기 때문이다.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..config import Settings
from ..models.schemas import Summary

MAX_CANDIDATES_IN_PROMPT = 25
MAX_HISTORY_TURNS = 8

# 질문에 흔히 섞이는 낱말. 주제어로 세면 «없는 채널»에도 일치가 났다고 잘못
# 판정한다. 형태소 분석기를 들이지 않고 이 목록만으로 막는다(명세 13절).
_QUERY_STOPWORDS = {
    "채널", "후보", "후보가", "후보는", "후보를", "소재", "소재가", "데이터",
    "알려줘", "알려줘.", "보여줘", "추천", "추천해줘", "해줘", "있어", "있어?",
    "있다면", "있나", "뭐야", "무엇", "무엇이야", "어떤", "중에", "중에서",
    "가장", "제일", "높은", "낮은", "최근", "오늘", "지금", "그리고", "관련",
    "것을", "것은", "이유", "왜", "설명", "정리", "목록", "전체", "상위",
}

SYSTEM_RULES = """당신은 RADAR Decision Assistant다. 유튜브 콘텐츠 소재 후보에 대해
MAKE / WATCH / SKIP 판단을 돕는다.

지켜야 할 규칙:
1. 아래 [데이터 요약]과 [후보 목록]에 있는 내용만 근거로 답한다.
2. 목록에 없는 영상·채널·수치를 RADAR 데이터인 것처럼 말하지 않는다.
   모르면 "저장된 데이터에는 없습니다"라고 분명히 말한다.
3. 특정 후보를 언급할 때는 반드시 목록의 번호(#3 형식)를 함께 쓴다.
   번호는 **이번 답변의 [후보 목록]** 기준이다. 목록은 질문마다 새로 매겨지므로
   이전 답변에서 쓴 번호를 다시 쓰지 않는다. 목록에 없는 번호를 만들지 않는다.
4. [표본] 표시가 붙은 행은 실제 관측이 아니라 모사 데이터다. 실측과 섞어
   단정하지 말고, 표본 기반 판단임을 밝힌다.
5. MAKE / WATCH / SKIP 을 제안할 수 있지만 최종 결정은 사용자가 한다.
   당신의 제안이 곧 제작 실행이 아니라는 점을 전제로 말한다.
6. 일반적인 유튜브 조언이 아니라 이 데이터에 대한 답을 한다.
7. 간결하게 답한다. 근거 수치를 함께 제시한다.

특정 후보를 추천하거나 판정을 논할 때는 아래 네 줄 구조를 지킨다.
«근거 데이터»는 목록에 있는 값만 옮기고, «판단 이유»는 그 값에서 끌어낸
해석이다. 둘을 섞지 않는다 — 관찰과 해석은 다르다.

    후보: #번호 제목
    판정 제안: MAKE | WATCH | SKIP
    근거 데이터: 점수 · 채널 · 날짜 · 현재 상태 (목록의 값 그대로)
    판단 이유: 위 수치에서 끌어낸 해석 한두 문장"""


def _decision_text(raw: Any) -> str:
    value = getattr(raw, "value", raw)
    return value if value in ("MAKE", "WATCH", "SKIP") else "미정"


def _source_text(raw: Any) -> str:
    value = getattr(raw, "value", raw) or "manual"
    return {"sample": "[표본]", "radar": "[실측]", "manual": "[수동]"}.get(value, "[수동]")


def select_candidates(
    question: str, candidates: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], str]:
    """질문과 관련된 후보를 고른다. (선별 결과, 무엇을 근거로 골랐는지) 를 돌려준다.

    임베딩이나 별도 검색 엔진을 두지 않는다(명세 13절: 새 엔진 개발 제외).

    ⚠️ 선별 근거를 **반드시 함께 돌려준다.** 근거를 숨기고 점수 상위를 조용히
    끼워 넣으면 "money_retirement 채널 후보 알려줘"(없는 채널)에 다른 채널
    후보가 답으로 제시된다. 후보 자체는 진짜여도 «질문에 대한 답»으로는 거짓이다.

    반대로 사용자 의도를 추측해 «없습니다»라고 단정하지도 않는다. 우리가 아는
    것은 «무엇으로 골랐는가»뿐이므로 그것만 사실대로 말하고, 질문한 대상이
    목록에 있는지는 번호가 붙은 목록을 보고 모델·사용자가 판단하게 한다.

    근거:
      decision  — 질문에 MAKE/WATCH/SKIP 이 있어 그 상태로 걸렀다
      keyword   — 질문의 낱말이 채널/주제/제목과 일치했다
      top_score — 일치가 없어 점수 상위로 채웠다
    """
    lowered = question.lower()

    # ① 상태 질의를 먼저 본다. "MAKE 후보만 보여줘"는 주제 검색이 아니다.
    wanted = [d for d in ("MAKE", "WATCH", "SKIP") if d in question.upper()]
    if wanted:
        picked = [
            item for item in candidates
            if _decision_text(item.get("decision")) in wanted
        ]
        picked.sort(key=lambda item: float(item.get("value") or 0), reverse=True)
        if picked:
            return picked[:MAX_CANDIDATES_IN_PROMPT], "decision"

    words = {
        w.strip("?!.,·")
        for w in lowered.replace(",", " ").split()
        if len(w.strip("?!.,·")) >= 2
    } - _QUERY_STOPWORDS

    def relevance(item: dict[str, Any]) -> int:
        # memo 는 넣지 않는다. 자유 서술이라 «채널 적합성은 높으나…» 같은 문장이
        # 질문의 일반어 '채널'과 걸려 오탐을 만든다. 실제로 없는 채널을 물었을 때
        # 일치했다고 잘못 판정된 적이 있다. 신원 필드만 본다.
        haystack = " ".join(
            str(item.get(key) or "") for key in ("channel", "topic", "title")
        ).lower()
        return sum(1 for w in words if w in haystack)

    scored = [(relevance(item), float(item.get("value") or 0), item) for item in candidates]
    hits = [row for row in scored if row[0] > 0]
    basis = "keyword" if hits else "top_score"
    pool = hits if hits else scored
    pool.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [item for _, _, item in pool[:MAX_CANDIDATES_IN_PROMPT]], basis


def _date_text(raw: Any) -> str:
    return raw.strftime("%Y-%m-%d") if isinstance(raw, datetime) else str(raw or "")[:10]


def build_candidate_refs(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """프롬프트 번호(#N) ↔ 후보 id 대응표.

    번호는 build_context_block 과 **같은 enumerate(start=1)** 에서 나온다.
    두 함수가 같은 리스트를 같은 순서로 받는 한 어긋나지 않는다 — 테스트가 이를 고정한다.
    값은 저장소의 것을 그대로 옮긴다. 화면이 AI 가 적은 수치와 대조하는 기준이다.
    """
    refs: list[dict[str, Any]] = []
    for index, item in enumerate(candidates, start=1):
        source = getattr(item.get("source"), "value", item.get("source")) or "manual"
        refs.append(
            {
                "index": index,
                "id": str(item.get("id")),
                "title": item.get("title"),
                "channel": item.get("channel"),
                "topic": item.get("topic"),
                "value": float(item.get("value") or 0),
                "date": _date_text(item.get("date")),
                "decision": _decision_text(item.get("decision")),
                "source": source,
            }
        )
    return refs


def build_context_block(
    summary: Summary, candidates: list[dict[str, Any]], basis: str = "keyword"
) -> str:
    lines = [
        "[데이터 요약]",
        f"- 기간: {summary.period}",
        f"- 후보 수: {summary.count}건",
        f"- 점수: 평균 {summary.metrics.average_score} / 최고 {summary.metrics.max_score} / 최저 {summary.metrics.min_score}",
        f"- 추세: {summary.trend}",
        f"- 결정: MAKE {summary.decisions.MAKE} · WATCH {summary.decisions.WATCH} · "
        f"SKIP {summary.decisions.SKIP} · 미정 {summary.decisions.PENDING}",
        f"- 상위 주제: {', '.join(summary.top_topics) if summary.top_topics else '없음'}",
        f"- 데이터 출처 구성: {summary.source_mix or '없음'}",
        "",
    ]
    if basis == "decision":
        lines.append(f"[후보 목록] 질문이 지정한 판단 상태로 걸러낸 {len(candidates)}건 (점수순)")
    elif basis == "keyword":
        lines.append(f"[후보 목록] 질문의 낱말과 일치한 {len(candidates)}건 (관련도·점수순)")
    else:
        # 무엇으로 골랐는지만 사실대로 말한다. 사용자가 물은 대상이 있는지 없는지는
        # 아래 번호 목록을 보고 판단하게 한다. 우리가 대신 단정하지 않는다.
        lines += [
            f"[후보 목록] ⚠️ 질문의 낱말과 일치한 후보가 없어 점수 상위 {len(candidates)}건으로 채웠다.",
            "이 목록은 질문에 대한 검색 결과가 아니다.",
            "사용자가 특정 채널·주제를 물었는데 아래 목록에 없다면,",
            "'저장된 데이터에는 없습니다'라고 먼저 분명히 말하라.",
        ]
    if not candidates:
        lines.append("- (없음)")
    for index, item in enumerate(candidates, start=1):
        when_text = _date_text(item.get("date"))
        lines.append(
            f"#{index} {_source_text(item.get('source'))} "
            f"{item.get('title') or item.get('topic') or '(제목 없음)'} "
            f"| 채널 {item.get('channel') or '-'} | 주제 {item.get('topic') or '-'} "
            f"| 점수 {item.get('value')} | {when_text} | 결정 {_decision_text(item.get('decision'))}"
        )
    return "\n".join(lines)


def _suggest(score: float, average: float, current: Any) -> tuple[str, str]:
    """점수와 전체 평균만으로 낸 기계적 제안.

    새 scoring engine 이 아니다 — RADAR 점수를 평균과 견줘 구간만 나눈다.
    이미 사용자가 정한 판단이 있으면 그것을 뒤집지 않고 그대로 존중한다.
    """
    decided = _decision_text(current)
    if decided != "미정":
        return decided, f"사용자가 이미 {decided} 로 확정한 후보다. 제안이 이를 대체하지 않는다."
    gap = score - average
    if gap >= 15:
        return "MAKE", f"전체 평균 {average}점 대비 +{gap:.1f}점으로 상위 구간이다."
    if gap >= 0:
        return "WATCH", f"전체 평균 {average}점 대비 +{gap:.1f}점으로 평균 부근이다. 추가 관찰이 필요하다."
    return "SKIP", f"전체 평균 {average}점 대비 {gap:.1f}점으로 하위 구간이다."


def _rule_based_reply(
    question: str, summary: Summary, candidates: list[dict[str, Any]], basis: str = "keyword"
) -> str:
    """OpenAI 키가 없을 때.

    계산된 사실만 돌려주되, 실제 AI 응답과 **같은 네 줄 구조**로 낸다.
    형식이 같아야 키를 넣었을 때 화면이 달라지지 않고, 키 없이도 흐름을
    검증할 수 있다. 다만 이것이 AI 해석이 아니라는 사실은 첫 줄에 밝힌다.
    """
    head = (
        "⚠️ OPENAI_API_KEY 가 없어 규칙 기반으로 답합니다. "
        "아래 «판단 이유»는 저장된 수치를 비교한 결과이며 AI 해석이 아닙니다.\n\n"
    )
    body = [
        f"질문: {question}",
        "",
        "[데이터 요약]",
        f"- 기간 {summary.period}, 후보 {summary.count}건",
        f"- 평균 {summary.metrics.average_score}점 (최고 {summary.metrics.max_score} / 최저 {summary.metrics.min_score})",
        f"- {summary.trend}",
        f"- MAKE {summary.decisions.MAKE} · WATCH {summary.decisions.WATCH} · "
        f"SKIP {summary.decisions.SKIP} · 미정 {summary.decisions.PENDING}",
    ]

    if not candidates:
        body += ["", "관련된 후보가 저장된 데이터에 없습니다. 없는 소재를 만들어 답하지 않습니다."]
        return head + "\n".join(body)

    average = summary.metrics.average_score
    n = min(3, len(candidates))
    if basis == "decision":
        body += ["", f"[질문이 지정한 판단 상태의 후보 상위 {n}건]"]
    elif basis == "keyword":
        body += ["", f"[질문의 낱말과 일치한 후보 상위 {n}건]"]
    else:
        body += [
            "",
            f"[점수 상위 {n}건] ❗ 질문의 낱말과 일치한 후보가 없어 점수순으로 채웠습니다.",
            "   특정 채널·주제를 찾으셨다면 저장된 데이터에 없는 것입니다.",
        ]
    for index, item in enumerate(candidates[:3], start=1):
        score = float(item.get("value") or 0)
        verdict, why = _suggest(score, average, item.get("decision"))
        when = item.get("date")
        when_text = when.strftime("%Y-%m-%d") if isinstance(when, datetime) else str(when)[:10]
        body += [
            "",
            f"후보: #{index} {item.get('title') or item.get('topic') or '(제목 없음)'}",
            f"판정 제안: {verdict}",
            f"근거 데이터: {score}점 · {item.get('channel') or '-'} · {when_text} · "
            f"현재 상태 {_decision_text(item.get('decision'))} · {_source_text(item.get('source'))}",
            f"판단 이유: {why}",
        ]
    body += ["", "※ 제안일 뿐이며 최종 확정은 화면에서 사용자가 합니다."]
    return head + "\n".join(body)


def generate_reply(
    *,
    question: str,
    summary: Summary,
    candidates: list[dict[str, Any]],
    history: list[dict[str, str]],
    settings: Settings,
    basis: str = "keyword",
) -> tuple[str, str, str]:
    """(답변, 사용한 모델명, 답변 출처) 를 돌려준다.

    출처를 문자열 모델명으로 추측하게 두지 않는다. 화면이 «AI 응답»과
    «대체 응답»을 확실히 갈라 보여줘야 하기 때문이다.
    """
    context = build_context_block(summary, candidates, basis)

    if not settings.openai_enabled:
        return (
            _rule_based_reply(question, summary, candidates, basis),
            "rule-based (no API key)",
            "rule_based",
        )

    try:
        from openai import OpenAI
    except ImportError:
        # 키는 넣었는데 패키지가 없는 상태. 여기서 막지 않으면 500 만 나가고
        # 사용자는 원인을 모른다. 해야 할 일을 그대로 알려준다.
        return (
            "⚠️ OPENAI_API_KEY 는 설정됐지만 openai 패키지가 설치되어 있지 않습니다.\n"
            "   backend 디렉터리에서 `pip install -r requirements.txt` 를 실행하세요.\n\n"
            + _rule_based_reply(question, summary, candidates, basis),
            "error-missing-package",
            "missing_package",
        )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_RULES + "\n\n" + context}
    ]
    # 직전 대화는 맥락 유지를 위해 넣되, 오래된 것은 자른다.
    for turn in history[-MAX_HISTORY_TURNS:]:
        role = turn.get("role")
        if role in ("user", "assistant") and turn.get("content"):
            messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": question})

    try:
        # 클라이언트 생성도 try 안에 둔다. 잘못된 키 형식·프록시 문제는 호출이
        # 아니라 **생성자**에서 터지는데, 그것이 밖에 있으면 500 만 나간다.
        #
        # base_url 이 있으면 OpenAI 호환 프록시로 보낸다(과정 제공 게이트웨이 등).
        # 지정하지 않으면 SDK 기본값인 api.openai.com 으로 가므로, 프록시용
        # virtual-key 를 쓰면서 이걸 비워 두면 401 이 난다.
        client = (
            OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
            if settings.openai_base_url
            else OpenAI(api_key=settings.openai_api_key)
        )
        # temperature 는 넣지 않는다. 게이트웨이 뒤 일부 모델(gpt-5-mini 등
        # reasoning 계열)이 이 파라미터 자체를 거부해 502(Provider returned
        # an error)로 떨어지는 걸 실측으로 확인했다. 결정성이 필요하면 모델
        # 기본값에 맡긴다.
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            max_tokens=settings.openai_max_tokens,
        )
    except Exception as exc:  # noqa: BLE001 - 사용자에게 원인을 그대로 보여준다
        fallback = _rule_based_reply(question, summary, candidates, basis)
        return (
            f"⚠️ OpenAI 호출 실패: {str(exc)[:200]}\n\n{fallback}",
            "error-fallback",
            "error_fallback",
        )

    reply = (completion.choices[0].message.content or "").strip()
    return reply or "(빈 응답)", settings.openai_model, "openai"


def default_title(question: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%m-%d %H:%M")
    trimmed = question.strip().splitlines()[0][:40]
    return f"{stamp} {trimmed}" if trimmed else f"{stamp} 대화"
