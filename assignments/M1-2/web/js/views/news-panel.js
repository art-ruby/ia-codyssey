// AI 동향의 '새 소식' 칸(docs/superpowers/specs/2026-10-04-ai-news-feed-design.md §8).
// 외부 글은 모두 textContent로 넣고, 링크는 http·https만 새 탭(noopener)으로 연다.
import { request } from "../api.js";
import { failureText, kindLabel, relativeTime, safeLink } from "../news.js";
import { el } from "../priority.js";

const POLL_MS = 5000;
const POLL_LIMIT = 6;

// ctx: { mode, isCurrent(), onError(error, retry) }
export function newsPanel(ctx) {
  const panel = el("section", { class: "panel news-panel" });
  if (ctx.mode !== "personal") {
    panel.append(el("h2", { class: "section-title", text: "새 소식" }),
      el("p", { class: "empty-row", text: "새 소식은 개인 모드에서 볼 수 있습니다." }));
    return panel;
  }

  const api = (path, options = {}) => request(path, { mode: ctx.mode, ...options });
  const title = el("h2", { class: "section-title", text: "새 소식" });
  const refreshBtn = el("button", { class: "button secondary small", type: "button", text: "지금 새로고침" });
  const meta = el("p", { class: "news-meta" });
  const failures = el("p", { class: "field-note" });
  const status = el("p", { class: "form-status", role: "status" });
  const list = el("ul", { class: "priority-list" });
  const more = el("button", { class: "button secondary small", type: "button", text: "더 보기" });
  more.hidden = true;
  panel.append(el("div", { class: "news-head" }, title, refreshBtn),
    el("p", { class: "field-note", text: "고른 공식 블로그·커뮤니티의 새 글입니다. 관심 분야와 맞는 글이 먼저 나옵니다. 저장한 글만 내 자료가 됩니다." }),
    meta, failures, status, list, more);

  let items = [];
  let total = 0;
  let nextCursor = null;
  let polls = 0;
  let timer = null;
  const alive = () => ctx.isCurrent() && panel.isConnected;

  function fail(error, node, retry) {
    if (error.kind === "http" && ([404, 409, 422].includes(error.status) || error.data?.reason)) {
      node.textContent = error.detail;
      return;
    }
    ctx.onError(error, retry);
  }

  function setTotal(count) {
    total = count;
    title.textContent = `새 소식 ${total}건`;
  }

  function showState(view) {
    const state = view.state;
    setTotal(view.total);
    meta.textContent = state.last_success_at
      ? `마지막 확인 ${relativeTime(state.last_success_at, new Date())}` : "아직 확인한 적이 없습니다.";
    failures.textContent = failureText(state.failures);
    status.textContent = state.refreshing ? "새 소식을 확인하는 중…" : "";
  }

  function button(text, kind) {
    return el("button", { class: `button ${kind} small`, type: "button", text });
  }

  function savedActions(actions) {
    actions.replaceChildren(el("span", { class: "tag mint", text: "저장됨" }),
      el("a", { class: "button secondary small", href: "#inbox", text: "받은 자료에서 보기" }));
  }

  function card(item) {
    const href = safeLink(item.link);
    const heading = href
      ? el("a", { href, target: "_blank", rel: "noopener noreferrer", text: item.title })
      : el("span", { text: item.title });
    const tags = el("div", { class: "news-tags" },
      el("span", { class: "tag", text: `${item.source_name} · ${kindLabel(item.kind)}` }),
      el("span", { class: "news-time", text: relativeTime(item.published_at || item.fetched_at, new Date()) }),
      ...item.matched_keywords.map((word) => el("span", { class: "tag mint", text: word })));
    const actions = el("div", { class: "form-actions" });
    const note = el("p", { class: "form-status", role: "status" });
    const li = el("li", { class: "priority-card news-card" }, el("strong", {}, heading), tags,
      item.summary ? el("p", { class: "news-summary", text: item.summary }) : null, actions, note);

    if (item.saved_material_id) {
      savedActions(actions);
      return li;
    }
    const save = button("자료로 저장", "primary");
    const hide = button("숨기기", "secondary");
    actions.append(save, hide);

    save.addEventListener("click", async () => {
      save.disabled = hide.disabled = true;
      note.textContent = "저장하는 중…";
      try {
        const res = await api(`/api/news/${encodeURIComponent(item.id)}/save`, { method: "POST" });
        if (!alive()) return;
        item.saved_material_id = res.material_id;
        savedActions(actions);
        note.textContent = res.created
          ? "받은 자료에 저장했습니다. 분석·검토는 받은 자료에서 이어집니다."
          : "같은 주소의 자료가 이미 있어 그 자료와 연결했습니다.";
      } catch (error) {
        save.disabled = hide.disabled = false;
        note.textContent = "";
        fail(error, note, () => save.click());
      }
    });

    hide.addEventListener("click", async () => {
      save.disabled = hide.disabled = true;
      try {
        await api(`/api/news/${encodeURIComponent(item.id)}/hide`, { method: "POST" });
        if (!alive()) return;
        setTotal(total - 1);
        const undo = button("되돌리기", "secondary");
        const row = el("li", { class: "priority-card news-card news-hidden" },
          el("span", { text: `숨겼습니다: ${item.title}` }), undo);
        li.replaceWith(row);
        undo.addEventListener("click", async () => {
          undo.disabled = true;
          try {
            await api(`/api/news/${encodeURIComponent(item.id)}/unhide`, { method: "POST" });
            if (!alive()) return;
            setTotal(total + 1);
            row.replaceWith(card(item));
          } catch (error) {
            undo.disabled = false;
            fail(error, status, () => undo.click());
          }
        });
      } catch (error) {
        save.disabled = hide.disabled = false;
        fail(error, note, () => hide.click());
      }
    });
    return li;
  }

  function renderList(refreshing) {
    if (!items.length) {
      list.replaceChildren(el("li", { class: "empty-row",
        text: refreshing ? "새 소식을 모으는 중입니다." : "표시할 새 소식이 없습니다. 프로젝트·설정에서 소식 출처를 확인하세요." }));
    } else {
      list.replaceChildren(...items.map(card));
    }
    more.hidden = !nextCursor;
  }

  function schedulePoll(refreshing) {
    clearTimeout(timer);
    if (!refreshing) {
      polls = 0;
      return;
    }
    if (polls >= POLL_LIMIT) {
      status.textContent = "확인이 오래 걸립니다. 잠시 뒤 다시 열어 보세요.";
      return;
    }
    polls += 1;
    timer = setTimeout(() => {
      if (alive()) load();
    }, POLL_MS);
  }

  function apply(view, append) {
    items = append ? [...items, ...view.items] : view.items;
    nextCursor = view.next_cursor;
    showState(view);
    renderList(view.state.refreshing);
    schedulePoll(view.state.refreshing);
  }

  async function load(cursor = null) {
    try {
      const view = await api(`/api/news${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`);
      if (!alive()) return;
      apply(view, Boolean(cursor));
    } catch (error) {
      if (!alive()) return;
      status.textContent = "";
      fail(error, status, () => load(cursor));
    }
  }

  refreshBtn.addEventListener("click", async () => {
    refreshBtn.disabled = true;
    status.textContent = "새 소식을 확인하는 중…";
    try {
      const view = await api("/api/news/refresh", { method: "POST" });
      if (!alive()) return;
      polls = 0;
      apply(view, false);
      if (!view.state.refreshing) status.textContent = "최근에 확인해서 지금은 다시 확인하지 않았습니다(5분 간격).";
    } catch (error) {
      if (!alive()) return;
      status.textContent = "";
      fail(error, status, () => refreshBtn.click());
    } finally {
      refreshBtn.disabled = false;
    }
  });
  more.addEventListener("click", () => load(nextCursor));

  status.textContent = "불러오는 중…";
  load();
  return panel;
}
