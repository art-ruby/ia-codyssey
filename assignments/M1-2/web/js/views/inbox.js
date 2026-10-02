// S02 받은 자료: URL·텍스트 접수 폼과 최신순 목록, 상세 수정.
// URL만 받은 자료는 본문을 읽었다고 표시하지 않는다(PRD C02). 모든 문자열은 textContent·value로만 넣는다.
import { analysisPanel, analysisState } from "../analysis.js";
import { request } from "../api.js";
import { loadAllLaterPages, sortLater } from "../later-list.js";
import { processBatches, splitBatches } from "../review-batches.js";
import { singleFlight } from "../single-flight.js";
import { trashButton } from "../trash.js";

// 서버 한도와 같다(server/app/features/materials/schemas.py). 최종 판단은 서버가 한다.
const LIMITS = { url: 2048, title: 200, description: 2000, body: 20000, save_reason: 2000, memo: 2000 };
const FIELDS = [
  ["title", "제목", "input"],
  ["description", "설명(내가 쓰는 요약·맥락)", "textarea", 3],
  ["body", "본문·핵심 내용(원문에서 가져온 내용)", "textarea", 6],
  ["save_reason", "저장 이유", "textarea", 2],
  ["memo", "메모", "textarea", 2],
];
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

function field(name, label, kind, rows) {
  const input = kind === "textarea"
    ? el("textarea", { rows: String(rows || 3), "data-field": name })
    : el("input", { type: name === "url" ? "url" : "text", "data-field": name });
  return el("label", {}, el("span", { text: label }), input);
}

// 입력창에 maxlength를 두지 않는다(붙여 넣은 내용이 조용히 잘리지 않게). 보내기 전에 서버와 같은 문구로 알린다.
const LABELS = { url: "URL", title: "제목", description: "설명", body: "본문", save_reason: "저장 이유", memo: "메모" };
function overLimit(data) {
  for (const [name, value] of Object.entries(data)) {
    if (LIMITS[name] && value.length > LIMITS[name]) {
      return `${LABELS[name]}은(는) ${LIMITS[name]}자까지 입력할 수 있습니다 (지금 ${value.length}자)`;
    }
  }
  return null;
}

const LIFECYCLE = { active: "", trash: "휴지통" };

function readFields(root) {
  const data = {};
  for (const input of root.querySelectorAll("[data-field]")) data[input.dataset.field] = input.value;
  return data;
}

// AI 분석 제외는 분석 상태를 덮어쓰지 않고 화면에서만 대신 보여준다(T03.04). 제외를 풀면 원래 상태가 다시 보인다.
function statusTag(material) {
  const { label, tone } = analysisState(material);
  return el("span", { class: `tag ${tone}`, text: label });
}

const DAY = new Intl.DateTimeFormat("ko-KR", { timeZone: "UTC", month: "long", day: "numeric" });

function todaySeoul() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(new Date());
}

// 나중에 보기 표시. 날짜가 지나도 서버는 상태를 바꾸지 않고, 화면이 정리 후보로만 표시한다(PRD §8).
function laterTag(material) {
  if (material.revisit_due) return el("span", { class: "tag amber", text: "다시 볼 날짜 지남 · 정리 후보" });
  if (material.revisit_on) {
    return el("span", { class: "tag", text: `${DAY.format(new Date(`${material.revisit_on}T00:00:00Z`))}에 다시 보기` });
  }
  return el("span", { class: "tag", text: "날짜 없이 나중에 보기" });
}

