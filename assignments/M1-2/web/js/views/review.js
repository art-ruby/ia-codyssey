// S07 검토·승인: 승인 요청 목록에서 묶음 선택·일부 제외, 제목·중요도·프로젝트를 고쳐 보관 승인한다(T03.03).
// 항목별 결과를 그대로 보여준다. 충돌한 자료는 성공으로 표시하지 않고, 고친 값은 남긴 채 최신 버전을 다시 불러온다.
// 모든 문자열은 textContent·value로만 넣는다.
import { request } from "../api.js";
import { processBatches, splitBatches } from "../review-batches.js";
import { singleFlight } from "../single-flight.js";

const TITLE_LIMIT = 200; // server/app/features/materials/schemas.py와 같다
const IMPORTANCE = [["", "판단 보류"], ["high", "높음"], ["medium", "보통"], ["low", "낮음"]];
const STATUS = {
  link_only: ["링크만 저장됨 · 본문 미확인", "amber"],
  awaiting_start: ["분석 시작 대기", "mint"],
};
const REASON = {
  trashed: "휴지통에 있는 자료라 승인하지 않았습니다.",
  project: "연결할 프로젝트가 없거나 비활성입니다. 프로젝트를 다시 고르세요.",
  no_content: "제목을 비우면 남는 내용이 없습니다. 제목을 입력하세요.",
  approved: "이미 승인된 자료입니다.",
};
const SEOUL = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "short" });

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (name === "text") node.textContent = value;
    else if (name === "value") node.value = value;
    else node.setAttribute(name, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

const excerpt = (text, size = 160) => (text.length > size ? `${text.slice(0, size)}…` : text);

// root: 화면 영역, ctx: { mode, isCurrent(), onError(error, retry) }
export function renderReview(root, ctx) {
  const api = (path, options = {}) => request(path, { mode: ctx.mode, ...options });
  async function guarded(promise) {
    const result = await promise;
    if (!ctx.isCurrent()) throw new Error("stale");
    return result;
  }
  function fail(error, retry) {
    if (error.message === "stale") return;
    if (error.kind === "http" && [404, 409, 422].includes(error.status)) {
      status.textContent = error.detail;
      return;
    }
    ctx.onError(error, retry);
  }

  let items = [];
  let nextCursor = null;
  let projects = [];
  const selected = new Set();
  const drafts = new Map(); // id → { title, user_importance, primary_project_id } 사용자가 고친 값
  const notes = new Map(); // id → 항목별 결과 안내

  const selectAll = el("input", { type: "checkbox", "aria-label": "전체 선택" });
  const approveBtn = el("button", { class: "button primary small", type: "button", text: "선택한 자료 보관 승인" });
  const backBtn = el("button", { class: "button secondary small", type: "button", text: "받은 자료로 되돌리기" });
  const status = el("p", { class: "form-status", role: "status" });
  const list = el("ul", { class: "review-list" });
  const more = el("button", { class: "button secondary small", type: "button", text: "더 보기", hidden: "" });
  root.append(el("section", { class: "panel" },
    el("h2", { text: "승인 요청 목록" }),
    el("p", { text: "보관할 자료를 고르고 필요하면 제목·중요도·프로젝트를 고친 뒤 승인합니다. 고르지 않은 자료는 그대로 남습니다. AI 요약·중요 이유는 분석 기능이 연결되면 함께 표시됩니다." }),
    el("div", { class: "review-toolbar" },
      el("label", { class: "check" }, selectAll, el("span", { text: "전체 선택" })), approveBtn, backBtn),
    status, list, more));

  function syncSelection() {
    const available = items.filter((m) => m.review_status !== "approved");
    const count = available.filter((m) => selected.has(m.id)).length;
    approveBtn.textContent = count ? `선택한 ${count}건 보관 승인` : "선택한 자료 보관 승인";
    approveBtn.disabled = backBtn.disabled = count === 0;
    selectAll.checked = available.length > 0 && count === available.length;
    selectAll.indeterminate = count > 0 && count < available.length;
  }

  function value(material, name) {
    const draft = drafts.get(material.id);
    return draft && name in draft ? draft[name] : (material[name] ?? "");
  }

  function setDraft(material, name, newValue) {
    const draft = { ...drafts.get(material.id) };
    if (newValue === (material[name] ?? "")) delete draft[name];
    else draft[name] = newValue;
    if (Object.keys(draft).length) drafts.set(material.id, draft);
    else drafts.delete(material.id);
  }

  function projectSelect(material) {
    const current = value(material, "primary_project_id");
    const options = [el("option", { value: "", text: "없음" })];
    for (const p of projects) {
      if (!p.active && p.id !== current) continue;
      const option = el("option", { value: p.id, text: p.active ? p.name : `${p.name} (비활성)` });
      if (!p.active) option.disabled = true;
      options.push(option);
    }
    const select = el("select", { "aria-label": "주 프로젝트" }, ...options);
    select.value = current;
    return select;
  }

  function row(material) {
    const box = el("input", { type: "checkbox", "aria-label": `${material.display_title || "자료"} 선택` });
    box.checked = selected.has(material.id);
    box.disabled = material.review_status === "approved";
    box.addEventListener("change", () => {
      if (box.checked) selected.add(material.id);
      else selected.delete(material.id);
      syncSelection();
    });

    const title = el("input", { type: "text", value: value(material, "title"), placeholder: material.display_title || "",
      "aria-label": "제목" });
    title.addEventListener("input", () => setDraft(material, "title", title.value));
    const importance = el("select", { "aria-label": "중요도" },
      ...IMPORTANCE.map(([v, label]) => el("option", { value: v, text: label })));
    importance.value = value(material, "user_importance");
    importance.addEventListener("change", () => setDraft(material, "user_importance", importance.value));
    const project = projectSelect(material);
    project.addEventListener("change", () => setDraft(material, "primary_project_id", project.value));
    const saveApproved = material.review_status === "approved"
      ? el("button", { class: "button secondary small", type: "button", text: "수정값 저장" }) : null;
    if (saveApproved) saveApproved.addEventListener("click", () => saveApprovedChanges(material, saveApproved));

    // AI 분석 제외는 분석 상태를 덮어쓰지 않고 화면에서만 대신 보여준다(T03.04).
    const [statusText, tone] = material.review_status === "approved" ? ["이미 보관 승인됨", "mint"]
      : material.ai_excluded ? ["AI 분석 제외", ""]
        : (STATUS[material.analysis_status] || [material.analysis_status, ""]);
    const context = material.description || material.body || "";
    const note = notes.get(material.id);
    return el("li", { class: "review-card", "data-id": material.id },
      el("div", { class: "review-check" }, box),
      el("div", { class: "review-body form" },
        el("div", { class: "material-meta" },
          el("span", { class: `tag ${tone}`, text: statusText }),
          el("span", { text: `${SEOUL.format(new Date(material.registered_at))} 접수` }),
          material.url ? el("span", { class: "url", text: material.url }) : null),
        context ? el("p", { class: "review-text", text: excerpt(context) }) : null,
        material.save_reason ? el("p", { class: "review-text", text: `저장 이유: ${excerpt(material.save_reason)}` }) : null,
        el("div", { class: "review-fields" },
          el("label", {}, el("span", { text: "제목" }), title),
          el("label", {}, el("span", { text: "중요도" }), importance),
          el("label", {}, el("span", { text: "주 프로젝트" }), project)),
        saveApproved,
        note ? el("p", { class: "row-note", role: "status", text: note }) : null));
  }

  function renderList() {
    list.replaceChildren(...(items.length ? items.map(row)
      : [el("li", { class: "empty-row", text: "승인을 기다리는 자료가 없습니다. 받은 자료에서 '검토로 이동'을 누르면 여기에 모입니다." })]));
    more.hidden = !nextCursor;
    syncSelection();
  }

  async function load(cursor = null) {
    status.textContent = "불러오는 중…";
    try {
      const [page, projectData] = await guarded(Promise.all([
        api(`/api/materials?view=review&limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`),
        cursor ? Promise.resolve({ items: projects }) : api("/api/projects?include_inactive=true"),
      ]));
      projects = projectData.items;
      items = cursor ? [...items, ...page.items.filter((m) => !items.some((x) => x.id === m.id))] : page.items;
      nextCursor = page.next_cursor;
      if (!cursor) {
        for (const id of [...selected]) if (!items.some((m) => m.id === id)) selected.delete(id);
      }
      renderList();
      status.textContent = "";
    } catch (error) {
      fail(error, () => load(cursor));
    }
  }

  // 충돌한 자료는 최신 버전으로 바꾸되, 사용자가 고친 값(drafts)과 선택은 남긴다.
  async function refresh(ids) {
    for (const id of ids) {
      try {
        const fresh = await guarded(api(`/api/materials/${encodeURIComponent(id)}`));
        const stillPending = fresh.review_status === "unreviewed" && fresh.review_requested && fresh.lifecycle === "active";
        const approvedWithDraft = fresh.review_status === "approved" && fresh.lifecycle === "active" && drafts.has(id);
        if (approvedWithDraft) {
          selected.delete(id);
          notes.set(id, "다른 곳에서 먼저 승인했습니다. 입력한 수정값은 남아 있습니다. 최신 내용을 확인한 뒤 수정값을 저장하세요.");
        }
        items = (stillPending || approvedWithDraft)
          ? items.map((m) => (m.id === id ? fresh : m)) : items.filter((m) => m.id !== id);
      } catch (error) {
        if (error.message === "stale") return;
        if (error.status === 404) items = items.filter((m) => m.id !== id);
      }
    }
  }

  function changesFor(material) {
    const draft = drafts.get(material.id) || {};
    const changes = {};
    if ("title" in draft) changes.title = draft.title.trim() || null;
    if ("user_importance" in draft) changes.user_importance = draft.user_importance || null;
    if ("primary_project_id" in draft) changes.primary_project_id = draft.primary_project_id || null;
    return changes;
  }

  async function saveApprovedChanges(material, button) {
    const changes = changesFor(material);
    if (!Object.keys(changes).length) {
      status.textContent = "저장할 수정값이 없습니다.";
      return;
    }
    if (typeof changes.title === "string" && changes.title.length > TITLE_LIMIT) {
      status.textContent = `제목은 ${TITLE_LIMIT}자까지 입력할 수 있습니다.`;
      return;
    }
    await runAction([approveBtn, backBtn, button], async () => {
      status.textContent = "수정값을 저장하는 중…";
      const apply = () => {
        items = items.filter((m) => m.id !== material.id);
        drafts.delete(material.id);
        notes.delete(material.id);
        renderList();
        status.textContent = "승인된 자료의 수정값을 저장했습니다.";
      };
      try {
        await guarded(api(`/api/materials/${encodeURIComponent(material.id)}`, {
          method: "PUT", body: { expected_version: material.version, ...changes },
        }));
        apply();
      } catch (error) {
        if (error.status === 409) {
          await refresh([material.id]);
          renderList();
          status.textContent = "자료가 다시 변경됐습니다. 입력값을 유지했으니 최신 내용을 확인하세요.";
        } else {
          fail(error, () => error.retry().then(apply).catch((e) => fail(e)));
        }
      }
    });
    syncSelection();
  }

  // 결과 반영: done 상태는 목록에서 빼고, 나머지는 항목별 안내를 남긴다.
  async function applyResults(results, done) {
    const conflicts = [];
    let doneCount = 0;
    for (const r of results) {
      if (done.includes(r.status)) {
        doneCount += 1;
        items = items.filter((m) => m.id !== r.material_id);
        selected.delete(r.material_id);
        drafts.delete(r.material_id);
        notes.delete(r.material_id);
      } else if (r.status === "conflict") {
        conflicts.push(r.material_id);
        notes.set(r.material_id, "다른 곳에서 먼저 바뀌어 승인하지 않았습니다. 최신 내용을 불러왔으니 확인 후 다시 승인하세요.");
      } else if (r.status === "not_found") {
        items = items.filter((m) => m.id !== r.material_id);
        selected.delete(r.material_id);
      } else {
        notes.set(r.material_id, REASON[r.reason] || "처리하지 못했습니다.");
      }
    }
    if (conflicts.length) await refresh(conflicts);
    renderList();
    return { doneCount, failedCount: results.length - doneCount };
  }

  const runAction = singleFlight();

  function chosen() {
    return items.filter((m) => m.review_status !== "approved" && selected.has(m.id));
  }

  async function submitBatches(batches, path, doneStatuses, label) {
    const counts = { done: 0, failed: 0 };
    async function process(startAt = 0, retryFirst = null) {
      await runAction([approveBtn, backBtn], async () => {
        const outcome = await processBatches(
          batches,
          (batch, index) => {
            status.textContent = `${label} 처리 중… (${index + 1}/${batches.length}묶음)`;
            return guarded(api(path, { method: "POST", body: batch }));
          },
          async (res) => {
            const summary = await applyResults(res.results, doneStatuses);
            counts.done += summary.doneCount;
            counts.failed += summary.failedCount;
            status.textContent = `${counts.done}건 ${label}, ${counts.failed}건 확인 필요.`;
          },
          { startAt, retryFirst: retryFirst && (() => guarded(retryFirst())) },
        );
        if (outcome.error) {
          status.textContent = `${counts.done}건 ${label}했습니다. 남은 묶음은 전송되지 않았습니다.`;
          // 실패한 묶음은 같은 요청 키로 다시 보내고, 성공하면 뒤 묶음을 이어 처리한다.
          fail(outcome.error, () => process(outcome.nextIndex, outcome.error.retry));
        } else {
          status.textContent = counts.failed
            ? `${counts.done}건 ${label}했습니다. ${counts.failed}건은 항목 안내를 확인하세요.`
            : `${counts.done}건 ${label}했습니다.`;
        }
      });
      syncSelection();
    }
    await process();
  }

  async function approveSelected() {
    const targets = chosen();
    const tooLong = targets.find((m) => (drafts.get(m.id)?.title || "").trim().length > TITLE_LIMIT);
    if (tooLong) {
      status.textContent = `제목은 ${TITLE_LIMIT}자까지 입력할 수 있습니다.`;
      return;
    }
    const batches = splitBatches(targets.map((m) => {
        const item = { material_id: m.id, expected_version: m.version, action: "keep" };
        const changes = changesFor(m);
        if (Object.keys(changes).length) item.changes = changes;
        return item;
    }));
    await submitBatches(batches.map((items) => ({ items })), "/api/reviews/approve",
      ["approved", "already_approved"], "보관 승인");
  }

  async function sendBack() {
    const targets = chosen();
    const batches = splitBatches(targets.map((m) => ({ material_id: m.id, expected_version: m.version })));
    await submitBatches(batches.map((items) => ({ requested: false, items })), "/api/reviews/request",
      ["updated", "unchanged"], "받은 자료로 이동");
  }

  selectAll.addEventListener("change", () => {
    for (const m of items) {
      if (m.review_status === "approved") continue;
      if (selectAll.checked) selected.add(m.id);
      else selected.delete(m.id);
    }
    renderList();
  });
  approveBtn.addEventListener("click", approveSelected);
  backBtn.addEventListener("click", sendBack);
  more.addEventListener("click", () => load(nextCursor));
  load();
}
