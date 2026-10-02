// 자료 분석 패널(T04.02): 시작 전 전송 범위 확인, 분석 중 상태 조회, 결과·실패·확인 필요 표시와 재시도.
// 분석은 사용자가 누를 때만 시작한다. 결과는 AI 제안이며 사실 확인 전이라는 표시를 함께 보여준다.
// 모든 문자열은 textContent로만 넣는다. 사용량 숫자·남은 한도는 T04.03에서 더한다.

const SENT_FIELDS = [["title", "제목"], ["description", "설명"], ["body", "본문"], ["save_reason", "저장 이유"], ["memo", "메모"]];
const IMPORTANCE = { high: "높음", medium: "보통", low: "낮음" };
const KIND = { article: "글", document: "문서", note: "메모", reference: "참고 자료", tool: "도구", other: "기타" };
const ERROR = {
  input_changed: "분석하는 동안 내용이 바뀌어 결과를 저장하지 않았습니다.",
  ai_excluded: "분석하는 동안 AI 분석 제외를 켜서 결과를 저장하지 않았습니다.",
  rate_limited: "AI 요청 한도에 걸렸습니다. 잠시 뒤 다시 시도하세요.",
  timeout: "AI 응답 시간이 초과되었습니다.",
  invalid_output: "AI 응답 형식이 맞지 않아 저장하지 않았습니다.",
  ungrounded_output: "AI 응답이 자료 내용과 맞지 않아 저장하지 않았습니다.",
  output_truncated: "AI 응답이 길이 한도에서 잘려 저장하지 않았습니다.",
  missing_ai_settings: "서버의 AI 설정이 비어 있어 보내지 않았습니다.",
  hermes_tools_enabled: "AI 서버에 도구가 켜져 있어 자료를 보내지 않았습니다.",
  hermes_toolset_check_failed: "AI 서버의 안전 설정을 확인하지 못해 자료를 보내지 않았습니다.",
  provider_connection_error: "AI 서버에 연결하지 못했습니다.",
  provider_http_error: "AI 서버가 오류로 응답했습니다.",
};
const POLL_MS = 3000;

// 화면 표시 상태(순수 함수, 테스트 대상). action: start | retry | reanalyze | null
export function analysisState(m) {
  if (m.ai_excluded) return { label: "AI 분석 제외", tone: "", action: null };
  if (m.lifecycle && m.lifecycle !== "active") return { label: "휴지통", tone: "", action: null };
  switch (m.analysis_status) {
    case "link_only":
      return { label: "링크만 저장됨 · 본문 미확인", tone: "amber", action: null };
    case "analyzing":
      return m.analysis_stale
        ? { label: "결과 확인 필요", tone: "amber", action: "retry",
          note: "분석이 끝났는지 확인되지 않았습니다(서버 재시작 등). 다시 시작하면 AI 요청이 1회 더 나갑니다." }
        : { label: "분석 중", tone: "mint", action: null, polling: true };
    case "failed":
      return { label: "분석 실패", tone: "amber", action: "retry",
        note: ERROR[m.analysis_error] || "분석하지 못했습니다. 입력은 그대로 남아 있습니다." };
    case "done":
      return m.analysis_outdated
        ? { label: "내용 변경 · 다시 분석 필요", tone: "amber", action: "reanalyze", result: true,
          note: "아래 결과는 고치기 전 내용 기준입니다." }
        : { label: "분석 완료", tone: "mint", action: null, result: true };
    default:
      return { label: "분석 시작 대기", tone: "mint", action: "start", note: ERROR[m.analysis_error] };
  }
}

