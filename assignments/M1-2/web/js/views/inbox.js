// S02 받은 자료: URL·텍스트 접수 폼과 최신순 목록, 상세 수정.
// URL만 받은 자료는 본문을 읽었다고 표시하지 않는다(PRD C02). 모든 문자열은 textContent·value로만 넣는다.
import { request } from "../api.js";

// 서버 한도와 같다(server/app/features/materials/schemas.py). 최종 판단은 서버가 한다.
const LIMITS = { url: 2048, title: 200, description: 2000, body: 20000, save_reason: 2000, memo: 2000 };
const FIELDS = [
  ["title", "제목", "input"],
  ["description", "설명(내가 쓰는 요약·맥락)", "textarea", 3],
  ["body", "본문·핵심 내용(원문에서 가져온 내용)", "textarea", 6],
  ["save_reason", "저장 이유", "textarea", 2],
  ["memo", "메모", "textarea", 2],
];
const STATUS = {
  link_only: ["링크만 저장됨 · 본문 미확인", "amber"],
  awaiting_start: ["분석 시작 대기", "mint"],
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

function field(name, label, kind, rows) {
  const input = kind === "textarea"
    ? el("textarea", { rows: String(rows || 3), maxlength: String(LIMITS[name]), "data-field": name })
    : el("input", { type: name === "url" ? "url" : "text", maxlength: String(LIMITS[name]), "data-field": name });
  return el("label", {}, el("span", { text: label }), input);
}

function readFields(root) {
  const data = {};
  for (const input of root.querySelectorAll("[data-field]")) data[input.dataset.field] = input.value;
  return data;
}

function statusTag(material) {
  const [text, tone] = STATUS[material.analysis_status] || [material.analysis_status, ""];
  return el("span", { class: `tag ${tone}`, text });
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

  // ── 목록 ──
  const list = el("ul", { class: "material-list" });
  const more = el("button", { class: "button secondary small", type: "button", text: "더 보기", hidden: "" });
  const listStatus = el("p", { class: "form-status", role: "status" });
  const listSection = el("section", { class: "panel" }, el("h2", { text: "접수 목록" }), list, more, listStatus);
  root.append(form, listSection);

  let items = [];
  let nextCursor = null;

  function renderList() {
    if (!items.length) {
      list.replaceChildren(el("li", { class: "empty-row", text: "아직 받은 자료가 없습니다." }));
    } else {
      list.replaceChildren(...items.map(row));
    }
    more.hidden = !nextCursor;
  }

  function row(material) {
    const temp = material.title_source !== "user";
    const head = el("button", { class: "material-head", type: "button", "aria-expanded": "false" },
      el("strong", { text: material.display_title || "(제목 없음)" }),
      temp ? el("span", { class: "temp-title", text: material.title_source === "url" ? "· 주소로 표시" : "· 내용 앞부분" }) : null);
    const meta = el("div", { class: "material-meta" },
      statusTag(material),
      el("span", { text: SEOUL.format(new Date(material.registered_at)) }),
      material.url ? el("span", { class: "url", text: material.url }) : null);
    const li = el("li", {}, head, meta);
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
    const save = el("button", { class: "button primary small", type: "button", text: "수정 저장" });
    const status = el("p", { class: "form-status", role: "status" });
    detail.append(el("div", { class: "form-actions" }, save, status));
    li.append(detail);

    save.addEventListener("click", async () => {
      save.disabled = true;
      status.textContent = "저장하는 중…";
      try {
        const updated = await guarded(api(`/api/materials/${encodeURIComponent(material.id)}`, {
          method: "PUT", body: { expected_version: material.version, ...readFields(detail) } }));
        items = items.map((m) => (m.id === updated.id ? updated : m));
        renderList();
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
      const page = await guarded(api(`/api/materials?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`));
      items = cursor ? [...items, ...page.items] : page.items;
      nextCursor = page.next_cursor;
      renderList();
      listStatus.textContent = "";
    } catch (error) {
      fail(error, listStatus, () => load(cursor));
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

  async function send() {
    const data = readFields(form);
    const body = Object.fromEntries(Object.entries(data).filter(([, v]) => v.trim()));
    submit.disabled = true;
    formStatus.textContent = "접수하는 중…";
    try {
      afterCreate(await guarded(api("/api/materials", { method: "POST", body })));
    } catch (error) {
      // 연결이 끊겨 결과를 모를 때는 같은 Idempotency-Key로 다시 보내 중복 접수를 막는다.
      fail(error, formStatus, () => error.retry().then(afterCreate).catch((e) => fail(e, formStatus)));
    } finally {
      submit.disabled = false;
    }
  }

  submit.addEventListener("click", send);
  more.addEventListener("click", () => load(nextCursor));
  load();
}
