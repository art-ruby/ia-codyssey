// S05 비서에게 묻기(T07.04): 질문·로딩·근거 카드·숫자 출처·새 대화·저장 실패 시 다시 저장.
// 화면 위에는 현재 모드의 기본 숫자 요약을 늘 보이고 답변마다 새로 받는다. 질문이 다른 지표·기간·출처를 고르면
// 답변 카드에 '질문 조건 요약'으로 따로 보인다. 모든 문자열은 textContent로만 넣는다.
import { request } from "../api.js";
import { statsText, trendText } from "../activity-format.js";
import {
  QUESTION_LIMIT, basisText, chatFailureText, relatedText, sourceStatus, summaryCondition, summaryHeading, toTurns,
} from "../chat-format.js";
import { el } from "../priority.js";
import { singleFlight } from "../single-flight.js";

// 대화 기록 화면에서 '열기'를 누르면 이 값을 정하고 #ask로 옮긴다(모드별로 기억).
const opening = { personal: null, sample: null };
export function openConversation(mode, conversationId) {
  opening[mode] = conversationId;
  location.hash = "#ask";
}

function tag(text, tone = "") {
  return el("span", { class: tone ? `tag ${tone}` : "tag", text });
}

function virtualTag(summary) {
  return summary.source === "sample" ? tag("가상 기록", "amber") : tag("실제 값", "mint");
}

function summaryBlock(summary) {
  return el("div", { class: "chat-summary" },
    el("div", { class: "analysis-head" }, el("strong", { text: summaryHeading(summary) }), tag(summary.label), virtualTag(summary)),
    el("p", { class: "field-note", text: summaryCondition(summary) }),
    el("p", { class: "activity-stats", text: statsText(summary) }),
    el("p", { class: "activity-trend", text: trendText(summary.trend) }));
}

function sourceCard(source) {
  const status = sourceStatus(source.current_status);
  return el("li", { class: "related-card" },
    el("div", { class: "analysis-head" }, el("strong", { text: `자료 ${source.number} · ${source.display_title || "(제목 없음)"}` }),
      tag(basisText(source.basis), source.basis === "link_only" ? "amber" : ""),
      status ? tag(status[0], status[1]) : null),
    source.url ? el("p", { class: "url field-note", text: source.url }) : null);
}

// 답변 카드: 한계 → 원문에서 확인한 내용 → 해석·제안 → 근거 자료 → 관련 자료 → 숫자 출처.
function answerCard(answer) {
  const a = answer.answer || { from_materials: answer.content || "", interpretation: "", limitations: [] };
  const sections = [];
  if (a.limitations && a.limitations.length) {
    sections.push(el("div", { class: "analysis-caution" }, el("strong", { text: "한계" }),
      el("ul", {}, ...a.limitations.map((t) => el("li", { text: t })))));
  }
  sections.push(el("div", { class: "detail-field" }, el("span", { class: "detail-label", text: "자료에서 확인한 내용" }),
    el("p", { class: "detail-text", text: a.from_materials || "자료에서 확인한 내용이 없습니다." })));
  if (a.interpretation) {
    sections.push(el("div", { class: "detail-field ai-suggestion" },
      el("span", { class: "detail-label", text: "비서의 해석·제안(사실 확인 전)" }), el("p", { class: "detail-text", text: a.interpretation })));
  }
  const sources = answer.sources || [];
  sections.push(el("div", { class: "detail-field" }, el("span", { class: "detail-label", text: `근거 자료 ${sources.length}건` }),
    sources.length ? el("ul", { class: "related-list" }, ...sources.map(sourceCard))
      : el("p", { class: "field-note", text: "이 답변이 근거로 쓴 보관 자료가 없습니다." })));
  if (answer.related && answer.related.length) {
    sections.push(el("div", { class: "detail-field" }, el("span", { class: "detail-label", text: "관련 자료" }),
      el("ul", {}, ...answer.related.map((r) => el("li", {},
        el("span", { text: r.numbers.map((n) => `자료 ${n}`).join(" ↔ ") }),
        tag(relatedText(r.status), r.status === "user_confirmed" ? "mint" : ""))))));
  }
  if (answer.numbers && answer.numbers.length) {
    sections.push(el("div", { class: "detail-field" }, el("span", { class: "detail-label", text: "답변에 쓴 숫자(서버 요약)" }),
      ...answer.numbers.map(summaryBlock)));
  }
  return el("div", { class: "chat-answer" }, ...sections);
}