// 이번 분석에 AI로 보내는 항목과 글자 수(서버 Adapter와 같은 필드).
export function sendScope(m) {
  const fields = SENT_FIELDS.filter(([name]) => m[name]);
  return { labels: fields.map(([, label]) => label), chars: fields.reduce((sum, [name]) => sum + m[name].length, 0) };
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (name === "text") node.textContent = value;
    else node.setAttribute(name, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

function resultView(m) {
  const scope = m.ai_checked_scope || {};
  const scopeText = `${(scope.fields || []).map((f) => (SENT_FIELDS.find(([n]) => n === f) || [f, f])[1]).join("·")} ${scope.chars || 0}자 확인`
    + (m.url ? " · 링크 내용은 열어 보지 않음" : "");
  const list = (items) => (items && items.length ? el("ul", {}, ...items.map((t) => el("li", { text: t }))) : null);
  return el("div", { class: "analysis-result" },
    el("p", { class: "analysis-caution", text: "AI 제안 · 사실 확인 안 됨 — 인용문만 원문과 대조했습니다. 판단과 수정은 직접 하세요." }),
    el("dl", {},
      el("dt", { text: "제목 제안" }), el("dd", { text: m.ai_title || "" }),
      el("dt", { text: "요약" }), el("dd", { text: m.ai_summary || "" }),
      el("dt", { text: "중요도 제안" }),
      el("dd", { text: `${m.ai_importance ? IMPORTANCE[m.ai_importance] : "판단 보류"} — ${m.ai_importance_reason || ""}` }),
      m.ai_kind ? el("dt", { text: "종류" }) : null, m.ai_kind ? el("dd", { text: KIND[m.ai_kind] || m.ai_kind }) : null,
      m.ai_recommended_action ? el("dt", { text: "권장 행동" }) : null,
      m.ai_recommended_action ? el("dd", { text: m.ai_recommended_action }) : null,
      m.ai_keywords && m.ai_keywords.length ? el("dt", { text: "핵심어" }) : null,
      m.ai_keywords && m.ai_keywords.length ? el("dd", { text: m.ai_keywords.join(", ") }) : null),
    m.ai_uncertainties && m.ai_uncertainties.length ? el("p", { class: "analysis-label", text: "불확실한 점" }) : null,
    list(m.ai_uncertainties),
    el("p", { class: "analysis-label", text: "근거 인용" }),
    ...(m.ai_evidence || []).map((q) => el("blockquote", { text: q })),
    el("p", { class: "analysis-scope", text: scopeText }));
}

// opts: { api(path, options), isCurrent(), onChange(material), onError(error, retry) }
export function analysisPanel(material, opts) {
  const root = el("section", { class: "analysis", "aria-live": "polite" });
  let current = material;
  let timer = null;

  function stopPolling() {
    clearTimeout(timer);
    timer = null;
  }

  function poll() {
    stopPolling();
    timer = setTimeout(async () => {
      if (!root.isConnected || !opts.isCurrent()) return stopPolling();
      try {
        update(await opts.api(`/api/materials/${encodeURIComponent(current.id)}`));
      } catch (error) {
        if (error.status === 404) return render("자료를 찾을 수 없습니다.");
        poll(); // 일시적인 연결 실패는 다음 주기에 다시 조회한다(조회만 하므로 AI 요청은 늘지 않는다)
      }
    }, POLL_MS);
  }

  function update(next) {
    current = next;
    opts.onChange(next);
    render();
  }

  function confirmBox(button, message) {
    const scope = sendScope(current);
    const send = el("button", { class: "button primary small", type: "button", text: "보내고 분석 시작" });
    const cancel = el("button", { class: "button secondary small", type: "button", text: "취소" });
    const box = el("div", { class: "analysis-confirm" },
      el("p", { text: `외부 AI(Hermes)로 보낼 내용: ${scope.labels.join("·")} (${scope.chars.toLocaleString("ko-KR")}자)` }),
      el("p", { text: `${current.url ? "URL은 열어 보지 않고 주소 문자열만 보냅니다. " : ""}AI 요청 1회가 사용량에 기록됩니다. 결과는 제안일 뿐이며 자료·중요도는 바뀌지 않습니다.` }),
      el("div", { class: "form-actions" }, send, cancel));
    cancel.addEventListener("click", () => render());
    send.addEventListener("click", async () => {
      send.disabled = true;
      cancel.disabled = true;
      message.textContent = "요청을 보내는 중…";
      try {
        const res = await opts.api(`/api/materials/${encodeURIComponent(current.id)}/analyze`,
          { method: "POST", body: { expected_version: current.version } });
        update(res.material);
        if (res.status === "reused") root.querySelector(".form-status").textContent = "같은 내용의 분석 결과가 있어 AI를 다시 부르지 않았습니다.";
      } catch (error) {
        if (error.kind === "http" && [404, 409, 422].includes(error.status)) render(error.detail);
        else opts.onError(error, () => render());
      }
    });
    button.replaceWith(box);
  }

  function render(messageText = "") {
    stopPolling();
    const state = analysisState(current);
    const message = el("p", { class: "form-status", role: "status", text: messageText });
    const head = el("div", { class: "analysis-head" },
      el("strong", { text: "AI 분석" }), el("span", { class: `tag ${state.tone}`, text: state.label }));
    const children = [head];
    if (state.note) children.push(el("p", { class: "row-note", text: state.note }));
    if (state.action) {
      const label = { start: "분석 시작", retry: "다시 시도", reanalyze: "다시 분석" }[state.action];
      const button = el("button", { class: "button secondary small", type: "button", text: label });
      button.addEventListener("click", () => confirmBox(button, message));
      children.push(button);
    }
    children.push(message);
    if (state.result) children.push(resultView(current));
    root.replaceChildren(...children);
    if (state.polling) poll();
  }

  render();
  return root;
}