// root: 화면 영역, ctx: { mode, isCurrent(), onError(error, retry) }
export function renderInbox(root, ctx) {
  const api = (path, options = {}) => request(path, { mode: ctx.mode, ...options });
  async function guarded(promise) {
    const result = await promise;
    if (!ctx.isCurrent()) throw new Error("stale");
    return result;
  }
  function fail(error, statusNode, retry) {
    if (error.message === "stale") return;
    if (error.kind === "http" && [404, 409, 422].includes(error.status)) {
      statusNode.textContent = error.detail;
      return;
    }
    ctx.onError(error, retry);
  }

  // ── 접수 폼 ──
  const form = el("section", { class: "panel form" },
    el("h2", { text: "새 자료 보내기" }),
    el("p", { text: "URL만 넣어도 접수됩니다. 이 서비스는 링크 본문을 자동으로 읽지 않으므로, 내용을 분석하려면 설명이나 본문을 직접 붙여 넣으세요." }),
    field("url", "URL", "input"),
    ...FIELDS.map(([name, label, kind, rows]) => field(name, label, kind, rows)));
  const submit = el("button", { class: "button primary small", type: "button", text: "자료 접수" });
  const formStatus = el("p", { class: "form-status", role: "status" });
  form.append(el("div", { class: "form-actions" }, submit, formStatus));

  // ── 목록: 검토로 옮기지 않은 미검토 자료만(view=inbox). 옮긴 자료는 검토·승인 화면에 모인다(T03.03). ──
  const list = el("ul", { class: "material-list" });
  const more = el("button", { class: "button secondary small", type: "button", text: "더 보기", hidden: "" });
  const listStatus = el("p", { class: "form-status", role: "status" });
  const moveBtn = el("button", { class: "button secondary small", type: "button", text: "선택한 자료 검토로 이동" });
  const laterBtn = el("button", { class: "button secondary small", type: "button", text: "나중에 보기" });
  const laterDate = el("input", { type: "date", "aria-label": "다시 볼 날짜(선택)", min: todaySeoul() });
  const listSection = el("section", { class: "panel" }, el("h2", { text: "접수 목록" }),
    el("p", { text: "검토할 자료를 골라 검토·승인 화면으로 옮기거나, 나중에 보기로 남깁니다. 보관은 검토·승인 화면에서 승인합니다." }),
    el("div", { class: "review-toolbar" }, moveBtn, laterBtn,
      el("label", { class: "check" }, el("span", { text: "다시 볼 날짜(선택)" }), laterDate)),
    listStatus, list, more);

  // ── 나중에 보기(view=later, T03.04) ──
  const laterList = el("ul", { class: "material-list" });
  const laterStatus = el("p", { class: "form-status", role: "status" });
  const laterToReview = el("button", { class: "button secondary small", type: "button", text: "검토로 이동" });
  const laterBack = el("button", { class: "button secondary small", type: "button", text: "받은 자료로 되돌리기" });
  const laterSection = el("section", { class: "panel" }, el("h2", { text: "나중에 볼 자료" }),
    el("p", { text: "다시 볼 날짜가 지난 자료는 정리 후보로 위에 표시합니다. 날짜가 지나도 자동으로 승인하거나 지우지 않습니다." }),
    el("div", { class: "review-toolbar" }, laterToReview, laterBack), laterStatus, laterList);
  root.append(form, listSection, laterSection);

  let items = [];
  let nextCursor = null;
  const selected = new Set();
  let laterItems = [];
  const laterSelected = new Set();
  const runBatch = singleFlight();
  const batchButtons = [moveBtn, laterBtn, laterToReview, laterBack];

  function syncSelection() {
    const count = items.filter((m) => selected.has(m.id)).length;
    moveBtn.textContent = count ? `선택한 ${count}건 검토로 이동` : "선택한 자료 검토로 이동";
    laterBtn.textContent = count ? `선택한 ${count}건 나중에 보기` : "나중에 보기";
    moveBtn.disabled = laterBtn.disabled = count === 0;
    const laterCount = laterItems.filter((m) => laterSelected.has(m.id)).length;
    laterToReview.disabled = laterBack.disabled = laterCount === 0;
  }

  function renderList() {
    if (!items.length) {
      list.replaceChildren(el("li", { class: "empty-row", text: "검토를 기다리는 받은 자료가 없습니다." }));
    } else {
      list.replaceChildren(...items.map((m) => row(m, selected, movable)));
    }
    more.hidden = !nextCursor;
    syncSelection();
  }

  function renderLater() {
    const sorted = sortLater(laterItems);
    laterList.replaceChildren(...(sorted.length ? sorted.map((m) => {
      const li = row(m, laterSelected, (x) => x.review_status === "later" && x.lifecycle === "active");
      li.querySelector(".material-meta").prepend(laterTag(m));
      return li;
    }) : [el("li", { class: "empty-row", text: "나중에 볼 자료가 없습니다." })]));
    syncSelection();
  }

  // 검토 대상이 아닌 자료(메모 추가·기존 자료 열기로 불러온 승인·검토 중 자료)는 고를 수 없다.
  const movable = (m) => m.review_status === "unreviewed" && !m.review_requested && m.lifecycle === "active";

  function row(material, chosen, canSelect) {
    const box = el("input", { type: "checkbox", "aria-label": `${material.display_title || "자료"} 선택` });
    box.checked = chosen.has(material.id);
    box.disabled = !canSelect(material);
    box.addEventListener("change", () => {
      if (box.checked) chosen.add(material.id);
      else chosen.delete(material.id);
      syncSelection();
    });
    const li = itemRow(material);
    li.prepend(el("div", { class: "review-check" }, box));
    li.classList.add("selectable");
    return li;
  }

  // 묶음 요청 공통: 서버 상한(50건)대로 나눠 보내며 실패한 묶음은 같은 요청 키로 재시도한다.
  async function sendBatch(path, body, targets, statusNode, label) {
    if (!targets.length) return;
    const batches = splitBatches(targets.map((m) => ({ material_id: m.id, expected_version: m.version })))
      .map((items) => ({ ...body, items }));
    const counts = { done: 0, failed: 0 };

    async function process(startAt = 0, retryFirst = null) {
      await runBatch(batchButtons, async () => {
        const outcome = await processBatches(
          batches,
          (payload, index) => {
            statusNode.textContent = `${label} 처리 중… (${index + 1}/${batches.length}묶음)`;
            return guarded(api(path, { method: "POST", body: payload }));
          },
          async (res) => {
            const doneIds = new Set(res.results.filter((r) => ["updated", "unchanged"].includes(r.status))
              .map((r) => r.material_id));
            counts.done += doneIds.size;
            counts.failed += res.results.length - doneIds.size;
            items = items.filter((m) => !doneIds.has(m.id));
            laterItems = laterItems.filter((m) => !doneIds.has(m.id));
            for (const id of doneIds) {
              selected.delete(id);
              laterSelected.delete(id);
            }
            statusNode.textContent = `${counts.done}건 처리, ${counts.failed}건 확인 필요.`;
          },
          { startAt, retryFirst: retryFirst && (() => guarded(retryFirst())) },
        );
        if (outcome.error) {
          renderList();
          renderLater();
          statusNode.textContent = `${counts.done}건 처리했습니다. 남은 묶음은 전송되지 않았습니다.`;
          fail(outcome.error, statusNode, () => process(outcome.nextIndex, outcome.error.retry));
        } else {
          await Promise.all([load(), loadLater()]);
          statusNode.textContent = counts.failed
            ? `${counts.done}건 ${label}. ${counts.failed}건은 다른 곳에서 바뀌었거나 처리할 수 없어 목록에서 확인하세요.`
            : `${counts.done}건 ${label}.`;
        }
      });
      syncSelection();
    }
    await process();
  }

  const chosenIn = (source, chosen) => source.filter((m) => chosen.has(m.id));

  function moveSelected() {
    return sendBatch("/api/reviews/request", { requested: true }, chosenIn(items, selected), listStatus,
      "검토·승인 화면으로 옮겼습니다");
  }

  function laterSelectedItems() {
    const body = { later: true };
    if (laterDate.value) {
      if (laterDate.value < todaySeoul()) {
        listStatus.textContent = "다시 볼 날짜는 오늘 이후로 고르세요.";
        return null;
      }
      body.revisit_on = laterDate.value;
    }
    return sendBatch("/api/reviews/later", body, chosenIn(items, selected), listStatus, "나중에 보기로 남겼습니다");
  }

  function itemRow(material) {
    const temp = material.title_source !== "user";
    const head = el("button", { class: "material-head", type: "button", "aria-expanded": "false" },
      el("strong", { text: material.display_title || "(제목 없음)" }),
      temp ? el("span", { class: "temp-title", text: material.title_source === "url" ? "· 주소로 표시" : "· 내용 앞부분" }) : null);
    const meta = el("div", { class: "material-meta" },
      statusTag(material),
      el("span", { text: SEOUL.format(new Date(material.registered_at)) }),
      material.url ? el("span", { class: "url", text: material.url }) : null);
    const li = el("li", { "data-id": material.id }, head, meta);
    head.addEventListener("click", () => toggleDetail(li, head, material));
    return li;
  }

  function toggleDetail(li, head, material) {
    const open = li.querySelector(".material-detail");
    if (open) {
      open.remove();
      head.setAttribute("aria-expanded", "false");
      return;
    }
    head.setAttribute("aria-expanded", "true");
    const detail = el("div", { class: "material-detail form" },
      material.url ? el("p", { class: "field-note", text: "원래 URL은 출처로 보존되어 고칠 수 없습니다." }) : null,
      ...FIELDS.map(([name, label, kind, rows]) => field(name, label, kind, rows)));
    for (const input of detail.querySelectorAll("[data-field]")) input.value = material[input.dataset.field] || "";
    const exclude = el("input", { type: "checkbox" });
    exclude.checked = Boolean(material.ai_excluded);
    detail.append(el("label", { class: "check" }, exclude,
      el("span", { text: "AI 분석 제외 — 켜면 이 자료의 내용을 AI에 보내지 않고, 채팅 근거로도 쓰지 않습니다." })));
    const save = el("button", { class: "button primary small", type: "button", text: "수정 저장" });
    const status = el("p", { class: "form-status", role: "status" });
    detail.append(el("div", { class: "form-actions" }, save, status));
    // 휴지통 이동(T05.03). 옮기면 받은 자료·나중에 보기 목록에서 빠진다.
    detail.append(trashButton(material, { api, onError: ctx.onError, onDone: () => {
      items = items.filter((m) => m.id !== material.id);
      laterItems = laterItems.filter((m) => m.id !== material.id);
      selected.delete(material.id);
      renderList();
      renderLater();
      listStatus.textContent = "휴지통으로 옮겼습니다. 지식 보관함의 휴지통 탭에서 복원할 수 있습니다.";
    } }));
    // 분석은 자료 버전을 올리지 않으므로 열린 수정 폼과 충돌하지 않는다(T04.02).
    detail.append(analysisPanel(material, {
      api, isCurrent: ctx.isCurrent, onError: ctx.onError,
      onChange: (next) => {
        items = items.map((m) => (m.id === next.id ? next : m));
        laterItems = laterItems.map((m) => (m.id === next.id ? next : m));
        li.querySelector(".material-meta .tag").replaceWith(statusTag(next));
      },
    }));
    li.append(detail);

    save.addEventListener("click", async () => {
      const tooLong = overLimit(readFields(detail));
      if (tooLong) {
        status.textContent = tooLong;
        return;
      }
      save.disabled = true;
      status.textContent = "저장하는 중…";
      try {
        const updated = await guarded(api(`/api/materials/${encodeURIComponent(material.id)}`, {
          method: "PUT", body: { expected_version: material.version, ...readFields(detail),
            ...(exclude.checked !== Boolean(material.ai_excluded) ? { ai_excluded: exclude.checked } : {}) } }));
        items = items.map((m) => (m.id === updated.id ? updated : m));
        laterItems = laterItems.map((m) => (m.id === updated.id ? updated : m));
        renderList();
        renderLater();
        listStatus.textContent = "수정했습니다.";
      } catch (error) {
        // 버전 충돌(409)·형식 오류(422)는 메시지로, 연결 실패는 공통 배너로 알린다.
        fail(error, status, () => load());
      } finally {
        save.disabled = false;
      }
    });
  }

  async function load(cursor = null) {
    listStatus.textContent = "불러오는 중…";
    try {
      const page = await guarded(api(`/api/materials?view=inbox&limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`));
      items = cursor ? [...items, ...page.items.filter((m) => !items.some((x) => x.id === m.id))] : page.items;
      nextCursor = page.next_cursor;
      for (const id of [...selected]) if (!items.some((m) => m.id === id)) selected.delete(id);
      renderList();
      listStatus.textContent = "";
    } catch (error) {
      fail(error, listStatus, () => load(cursor));
    }
  }

  async function loadLater() {
    laterStatus.textContent = "불러오는 중…";
    try {
      laterItems = await guarded(loadAllLaterPages((cursor) => guarded(api(
        `/api/materials?view=later&limit=100${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`))));
      for (const id of [...laterSelected]) if (!laterItems.some((m) => m.id === id)) laterSelected.delete(id);
      renderLater();
      laterStatus.textContent = "";
    } catch (error) {
      fail(error, laterStatus, () => loadLater());
    }
  }

  function afterCreate(created) {
    items = [created, ...items.filter((m) => m.id !== created.id)];
    renderList();
    for (const input of form.querySelectorAll("[data-field]")) input.value = "";
    formStatus.textContent = created.analysis_status === "link_only"
      ? "접수했습니다. 링크만 저장되었고 본문은 확인하지 않았습니다."
      : "접수했습니다. 분석은 자료를 검토할 때 직접 시작합니다.";
  }

  // ── 같은 URL(T03.02): 기존 자료 열기 / 메모 추가 / 별도 저장 ──
  const dupPanel = el("div", { class: "dup-panel", hidden: "" });
  form.insertBefore(dupPanel, form.querySelector(".form-actions"));
  const runDuplicateChoice = singleFlight();

  async function openExisting(id) {
    if (!items.some((m) => m.id === id)) {
      try {
        items = [await guarded(api(`/api/materials/${encodeURIComponent(id)}`)), ...items];
        renderList();
      } catch (error) {
        fail(error, formStatus, () => openExisting(id));
        return;
      }
    }
    const li = list.querySelector(`li[data-id="${CSS.escape(id)}"]`);
    if (li && !li.querySelector(".material-detail")) li.querySelector(".material-head").click();
    li?.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  async function chooseDuplicate(body, extra, onDone) {
    return runDuplicateChoice([...dupPanel.querySelectorAll("button"), submit], async () => {
      formStatus.textContent = "처리하는 중…";
      try {
        onDone(await guarded(api("/api/materials", { method: "POST", body: { ...body, ...extra } })));
      } catch (error) {
        fail(error, formStatus, () => error.retry().then(onDone).catch((e) => fail(e, formStatus)));
      }
    });
  }

  function showDuplicate(body, existing) {
    dupPanel.hidden = false;
    const rows = existing.map((m) => {
      const label = LIFECYCLE[m.lifecycle] ?? m.lifecycle;
      const open = el("button", { class: "button secondary small", type: "button", text: "기존 자료 열기" });
      const memo = el("button", { class: "button secondary small", type: "button", text: "이 자료에 메모 추가" });
      if (m.lifecycle !== "active") memo.disabled = true;
      open.addEventListener("click", () => openExisting(m.id));
      memo.addEventListener("click", () => {
        // 409 안내 뒤에 메모를 적을 수 있으므로 누르는 순간의 입력값을 읽는다.
        const memoText = form.querySelector('[data-field="memo"]').value.trim();
        if (!memoText) {
          formStatus.textContent = "메모 칸에 덧붙일 내용을 적은 뒤 다시 누르세요. 기존 본문은 바뀌지 않습니다.";
          return;
        }
        chooseDuplicate({ url: body.url, memo: memoText },
          { duplicate_action: "add_memo", target_id: m.id, target_version: m.version }, (updated) => {
            items = items.map((x) => (x.id === updated.id ? updated : x));
            renderList();
            for (const input of form.querySelectorAll("[data-field]")) input.value = "";
            dupPanel.hidden = true;
            formStatus.textContent = "기존 자료에 메모를 더했습니다. 새 자료는 만들지 않았습니다.";
          });
      });
      return el("li", {},
        el("strong", { text: m.display_title || "(제목 없음)" }),
        el("span", { class: "dup-meta", text: ` · ${SEOUL.format(new Date(m.registered_at))} 접수${label ? ` · ${label}` : ""}` }),
        el("div", { class: "row-actions" }, open, memo));
    });
    const separate = el("button", { class: "button secondary small", type: "button", text: "새 자료로 따로 저장" });
    separate.addEventListener("click", () => chooseDuplicate(body, { duplicate_action: "save_separately" }, (created) => {
      dupPanel.hidden = true;
      afterCreate(created);
    }));
    dupPanel.replaceChildren(
      el("p", { class: "field-note", text: "같은 URL의 자료가 이미 있습니다. 어떻게 할지 고르세요." }),
      el("ul", { class: "dup-list" }, ...rows), separate);
    formStatus.textContent = "";
  }

  async function send() {
    const data = readFields(form);
    const body = Object.fromEntries(Object.entries(data).filter(([, v]) => v.trim()));
    const tooLong = overLimit(data);
    if (tooLong) {
      formStatus.textContent = tooLong;
      return;
    }
    dupPanel.hidden = true;
    submit.disabled = true;
    formStatus.textContent = "접수하는 중…";
    try {
      afterCreate(await guarded(api("/api/materials", { method: "POST", body })));
    } catch (error) {
      if (error.kind === "http" && error.status === 409 && error.data?.reason === "duplicate_url") {
        showDuplicate(body, error.data.existing);
        return;
      }
      // 연결이 끊겨 결과를 모를 때는 같은 Idempotency-Key로 다시 보내 중복 접수를 막는다.
      fail(error, formStatus, () => error.retry().then(afterCreate).catch((e) => fail(e, formStatus)));
    } finally {
      submit.disabled = false;
    }
  }

  submit.addEventListener("click", send);
  moveBtn.addEventListener("click", moveSelected);
  laterBtn.addEventListener("click", laterSelectedItems);
  laterToReview.addEventListener("click", () => sendBatch("/api/reviews/request", { requested: true },
    chosenIn(laterItems, laterSelected), laterStatus, "검토·승인 화면으로 옮겼습니다"));
  laterBack.addEventListener("click", () => sendBatch("/api/reviews/later", { later: false },
    chosenIn(laterItems, laterSelected), laterStatus, "받은 자료로 되돌렸습니다"));
  more.addEventListener("click", () => load(nextCursor));
  load();
  loadLater();
}
