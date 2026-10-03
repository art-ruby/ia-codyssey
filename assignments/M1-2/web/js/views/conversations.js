// S06 대화 기록(T07.04): 현재 모드의 대화 목록·불러오기·삭제와 저장하지 못한 답변(다시 저장·버리기).
// 불러오기는 '비서에게 묻기' 화면에서 열어 출처마다 지금 자료 상태를 보여 준다. 모든 문자열은 textContent로만 넣는다.
import { request } from "../api.js";
import { el } from "../priority.js";
import { singleFlight } from "../single-flight.js";
import { openConversation } from "./ask.js";

const SEOUL = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "short" });
const when = (iso) => (iso ? SEOUL.format(new Date(iso)) : "-");

// root: 화면 영역, ctx: { mode, isCurrent(), onError(error, retry) }
export function renderConversations(root, ctx) {
  const api = (path, options = {}) => request(path, { mode: ctx.mode, ...options });
  const status = el("p", { class: "form-status", role: "status", text: "불러오는 중…" });
  const pendingPanel = el("section", { class: "panel", hidden: "" });
  const list = el("ul", { class: "material-list" });
  const more = el("button", { class: "button secondary small", type: "button", text: "더 보기", hidden: "" });
  root.replaceChildren(pendingPanel,
    el("section", { class: "panel" },
      el("div", { class: "analysis-head" }, el("strong", { text: "대화 목록(최근 만든 순)" }),
        el("a", { class: "button primary small", href: "#ask", text: "새 대화 시작" })),
      el("p", { class: "field-note", text: ctx.mode === "sample" ? "표본 모드의 대화만 보입니다." : "개인 모드의 대화만 보입니다." }),
      status, list, more));
  const flight = singleFlight();
  let items = [];
  let nextCursor = null;

  async function load(cursor = null, note = "") {
    status.textContent = "불러오는 중…";
    try {
      const page = await api(`/api/conversations?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`);
      if (!ctx.isCurrent()) return;
      items = cursor ? [...items, ...page.items.filter((i) => !items.some((x) => x.id === i.id))] : page.items;
      nextCursor = page.next_cursor;
      if (!cursor) renderPending(page.pending);
      render();
      status.textContent = note;
    } catch (error) {
      if (!ctx.isCurrent()) return;
      status.textContent = "대화 목록을 불러오지 못했습니다.";
      ctx.onError(error, () => load(cursor, note));
    }
  }

  function render() {
    list.replaceChildren(...(items.length ? items.map(row)
      : [el("li", { class: "empty-row", text: "저장된 대화가 없습니다. '비서에게 묻기'에서 질문하면 자동으로 저장됩니다." })]));
    if (nextCursor) more.removeAttribute("hidden");
    else more.setAttribute("hidden", "");
  }

  function row(conv) {
    const open = el("button", { class: "button secondary small", type: "button", text: "열기" });
    const remove = el("button", { class: "button small danger", type: "button", text: "삭제" });
    const note = el("p", { class: "form-status", role: "status" });
    const li = el("li", { "data-id": conv.id },
      el("div", { class: "material-head" }, el("strong", { text: conv.title || "(제목 없음)" })),
      el("div", { class: "material-meta" },
        el("span", { text: `메시지 ${conv.message_count || 0}개` }),
        el("span", { text: `마지막 ${when(conv.last_message_at || conv.created_at)}` })),
      el("div", { class: "form-actions" }, open, remove, note));
    open.addEventListener("click", () => openConversation(ctx.mode, conv.id));
    remove.addEventListener("click", () => confirmDelete(li, conv, remove, note));
    return li;
  }

  // 지우기 전에 범위를 알린다(브라우저 확인 창 대신 화면 안에서 한 번 더 누른다).
  function confirmDelete(li, conv, remove, note) {
    if (li.querySelector(".analysis-confirm")) return;
    const yes = el("button", { class: "button primary small danger", type: "button", text: "대화 삭제 확인" });
    const no = el("button", { class: "button secondary small", type: "button", text: "취소" });
    const box = el("div", { class: "analysis-confirm" },
      el("p", { text: "이 대화의 질문·답변·인용문과 저장하지 못한 답변을 모두 지웁니다. 되돌릴 수 없습니다. 보관함의 자료는 지우지 않습니다." }),
      el("div", { class: "form-actions" }, yes, no));
    li.append(box);
    no.addEventListener("click", () => box.remove());
    yes.addEventListener("click", () => flight([yes, no, remove], async () => {
      note.textContent = "삭제하는 중…";
      try {
        await api(`/api/conversations/${encodeURIComponent(conv.id)}`, { method: "DELETE" });
        if (ctx.isCurrent()) load(null, "대화를 삭제했습니다.");
      } catch (error) {
        if (!ctx.isCurrent()) return;
        if (error.kind === "http" && error.status === 404) load(null, "이미 삭제된 대화입니다.");
        else {
          note.textContent = "삭제하지 못했습니다.";
          ctx.onError(error, () => yes.click());
        }
      }
    }));
  }

  function renderPending(pending) {
    if (!pending.length) {
      pendingPanel.setAttribute("hidden", "");
      pendingPanel.replaceChildren();
      return;
    }
    pendingPanel.removeAttribute("hidden");
    pendingPanel.replaceChildren(
      el("h2", { class: "section-title", text: `저장하지 못한 답변 ${pending.length}건` }),
      el("p", { class: "field-note", text: "답변은 받았지만 대화에 저장하지 못했습니다. 다시 저장해도 AI를 다시 부르지 않습니다." }),
      el("ul", { class: "material-list" }, ...pending.map(pendingRow)));
  }

  function pendingRow(p) {
    const save = el("button", { class: "button primary small", type: "button", text: "다시 저장" });
    const drop = el("button", { class: "button small danger", type: "button", text: "버리기" });
    const note = el("p", { class: "form-status", role: "status" });
    const li = el("li", {}, el("strong", { text: p.question || "(질문 없음)" }),
      el("div", { class: "material-meta" }, el("span", { text: when(p.created_at) }),
        el("span", { text: p.conversation_id ? "기존 대화에 이어 붙임" : "새 대화로 저장" })),
      el("div", { class: "form-actions" }, save, drop, note));
    save.addEventListener("click", () => flight([save, drop], async () => {
      note.textContent = "저장하는 중…";
      try {
        const saved = await api("/api/conversations", { method: "POST", body: { pending_id: p.id } });
        if (ctx.isCurrent()) load(null, saved.moved_to_new ? "원래 대화가 없어 새 대화로 저장했습니다." : "대화에 저장했습니다.");
      } catch (error) {
        if (!ctx.isCurrent()) return;
        if (error.kind === "http" && error.status === 404) load(null, "이미 저장했거나 버린 답변입니다.");
        else {
          note.textContent = "저장하지 못했습니다.";
          ctx.onError(error, () => save.click());
        }
      }
    }));
    drop.addEventListener("click", () => flight([save, drop], async () => {
      note.textContent = "버리는 중…";
      try {
        await api(`/api/conversations/pending/${encodeURIComponent(p.id)}`, { method: "DELETE" });
        if (ctx.isCurrent()) load(null, "저장하지 못한 답변을 버렸습니다.");
      } catch (error) {
        if (!ctx.isCurrent()) return;
        if (error.kind === "http" && error.status === 404) load(null, "이미 처리된 답변입니다.");
        else {
          note.textContent = "버리지 못했습니다.";
          ctx.onError(error, () => drop.click());
        }
      }
    }));
    return li;
  }

  more.addEventListener("click", () => flight([more], () => load(nextCursor)));
  load();
}
