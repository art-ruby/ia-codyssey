// 관련 자료 패널(T05.02): 근거 있는 보관 자료 후보(제안)와 내가 확정한 연결을 나눠 보여주고,
// 연결·관련 없음·연결 해제를 승인 API(action=link)로 보낸다. 같은 URL 경고(받은 자료)와는 다른 기능이다.
// 후보 계산은 자료를 훑는 작업이라 '관련 자료 보기'를 눌렀을 때만 불러온다. 모든 문자열은 textContent로만 넣는다.
import { el } from "./priority.js";

const REASON = {
  trashed: "휴지통에 있는 자료는 연결할 수 없습니다.",
  target_unavailable: "상대 자료가 보관 상태가 아니어서(미승인·휴지통) 연결할 수 없습니다.",
  same_url: "같은 URL 자료는 받은 자료의 중복 확인에서 처리합니다.",
  not_linked: "연결되어 있지 않은 자료입니다.",
};

// "같은 프로젝트: 결제 개편 · 함께 나오는 단어: 정산, oauth"
export function evidenceText(evidence) {
  return (evidence || []).map((e) => `${e.label}: ${e.values.join(", ")}`).join(" · ");
}

// 승인 API 항목. 두 자료의 버전을 보내 내가 본 내용인지 서버가 확인한다.
export function linkItem(material, target, decision) {
  return { material_id: material.id, expected_version: material.version, action: "link",
    link: { target_id: target.id, target_version: target.version, decision } };
}

export function resultMessage(result) {
  switch (result.status) {
    case "linked": return "관련 자료로 연결했습니다.";
    case "marked_unrelated": return "관련 없음으로 기록했습니다. 다시 제안하지 않습니다.";
    case "unlinked": return "연결을 해제했습니다.";
    case "conflict": return "다른 곳에서 먼저 바뀌었습니다. 최신 내용으로 다시 불러왔습니다.";
    case "not_found": return "자료를 찾을 수 없습니다.";
    default: return REASON[result.reason] || "처리하지 못했습니다.";
  }
}

// opts: { api(path, options), isCurrent(), onError(error, retry) }
export function relatedPanel(material, opts) {
  const root = el("section", { class: "related", "aria-live": "polite" });
  const open = el("button", { class: "button secondary small", type: "button", text: "관련 자료 보기" });
  const status = el("p", { class: "form-status", role: "status" });
  const body = el("div");
  root.append(el("div", { class: "analysis-head" }, el("strong", { text: "관련 자료" }), open), status, body);
  let current = material;

  async function load(message = "") {
    status.textContent = "불러오는 중…";
    try {
      const [fresh, view] = await Promise.all([
        opts.api(`/api/materials/${encodeURIComponent(material.id)}`),
        opts.api(`/api/materials/${encodeURIComponent(material.id)}/related`),
      ]);
      if (!opts.isCurrent()) return;
      current = fresh;
      render(view);
      status.textContent = message;
    } catch (error) {
      if (!opts.isCurrent()) return;
      status.textContent = "";
      if (error.kind === "http" && error.status === 404) status.textContent = "자료를 찾을 수 없습니다.";
      else opts.onError(error, () => load(message));
    }
  }

  async function decide(target, decision, buttons) {
    for (const b of buttons) b.disabled = true;
    status.textContent = "저장하는 중…";
    try {
      const res = await opts.api("/api/reviews/approve", { method: "POST", body: { items: [linkItem(current, target, decision)] } });
      if (!opts.isCurrent()) return;
      await load(resultMessage(res.results[0]));
    } catch (error) {
      if (!opts.isCurrent()) return;
      for (const b of buttons) b.disabled = false;
      if (error.kind === "http" && [404, 409, 422].includes(error.status)) status.textContent = error.detail;
      else opts.onError(error, () => load());
    }
  }

  function card(item, evidence, actions, note = null) {
    return el("li", { class: "related-card", "data-id": item.id },
      el("strong", { text: item.display_title || "(제목 없음)" }),
      evidence && evidence.length ? el("p", { class: "related-evidence", text: `근거 — ${evidenceText(evidence)}` }) : null,
      note,
      el("div", { class: "form-actions" }, ...actions));
  }

  function render(view) {
    const suggestions = view.candidates.map((c) => {
      const link = el("button", { class: "button primary small", type: "button", text: "관련 자료로 연결" });
      const unrelated = el("button", { class: "button secondary small", type: "button", text: "관련 없음" });
      link.addEventListener("click", () => decide(c.material, "link", [link, unrelated]));
      unrelated.addEventListener("click", () => decide(c.material, "unrelated", [link, unrelated]));
      return card(c.material, c.evidence, [link, unrelated]);
    });
    const confirmed = view.confirmed.map((c) => {
      const unlink = el("button", { class: "button secondary small", type: "button", text: "연결 해제" });
      unlink.addEventListener("click", () => decide(c.material, "unlink", [unlink]));
      const note = c.available ? null
        : el("p", { class: "row-note", text: "상대 자료가 휴지통에 있거나 지워져 지금은 볼 수 없습니다." });
      return card(c.material, c.evidence, [unlink], note);
    });
    // replaceChildren은 null을 "null" 글자로 넣으므로 빈 항목을 먼저 거른다.
    body.replaceChildren(...[
      el("p", { class: "analysis-label", text: `내가 연결한 자료 ${confirmed.length}건` }),
      confirmed.length ? el("ul", { class: "related-list" }, ...confirmed) : el("p", { class: "empty-row", text: "아직 연결한 자료가 없습니다." }),
      el("p", { class: "analysis-label", text: `제안 ${suggestions.length}건(아직 연결되지 않음)` }),
      suggestions.length ? el("ul", { class: "related-list" }, ...suggestions)
        : el("p", { class: "empty-row", text: "근거가 충분한 보관 자료가 없어 제안하지 않습니다." }),
      view.unrelated_count ? el("p", { class: "field-note", text: `관련 없음으로 기록한 자료 ${view.unrelated_count}건은 제안에서 뺐습니다.` }) : null,
      view.scope.truncated ? el("p", { class: "field-note", text: `최근 ${view.scope.scanned}건까지만 비교했습니다.` }) : null,
    ].filter(Boolean));
    open.textContent = "다시 불러오기";
  }

  open.addEventListener("click", () => load());
  return root;
}
