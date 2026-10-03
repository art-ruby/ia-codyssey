// 채팅·대화 기록 표시용 순수 함수(T07.04). 화면(ask.js·conversations.js)과 테스트가 함께 쓴다.
// 출처·관련 자료·숫자 요약의 상태 이름을 한곳에서 정한다. 서버가 준 label·기간은 그대로 쓴다.

// 근거로 쓴 방식: 본문을 실제로 읽었는지(URL만 있는 자료는 본문 미확인).
export function basisText(basis) {
  return basis === "link_only" ? "링크만 · 본문 미확인" : "본문 확인";
}

// 대화 기록의 출처가 지금 어떤 상태인가(GET /api/conversations/{id}의 current_status).
const SOURCE_STATUS = {
  available: ["현재 보관 중", "mint"],
  trashed: ["지금은 휴지통", "amber"],
  deleted: ["삭제된 자료", "amber"],
  unapproved: ["지금은 미승인", "amber"],
  not_kept: ["보관 상태 아님", "amber"],
  ai_excluded: ["지금은 AI 분석 제외", "amber"],
};
export function sourceStatus(status) {
  return SOURCE_STATUS[status] || null; // 방금 받은 답변에는 현재 상태가 없다
}

// 관련 자료: 사용자가 확정한 연결과 AI 제안을 다르게 적는다(제안을 확정처럼 보이지 않게).
export function relatedText(status) {
  return status === "user_confirmed" ? "내가 연결한 관련 자료" : "AI 제안 · 확정 아님";
}

const METRICS = { kept_count: "보관 건수", received_count: "접수 건수" };
const SOURCES = { actual: "실제 값", manual: "사용자 입력 기록", sample: "가상 기록(표본)" };

// "기본 요약" / "질문 조건 요약" 머리말과 출처·지표·기간 조건.
export function summaryHeading(summary) {
  return summary.role === "question" ? "질문 조건 요약" : "기본 요약";
}

export function summaryCondition(summary) {
  const period = summary.period ? `${summary.period.start} ~ ${summary.period.end}` : "기간 없음";
  return `출처 ${SOURCES[summary.source] || summary.source} · 지표 ${METRICS[summary.metric_type] || summary.metric_type} · ${period}`;
}

// 채팅 실패를 원인별 문구로. null이면 화면 공통 오류 처리(연결 끊김·로그인 만료 등)에 맡긴다.
// save_failed는 답을 받았으므로 여기서 다루지 않는다(답과 '다시 저장'을 보여 준다).
export function chatFailureText(error) {
  const data = error && error.data;
  const reason = data && data.reason;
  if (reason === "search_failed") return "자료를 검색하지 못했습니다. 저장한 자료가 없다는 뜻이 아닙니다. 잠시 뒤 다시 질문하세요.";
  if (reason === "quota_exceeded") return "오늘 AI 요청 한도에 도달했습니다. 서울 시간 자정 이후 다시 질문하세요.";
  if (reason === "provider_failed") return `AI 답변을 받지 못했습니다(${data.kind || "알 수 없는 오류"}). 대화는 저장하지 않았습니다.`;
  if (reason === "conversation_full") return "이 대화는 메시지 한도에 도달했습니다. 새 대화를 시작하세요.";
  if (error && error.kind === "http" && [404, 409, 422].includes(error.status)) return error.detail;
  return null;
}

export const QUESTION_LIMIT = 2000; // server/app/features/chat/schemas.py와 같다

// 대화 상세의 messages를 [질문, 답변] 묶음으로. 답변이 없는 질문은 답변 null.
export function toTurns(messages) {
  const turns = [];
  for (const message of messages) {
    if (message.role === "user") turns.push({ question: message.content, answer: null });
    else if (message.role === "assistant" && turns.length && !turns[turns.length - 1].answer) {
      turns[turns.length - 1].answer = message;
    }
  }
  return turns;
}
