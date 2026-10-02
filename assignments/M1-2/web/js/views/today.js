// S01 오늘: AI 동향과 같은 우선순위로 확인할 자료 최대 3건과 이유, 미검토·보관 수(T04.04), 숫자 요약(T06.04).
// 실제로 확인한 자료가 없으면 빈 상태만 보인다. 예약 브리핑이 실행된 것처럼 쓰지 않는다.
import { request } from "../api.js";
import { periodText, statsText, trendText } from "../activity-format.js";
import { el, priorityCard, todayPicks } from "../priority.js";

// root: 화면 영역, ctx: { mode, isCurrent(), onError(error, retry) }
export function renderToday(root, ctx) {
  const status = el("p", { class: "form-status", role: "status", text: "불러오는 중…" });
  const body = el("div");
  root.replaceChildren(body, status);

  async function load() {
    status.textContent = "불러오는 중…";
    try {
      // 숫자 요약은 현재 모드의 기본값(개인: 현재 보관 자료 수, 표본: 가상 보관 기록)을 매번 새로 받는다.
      const [view, numbers] = await Promise.all([
        request("/api/materials/priority", { mode: ctx.mode }),
        request("/api/data/summary", { mode: ctx.mode }),
      ]);
      if (!ctx.isCurrent()) return;
      render(view, numbers);
      status.textContent = view.truncated ? `최근 ${view.scanned}건까지만 비교했습니다.` : "";
    } catch (error) {
      if (!ctx.isCurrent()) return;
      status.textContent = "";
      ctx.onError(error, load);
    }
  }

  function render(view, numbers) {
    const picks = todayPicks(view.items);
    const total = view.items.length + view.pending.length;
    const counts = el("section", { class: "panel today-counts" },
      el("div", { class: "mini-line" }, el("span", { text: "검토 대기" }), el("strong", { text: `${view.counts.unreviewed}건` })),
      el("div", { class: "mini-line" }, el("span", { text: "보관한 자료" }), el("strong", { text: `${view.counts.kept}건` })),
      el("a", { class: "button secondary small", href: "#review", text: "검토·승인 열기" }));

    let main;
    if (!total) {
      main = el("section", { class: "panel empty" },
        el("strong", { text: "아직 자료가 없습니다" }),
        el("p", { text: "받은 자료에서 URL이나 텍스트를 접수하면, 중요도가 정해진 자료를 여기서 먼저 보여줍니다." }),
        el("a", { class: "button secondary small", href: "#inbox", text: "받은 자료로 가기" }));
    } else if (!picks.length) {
      main = el("section", { class: "panel empty" },
        el("strong", { text: "먼저 확인할 자료가 없습니다" }),
        el("p", { text: `중요도가 높음·보통인 자료가 없습니다. 판단 보류 ${view.pending.length}건은 AI 동향에서 중요도를 정할 수 있습니다.` }),
        el("a", { class: "button secondary small", href: "#trends", text: "AI 동향 열기" }));
    } else {
      main = el("section", { class: "panel" },
        el("h2", { class: "section-title", text: `먼저 확인할 자료 ${picks.length}건` }),
        el("p", { class: "field-note", text: "최종 중요도 → 대응 필요 → 최신 접수 순입니다. AI 제안은 사실 확인 전 제안입니다." }),
        el("ul", { class: "priority-list" }, ...picks.map((m) => priorityCard(m))),
        el("a", { class: "button secondary small", href: "#trends", text: "전체 순서 보기" }));
    }
    const summaryCard = el("section", { class: "panel today-numbers" },
      el("h2", { class: "section-title", text: numbers.label }),
      el("p", { class: "field-note", text: periodText(numbers) }),
      el("p", { class: "activity-stats", text: statsText(numbers) }),
      el("p", { class: "activity-trend", text: trendText(numbers.trend) }),
      el("a", { class: "button secondary small", href: "#knowledge", text: "활동 기록에서 자세히 보기" }));
    body.replaceChildren(main, counts, summaryCard);
  }

  load();
}
