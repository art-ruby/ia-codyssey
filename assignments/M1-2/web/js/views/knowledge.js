// S03 지식 보관함: 보관 완료 자료 검색·기간·종류·프로젝트 필터, 상세 보기·메모 수정(T05.01).
// 관련 자료 연결은 related.js(T05.02), 휴지통 탭·휴지통 이동은 trash.js(T05.03). 모든 문자열은 textContent·value로만 넣는다.
import { analysisPanel } from "../analysis.js";
import { request } from "../api.js";
import { relatedPanel } from "../related.js";
import { el } from "../priority.js";
import { FIELD_LABELS, KIND_OPTIONS, SOURCE_OPTIONS, mergePage, scopeText, searchQuery } from "../search-query.js";
import { singleFlight } from "../single-flight.js";
import { renderTrashTab, trashButton } from "../trash.js";

const MEMO_LIMIT = 2000; // server/app/features/materials/schemas.py와 같다
const SEOUL = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "short" });

function select(label, options) {
  return el("select", { "aria-label": label }, ...options.map(([value, text]) => el("option", { value, text })));
}

// root: 화면 영역, ctx: { mode, isCurrent(), onError(error, retry) }
export function renderKnowledge(root, ctx) {
  const api = (path, options = {}) => request(path, { mode: ctx.mode, ...options });
  const q = el("input", { type: "search", placeholder: "제목·설명·본문·저장 이유·메모·URL에서 찾기", "aria-label": "검색어" });
  const from = el("input", { type: "date", "aria-label": "시작 날짜" });
  const to = el("input", { type: "date", "aria-label": "끝 날짜" });
  const kind = select("종류", KIND_OPTIONS);
  const source = select("링크·텍스트", SOURCE_OPTIONS);
  const project = select("프로젝트", [["", "전체 프로젝트"]]);
  const go = el("button", { class: "button primary small", type: "submit", text: "검색" });
  const form = el("form", { class: "panel form search-form", role: "search" },
    el("label", {}, el("span", { text: "검색어" }), q),
    el("div", { class: "search-filters" },
      el("label", {}, el("span", { text: "기간(서울 날짜)" }), el("div", { class: "date-range" }, from, el("span", { text: "~" }), to)),
      el("label", {}, el("span", { text: "종류" }), kind),
      el("label", {}, el("span", { text: "링크·텍스트" }), source),
      el("label", {}, el("span", { text: "프로젝트" }), project)),
    el("div", { class: "form-actions" }, go));
  const scope = el("p", { class: "form-status", role: "status" });
  const list = el("ul", { class: "material-list" });
  const more = el("button", { class: "button secondary small", type: "button", text: "더 보기", hidden: "" });
  // 보관 자료 | 휴지통 탭. 휴지통은 처음 열 때 불러오고, 복원하면 보관 자료 검색을 다시 한다.
  const keptTab = el("button", { class: "tab", type: "button", role: "tab", "aria-selected": "true", text: "보관 자료" });
  const trashTab = el("button", { class: "tab", type: "button", role: "tab", "aria-selected": "false", text: "휴지통" });
  const keptPane = el("div", {}, form, el("section", { class: "panel" }, scope, list, more));
  const trashPane = el("section", { class: "panel", hidden: "" });
  root.replaceChildren(el("div", { class: "tabs", role: "tablist" }, keptTab, trashTab), keptPane, trashPane);
  let trashView = null;
  let keptStale = false;
  function show(kept) {
    keptTab.setAttribute("aria-selected", String(kept));
    trashTab.setAttribute("aria-selected", String(!kept));
    if (kept) { keptPane.removeAttribute("hidden"); trashPane.setAttribute("hidden", ""); }
    else { trashPane.removeAttribute("hidden"); keptPane.setAttribute("hidden", ""); }
  }
  keptTab.addEventListener("click", () => {
    show(true);
    if (keptStale) {
      keptStale = false;
      search(null, { fresh: false });
    }
  });
  trashTab.addEventListener("click", () => {
    show(false);
    if (trashView) trashView.reload();
    else trashView = renderTrashTab(trashPane, { api, isCurrent: ctx.isCurrent, onError: ctx.onError, onChanged: () => { keptStale = true; } });
  });

  let conditions = {};
  let items = [];
  // 검색·더 보기 요청이 끝나기 전에는 다시 보내지 않는다(같은 커서로 두 번 요청해 목록이 겹치는 것을 막음).
  const flight = singleFlight();
  let nextCursor = null;
  let projects = [];

  const projectName = (id) => (projects.find((p) => p.id === id) || {}).name || "(알 수 없는 프로젝트)";

  function readConditions() {
    return { q: q.value, date_from: from.value, date_to: to.value, kind: kind.value, source_type: source.value,
      project_id: project.value };
  }

  // cursor가 있으면 같은 조건의 다음 페이지. fresh면 폼에서 새 조건을 읽고, 아니면 마지막 조건으로 다시 검색한다.
  function search(cursor = null, { fresh = true, note = "" } = {}) {
    return flight([go, more], () => runSearch(cursor, fresh, note));
  }

  async function runSearch(cursor, fresh, note) {
    if (!cursor && fresh) conditions = readConditions();
    scope.textContent = "검색하는 중…";
    try {
      const page = await api(searchQuery(conditions, cursor));
      if (!ctx.isCurrent()) return;
      items = cursor ? mergePage(items, page.items) : page.items;
      nextCursor = page.next_cursor;
      render();
      scope.textContent = [note, scopeText(page)].filter(Boolean).join(" ");
    } catch (error) {
      if (!ctx.isCurrent()) return;
      // 검색 실패를 '결과 없음'으로 보이지 않게 목록을 비우지 않고 오류를 알린다.
      if (error.kind === "http" && [404, 409, 422].includes(error.status)) scope.textContent = error.detail;
      else {
        scope.textContent = "검색하지 못했습니다.";
        ctx.onError(error, () => search(cursor, { fresh }));
      }
    }
  }

  function render() {
    list.replaceChildren(...(items.length ? items.map(row)
      : [el("li", { class: "empty-row", text: "조건에 맞는 보관 자료가 없습니다. 보관은 검토·승인 화면에서 합니다." })]));
    if (nextCursor) more.removeAttribute("hidden");
    else more.setAttribute("hidden", "");
  }

  function row(material) {
    const head = el("button", { class: "material-head", type: "button", "aria-expanded": "false" },
      el("strong", { text: material.display_title || "(제목 없음)" }));
    const projectsText = [material.primary_project_id, ...(material.related_project_ids || [])].filter(Boolean)
      .map(projectName).join(", ");
    const meta = el("div", { class: "material-meta" },
      el("span", { text: `${SEOUL.format(new Date(material.registered_at))} 접수` }),
      projectsText ? el("span", { text: `프로젝트: ${projectsText}` }) : null,
      material.url ? el("span", { class: "url", text: material.url }) : null);
    const match = material.match && material.match.snippet
      ? el("p", { class: "search-snippet", text: `${FIELD_LABELS[material.match.field] || ""}: ${material.match.snippet}` }) : null;
    const li = el("li", { "data-id": material.id }, head, meta, match);
    head.addEventListener("click", () => toggle(li, head, material));
    return li;
  }

  function toggle(li, head, material) {
    const open = li.querySelector(".material-detail");
    if (open) {
      open.remove();
      head.setAttribute("aria-expanded", "false");
      return;
    }
    head.setAttribute("aria-expanded", "true");
    const field = (label, text) => (text ? el("div", { class: "detail-field" },
      el("span", { class: "detail-label", text: label }), el("p", { class: "detail-text", text })) : null);
    const memo = el("textarea", { rows: "3", "aria-label": "메모" });
    memo.value = material.memo || "";
    const save = el("button", { class: "button primary small", type: "button", text: "메모 저장" });
    const status = el("p", { class: "form-status", role: "status" });
    const detail = el("div", { class: "material-detail form" },
      field("URL(원래 주소, 고칠 수 없음)", material.url),
      field("설명", material.description),
      field("본문", material.body),
      field("저장 이유", material.save_reason),
      el("label", {}, el("span", { text: "메모" }), memo),
      el("div", { class: "form-actions" }, save, status),
      trashButton(material, { api, onError: ctx.onError,
        onDone: () => search(null, { fresh: false, note: "휴지통으로 옮겼습니다." }) }),
      analysisPanel(material, {
        api, isCurrent: ctx.isCurrent, onError: ctx.onError,
        onChange: (next) => { items = items.map((m) => (m.id === next.id ? { ...next, match: m.match } : m)); },
      }),
      relatedPanel(material, { api, isCurrent: ctx.isCurrent, onError: ctx.onError }));
    li.append(detail);

    save.addEventListener("click", async () => {
      if (memo.value.length > MEMO_LIMIT) {
        status.textContent = `메모는 ${MEMO_LIMIT}자까지 입력할 수 있습니다 (지금 ${memo.value.length}자)`;
        return;
      }
      save.disabled = true;
      status.textContent = "저장하는 중…";
      try {
        const updated = await api(`/api/materials/${encodeURIComponent(material.id)}`,
          { method: "PUT", body: { expected_version: material.version, memo: memo.value } });
        if (!ctx.isCurrent()) return;
        Object.assign(material, updated);
        // 메모가 검색어와 일치해 나온 자료일 수 있으므로 마지막 검색 조건으로 결과를 다시 계산한다.
        status.textContent = "메모를 저장했습니다.";
        search(null, { fresh: false, note: "메모를 저장했고 같은 조건으로 다시 검색했습니다." });
      } catch (error) {
        if (error.kind === "http" && [404, 409, 422].includes(error.status)) status.textContent = error.detail;
        else ctx.onError(error, () => save.click());
      } finally {
        save.disabled = false;
      }
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    search();
  });
  more.addEventListener("click", () => search(nextCursor));

  (async () => {
    try {
      projects = (await api("/api/projects?include_inactive=true")).items;
      if (!ctx.isCurrent()) return;
      project.append(...projects.map((p) => el("option", { value: p.id, text: p.active === false ? `${p.name}(비활성)` : p.name })));
    } catch (error) {
      if (ctx.isCurrent()) ctx.onError(error, () => {});
    }
    search();
  })();
}
