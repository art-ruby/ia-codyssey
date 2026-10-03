// S04 AI 동향: 사용자 제공 자료를 대응 필요·학습 자료·판단 보류로 나눠 중요 이유와 순서를 보여준다(T04.04).
// 중요도를 바로 고치면 저장 후 서버 순서로 다시 그린다. 외부 인기 수치를 표시하지 않는다.
import { request } from "../api.js";
import { IMPORTANCE_OPTIONS, el, priorityCard, trendGroups } from "../priority.js";
import { newsPanel } from "./news-panel.js";

// root: 화면 영역, ctx: { mode, isCurrent(), onError(error, retry) }
export function renderTrends(root, ctx) {
  const api = (path, options = {}) => request(path, { mode: ctx.mode, ...options });
  const status = el("p", { class: "form-status", role: "status", text: "불러오는 중…" });
  const body = el("div");
  root.replaceChildren(newsPanel(ctx), status, body);

  async function load(message = "") {
    try {
      const view = await api("/api/materials/priority");
      if (!ctx.isCurrent()) return;
      render(view);
      status.textContent = [message, view.truncated ? `최근 ${view.scanned}건까지만 비교했습니다.` : ""]
        .filter(Boolean).join(" ");
    } catch (error) {
      if (!ctx.isCurrent()) return;
      status.textContent = "";
      ctx.onError(error, () => load(message));
    }
  }

  // 사용자 최종 중요도 수정. AI 제안은 그대로 두고 user_importance만 바꾼다(PRD §6.3).
  function editor(m) {
    const select = el("select", { "aria-label": `${m.display_title} 중요도` },
      ...IMPORTANCE_OPTIONS.map(([value, label]) => el("option", { value, text: label })));
    select.value = m.user_importance || "";
    const hint = m.importance_source === "ai"
      ? el("span", { class: "field-note", text: "지금은 AI 제안을 따릅니다. 고르면 내 판단으로 저장됩니다." }) : null;
    select.addEventListener("change", async () => {
      select.disabled = true;
      status.textContent = "중요도를 저장하는 중…";
      try {
        await api(`/api/materials/${encodeURIComponent(m.id)}`,
          { method: "PUT", body: { expected_version: m.version, user_importance: select.value || null } });
        if (!ctx.isCurrent()) return;
        await load("중요도를 저장했고 순서를 다시 맞췄습니다.");
      } catch (error) {
        if (!ctx.isCurrent()) return;
        if (error.kind === "http" && [404, 409, 422].includes(error.status)) {
          await load(`${error.detail} 최신 내용으로 다시 불러왔습니다.`);
        } else {
          select.disabled = false;
          status.textContent = "";
          ctx.onError(error, () => load());
        }
      }
    });
    return el("label", { class: "priority-edit" }, el("span", { text: "내 중요도" }), select, hint);
  }

  function section(title, note, items, emptyText) {
    return el("section", { class: "panel" },
      el("h2", { class: "section-title", text: `${title} ${items.length}건` }),
      el("p", { class: "field-note", text: note }),
      items.length ? el("ul", { class: "priority-list" }, ...items.map((m) => priorityCard(m, editor(m))))
        : el("p", { class: "empty-row", text: emptyText }));
  }

  function render(view) {
    if (!view.items.length && !view.pending.length) {
      body.replaceChildren(el("section", { class: "panel empty" },
        el("strong", { text: "아직 자료가 없습니다" }),
        el("p", { text: "받은 자료에서 접수하고 분석을 시작하면, 내 자료 중 대응이 필요한 것과 학습 자료를 나눠 보여줍니다." }),
        el("a", { class: "button secondary small", href: "#inbox", text: "받은 자료로 가기" })));
      return;
    }
    const { action, learning } = trendGroups(view.items);
    body.replaceChildren(
      section("대응 필요", "자료에 기한·변경·종료·요청이 적혀 있다고 AI가 판단한 자료입니다. 같은 중요도 안에서 먼저 놓입니다.",
        action, "대응이 필요하다고 판단된 자료가 없습니다."),
      section("학습 자료", "참고·학습용 자료입니다. '대응 여부 미확인'은 이전 분석 결과라 구분 정보가 없는 자료입니다.",
        learning, "학습 자료가 없습니다."),
      section("판단 보류", "내 중요도도, 지금 내용 기준의 AI 제안도 없는 자료입니다. 분석하거나 직접 중요도를 고르세요.",
        view.pending, "판단 보류 자료가 없습니다."));
  }

  load();
}