// root: 화면 영역, ctx: { mode, isCurrent(), onError(error, retry) }
export function renderAsk(root, ctx) {
  const api = (path, options = {}) => request(path, { mode: ctx.mode, ...options });
  let conversationId = opening[ctx.mode];
  opening[ctx.mode] = null;

  const summaryPanel = el("section", { class: "panel chat-summary-panel", "aria-live": "polite" },
    el("p", { class: "form-status", text: "숫자 요약을 불러오는 중…" }));
  const head = el("p", { class: "field-note" });
  const newButton = el("button", { class: "button secondary small", type: "button", text: "새 대화" });
  const turns = el("ol", { class: "chat-turns" });
  const question = el("textarea", { rows: "3", maxlength: String(QUESTION_LIMIT), "aria-label": "질문",
    placeholder: "예: 정산 API는 언제 종료돼? / 지난달 내가 입력한 보관 기록 알려줘" });
  const counter = el("span", { class: "field-note", text: `0 / ${QUESTION_LIMIT}자` });
  const send = el("button", { class: "button primary small", type: "submit", text: "질문하기" });
  const status = el("p", { class: "form-status", role: "status" });
  const form = el("form", { class: "panel form" },
    el("label", {}, el("span", { text: "질문" }), question),
    el("div", { class: "form-actions" }, send, counter, status));
  root.replaceChildren(summaryPanel,
    el("section", { class: "panel" }, el("div", { class: "analysis-head" }, el("strong", { text: "대화" }), newButton), head, turns),
    form);
  const flight = singleFlight();

  function showHead() {
    head.textContent = conversationId ? "이어지는 대화입니다. 답변은 자동으로 저장됩니다."
      : "새 대화입니다. 첫 답변을 받으면 자동으로 저장됩니다.";
  }

  async function loadSummary() {
    try {
      const summary = await api("/api/data/summary");
      if (!ctx.isCurrent()) return;
      summaryPanel.replaceChildren(
        el("div", { class: "analysis-head" }, el("h2", { class: "section-title", text: `현재 모드 기본 요약 · ${summary.label}` }),
          virtualTag(summary)),
        el("p", { class: "field-note", text: summaryCondition(summary) }),
        el("p", { class: "activity-stats", text: statsText(summary) }),
        el("p", { class: "activity-trend", text: trendText(summary.trend) }),
        el("p", { class: "field-note", text: summary.source === "sample"
          ? "표본 모드의 가상 기록입니다. 실제 사용량이 아닙니다." : "보관 승인·보관 완료·활성 자료만 센 실제 값입니다." }));
    } catch (error) {
      if (!ctx.isCurrent()) return;
      summaryPanel.replaceChildren(el("p", { class: "form-status", text: "숫자 요약을 불러오지 못했습니다." }));
      ctx.onError(error, loadSummary);
    }
  }

  function turnItem(text) {
    const answerSlot = el("div", {}, el("p", { class: "form-status", text: "답변을 만드는 중… (자료 검색 → AI 호출 → 저장)" }));
    turns.append(el("li", { class: "chat-turn" }, el("p", { class: "chat-question", text }), answerSlot));
    return answerSlot;
  }

  function showAnswer(slot, body) {
    conversationId = body.conversation_id;
    showHead();
    slot.replaceChildren(answerCard(body));
    loadSummary();
  }

  function pendingBox(slot, pendingId, detail) {
    const retry = el("button", { class: "button primary small", type: "button", text: "다시 저장" });
    const note = el("p", { class: "form-status", role: "status", text: detail });
    const box = el("div", { class: "analysis-confirm" }, note, pendingId ? el("div", { class: "form-actions" }, retry) : null);
    retry.addEventListener("click", () => flight([retry, send], async () => {
      note.textContent = "저장하는 중…";
      try {
        const saved = await api("/api/conversations", { method: "POST", body: { pending_id: pendingId } });
        if (!ctx.isCurrent()) return;
        conversationId = saved.conversation_id;
        showHead();
        box.replaceWith(el("p", { class: "field-note", text: saved.moved_to_new
          ? "원래 대화가 없어 새 대화로 저장했습니다." : "대화에 저장했습니다." }));
      } catch (error) {
        if (!ctx.isCurrent()) return;
        if (error.kind === "http" && error.status === 404) note.textContent = "이미 저장했거나 버린 답변입니다. 대화 기록에서 확인하세요.";
        else {
          note.textContent = "다시 저장하지 못했습니다.";
          ctx.onError(error, () => retry.click());
        }
      }
    }));
    slot.append(box);
  }

  // 실패 처리. save_failed는 답을 받았으므로 답과 '다시 저장'을 보인다(AI 재호출 없음).
  // 원인을 알 수 있는 실패는 그 자리에 적고, 연결 끊김 등은 같은 요청 키로 다시 보낸다(서버가 한 번만 처리).
  function showFailure(slot, error) {
    if (error.data && error.data.reason === "save_failed") {
      slot.replaceChildren(answerCard(error.data));
      pendingBox(slot, error.data.pending_id, error.data.detail);
      return;
    }
    const text = chatFailureText(error);
    slot.replaceChildren(el("p", { class: "form-status", text: text || "질문을 처리하지 못했습니다." }));
    if (!text && error.retry) ctx.onError(error, () => flight([send], () => sendTurn(slot, error.retry)));
    else if (!text) ctx.onError(error, () => {});
  }

  async function sendTurn(slot, call) {
    slot.replaceChildren(el("p", { class: "form-status", text: "답변을 기다리는 중…" }));
    try {
      const body = await call();
      if (!ctx.isCurrent()) return;
      showAnswer(slot, body);
      return true;
    } catch (error) {
      if (!ctx.isCurrent()) return;
      showFailure(slot, error);
      return false;
    }
  }

  async function ask(text) {
    status.textContent = "";
    const slot = turnItem(text);
    const ok = await sendTurn(slot, () => api("/api/chat", { method: "POST",
      body: conversationId ? { question: text, conversation_id: conversationId } : { question: text } }));
    if (ok) {
      question.value = "";
      counter.textContent = `0 / ${QUESTION_LIMIT}자`;
    }
  }

  async function loadConversation(id) {
    status.textContent = "대화를 불러오는 중…";
    try {
      const conv = await api(`/api/conversations/${encodeURIComponent(id)}`);
      if (!ctx.isCurrent()) return;
      turns.replaceChildren();
      for (const turn of toTurns(conv.messages)) {
        turnItem(turn.question).replaceChildren(turn.answer ? answerCard(turn.answer)
          : el("p", { class: "field-note", text: "답변이 저장되지 않았습니다." }));
      }
      for (const pending of conv.pending) {
        const slot = turnItem(pending.question);
        slot.replaceChildren();
        pendingBox(slot, pending.id, "답변은 받았지만 대화에 저장하지 못했습니다. 다시 저장하세요.");
      }
      status.textContent = `'${conv.title || "제목 없음"}' 대화를 불러왔습니다. 출처마다 지금 자료 상태를 함께 보여 줍니다.`;
    } catch (error) {
      if (!ctx.isCurrent()) return;
      conversationId = null;
      showHead();
      if (error.kind === "http" && error.status === 404) status.textContent = "대화를 찾을 수 없습니다(삭제됐거나 다른 모드의 대화).";
      else {
        status.textContent = "대화를 불러오지 못했습니다.";
        ctx.onError(error, () => loadConversation(id));
      }
    }
  }

  question.addEventListener("input", () => { counter.textContent = `${question.value.length} / ${QUESTION_LIMIT}자`; });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = question.value.trim();
    if (!text) {
      status.textContent = "질문을 입력하세요.";
      return;
    }
    flight([send, newButton], () => ask(text));
  });
  newButton.addEventListener("click", () => {
    conversationId = null;
    turns.replaceChildren();
    status.textContent = "";
    showHead();
    question.focus();
  });

  showHead();
  loadSummary();
  if (conversationId) loadConversation(conversationId);
}
