// 오늘·AI 동향 공통(T04.04): 최종 중요도 표시, 대응 필요·학습 자료 구분, 상태 표시, 자료 카드.
// 정렬은 서버(`GET /api/materials/priority`)가 한다. 화면은 받은 순서를 그대로 쓰고 묶기만 한다.
// 외부 인기 숫자나 예약 브리핑 문구를 쓰지 않는다. 모든 문자열은 textContent로만 넣는다.

const IMPORTANCE = { high: "높음", medium: "보통", low: "낮음" };
export const IMPORTANCE_OPTIONS = [["", "판단 보류"], ["high", "높음"], ["medium", "보통"], ["low", "낮음"]];
export const TODAY_LIMIT = 3;

// "높음 · 내가 정함" / "보통 · AI 제안" / "판단 보류"
export function importanceText(m) {
  if (!m.final_importance) return "판단 보류";
  return `${IMPORTANCE[m.final_importance]} · ${m.importance_source === "user" ? "내가 정함" : "AI 제안"}`;
}

export function actionText(m) {
  if (m.needs_action === true) return "대응 필요";
  if (m.needs_action === false) return "학습 자료";
  return "대응 여부 미확인";
}

// 자료 상태 표시. 미승인 자료에는 검토 대기를 붙인다(PRD S04).
export function stateTags(m) {
  const tags = [];
  if (m.review_status === "approved") tags.push(["보관됨", "mint"]);
  else if (m.review_status === "later") tags.push(["나중에 보기", ""]);
  else tags.push(["검토 대기", "amber"]);
  if (m.ai_excluded) tags.push(["AI 분석 제외", ""]);
  return tags;
}

// 오늘: 같은 정렬에서 높음·보통만 최대 3건.
export function todayPicks(items) {
  return items.filter((m) => m.final_importance === "high" || m.final_importance === "medium").slice(0, TODAY_LIMIT);
}

// AI 동향: 서버 순서를 유지한 채 대응 필요와 그 밖(학습 자료·미확인)으로 나눈다.
export function trendGroups(items) {
  return { action: items.filter((m) => m.needs_action === true), learning: items.filter((m) => m.needs_action !== true) };
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (name === "text") node.textContent = value;
    else if (name === "value") node.value = value;
    else node.setAttribute(name, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

// 자료 카드. editor가 있으면 중요도를 바로 고칠 수 있다(AI 동향).
// AI 요약은 지금 내용 기준으로 끝난 결과일 때만 보여준다.
export function priorityCard(m, editor = null) {
  const tags = el("div", { class: "material-meta" },
    el("span", { class: `tag ${m.final_importance === "high" ? "amber" : "mint"}`, text: importanceText(m) }),
    m.final_importance ? el("span", { class: "tag", text: actionText(m) }) : null,
    ...stateTags(m).map(([text, tone]) => el("span", { class: `tag ${tone}`, text })));
  const summary = m.analysis_status === "done" && !m.analysis_outdated ? m.ai_summary : null;
  return el("li", { class: "priority-card", "data-id": m.id },
    el("strong", { text: m.display_title || "(제목 없음)" }),
    tags,
    m.reason ? el("p", { class: "priority-reason", text: `이유: ${m.reason}` }) : null,
    summary ? el("p", { class: "priority-summary", text: `AI 요약(사실 확인 안 됨): ${summary}` }) : null,
    editor);
}
