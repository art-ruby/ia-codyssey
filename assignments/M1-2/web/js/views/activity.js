// S03 활동 기록 탭(T06.04): 숫자 요약(출처·지표·기간 선택)과 숫자 기록 CRUD.
// 기록을 바꾸면 같은 조건으로 요약과 목록을 서버에서 다시 받는다(화면에 이전 값을 남기지 않음).
// 실제 값은 자료에서 계산하며 숫자 기록과 합산하지 않는다(PRD §11). 모든 문자열은 textContent·value로만 넣는다.
import { request } from "../api.js";
import {
  METRIC_OPTIONS, editableOrigin, periodText, sourceOptions, statsText, summaryCsv, summaryFilename, trendText,
} from "../activity-format.js";
import { el } from "../priority.js";

const METRIC_LABEL = Object.fromEntries(METRIC_OPTIONS);

function select(label, options, value) {
  const node = el("select", { "aria-label": label }, ...options.map(([v, text]) => el("option", { value: v, text })));
  if (value) node.value = value;
  return node;
}

// root: 탭 영역, ctx: { mode, isCurrent(), onError(error, retry) }
export function renderActivityTab(root, ctx) {
  const api = (path, options = {}) => request(path, { mode: ctx.mode, ...options });
  const source = select("출처", sourceOptions(ctx.mode));
  const metric = select("지표", METRIC_OPTIONS);
  const from = el("input", { type: "date", "aria-label": "시작 날짜" });
  const to = el("input", { type: "date", "aria-label": "끝 날짜" });
  const go = el("button", { class: "button primary small", type: "button", text: "요약 보기" });
  const csv = el("button", { class: "button secondary small", type: "button", text: "CSV 내보내기", disabled: "disabled" });
  const summaryBox = el("div", { class: "activity-summary", "aria-live": "polite" });
  const status = el("p", { class: "form-status", role: "status" });
  let currentSummary = null;

  const addDate = el("input", { type: "date", "aria-label": "기록 날짜" });
  const addMetric = select("기록 지표", METRIC_OPTIONS);
  const addValue = el("input", { type: "number", min: "0", step: "1", "aria-label": "건수" });
  const addMemo = el("input", { type: "text", "aria-label": "메모", placeholder: "메모(선택)" });
  const add = el("button", { class: "button secondary small", type: "button", text: "기록 추가" });
  const recordNote = el("p", { class: "field-note" });
  const list = el("ul", { class: "material-list" });

  root.replaceChildren(
    el("section", { class: "panel form" },
      el("div", { class: "search-filters" },
        el("label", {}, el("span", { text: "출처" }), source),
        el("label", {}, el("span", { text: "지표" }), metric),
        el("label", {}, el("span", { text: "기간(비우면 관측 시작~기준일)" }), el("div", { class: "date-range" }, from, el("span", { text: "~" }), to))),
      el("div", { class: "form-actions" }, go, csv), summaryBox),
    el("section", { class: "panel form" },
      el("h2", { class: "section-title", text: "숫자 기록" }), recordNote,
      el("div", { class: "search-filters" },
        el("label", {}, el("span", { text: "날짜" }), addDate), el("label", {}, el("span", { text: "지표" }), addMetric),
        el("label", {}, el("span", { text: "건수" }), addValue), el("label", {}, el("span", { text: "메모" }), addMemo)),
      el("div", { class: "form-actions" }, add), status, list));

  function query() {
    const params = new URLSearchParams({ metric_type: metric.value });
    if (source.value) params.set("source", source.value);
    if (from.value) params.set("start_date", from.value);
    if (to.value) params.set("end_date", to.value);
    return params;
  }

  function renderSummary(s) {
    currentSummary = s;
    csv.disabled = !s.daily.length;
    const recent = s.daily.slice(-14);
    const peak = Math.max(1, ...recent.map((d) => d.value));
    const totalHeight = 100;
    summaryBox.replaceChildren(...[
      el("p", { class: "activity-label", text: `${s.label} · ${periodText(s)}` }),
      el("p", { class: "activity-stats", text: statsText(s) }),
      el("p", { class: "activity-trend", text: trendText(s.trend) }),
      recent.length ? el("div", { class: "activity-bars", "aria-label": "최근 14일 일별 값" },
        ...recent.map((d) => el("span", { class: "activity-bar-wrap" },
          el("span", { class: "activity-bar-value", text: String(d.value) }),
          el("span", { class: "activity-bar", title: `${d.date}: ${d.value}건`,
            style: `height:${Math.max(2, Math.round((d.value / peak) * totalHeight))}%` }),
          el("span", { class: "activity-bar-date", text: d.date.slice(5) })))) : null,
    ].filter(Boolean));
  }

  function downloadCsv() {
    if (!currentSummary?.daily.length) {
      status.textContent = "내보낼 요약 데이터가 없습니다.";
      return;
    }
    const blob = new Blob([summaryCsv(currentSummary)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = el("a", { href: url, download: summaryFilename(currentSummary) });
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    status.textContent = "현재 요약을 CSV로 내보냈습니다.";
  }

  async function load(message = "") {
    status.textContent = "불러오는 중…";
    const origin = editableOrigin(ctx.mode, source.value);
    recordNote.textContent = origin
      ? `${ctx.mode === "sample" ? "가상(표본)" : "사용자 입력"} 기록입니다. 고치면 위 요약이 같은 조건으로 다시 계산됩니다.`
      : "실제 값은 자료(접수·보관 상태)에서 계산되며 아래 기록과 합산되지 않습니다. 기록을 고쳐도 실제 값은 바뀌지 않습니다.";
    try {
      const listParams = new URLSearchParams({ metric_type: metric.value, limit: "100" });
      if (from.value) listParams.set("date_from", from.value);
      if (to.value) listParams.set("date_to", to.value);
      const [s, records] = await Promise.all([api(`/api/data/summary?${query()}`), api(`/api/data?${listParams}`)]);
      if (!ctx.isCurrent()) return;
      renderSummary(s);
      list.replaceChildren(...(records.items.length ? records.items.map(row)
        : [el("li", { class: "empty-row", text: "이 조건의 숫자 기록이 없습니다." })]));
      status.textContent = [message, records.total > records.items.length ? `최근 ${records.items.length}건만 표시합니다(전체 ${records.total}건).` : ""]
        .filter(Boolean).join(" ");
    } catch (error) {
      if (!ctx.isCurrent()) return;
      if (error.kind === "http" && error.status === 422) status.textContent = error.detail;
      else { status.textContent = "불러오지 못했습니다."; ctx.onError(error, () => load(message)); }
    }
  }

  async function change(path, options, message) {
    try {
      await api(path, options);
      if (!ctx.isCurrent()) return;
      await load(message);  // 바꾼 뒤에는 늘 서버에서 다시 받는다
    } catch (error) {
      if (!ctx.isCurrent()) return;
      if (error.kind === "http" && [404, 409, 422].includes(error.status)) await load(error.detail);
      else ctx.onError(error, () => load());
    }
  }

  function readValue(input) {
    const value = Number(input.value);
    return input.value !== "" && Number.isInteger(value) && value >= 0 ? value : null;
  }

  function row(record) {
    const text = el("span", { text: `${record.date} · ${METRIC_LABEL[record.metric_type]} ${record.value}건${record.memo ? ` · ${record.memo}` : ""}` });
    const edit = el("button", { class: "button secondary small", type: "button", text: "수정" });
    const remove = el("button", { class: "button secondary small danger", type: "button", text: "삭제" });
    const actions = el("div", { class: "form-actions" }, edit, remove);
    const li = el("li", { "data-id": record.id }, text, actions);
    edit.addEventListener("click", () => {
      const date = el("input", { type: "date", value: record.date, "aria-label": "날짜" });
      const value = el("input", { type: "number", min: "0", step: "1", value: String(record.value), "aria-label": "건수" });
      const memo = el("input", { type: "text", value: record.memo || "", "aria-label": "메모" });
      const save = el("button", { class: "button primary small", type: "button", text: "저장" });
      const cancel = el("button", { class: "button secondary small", type: "button", text: "취소" });
      li.replaceChildren(el("div", { class: "inline-form" }, date, value, memo, save, cancel));
      cancel.addEventListener("click", () => li.replaceChildren(text, actions));
      save.addEventListener("click", () => {
        const v = readValue(value);
        if (v === null) { status.textContent = "건수는 0 이상의 정수로 입력하세요."; return; }
        save.disabled = true;
        change(`/api/data/${encodeURIComponent(record.id)}`,
          { method: "PUT", body: { expected_version: record.version, date: date.value, value: v, memo: memo.value } },
          "기록을 고쳤고 요약을 다시 계산했습니다.");
      });
    });
    remove.addEventListener("click", () => {
      const confirm = el("button", { class: "button primary small danger", type: "button", text: "삭제 확인" });
      const cancel = el("button", { class: "button secondary small", type: "button", text: "취소" });
      const box = el("div", { class: "form-actions" }, confirm, cancel);
      actions.replaceWith(box);
      cancel.addEventListener("click", () => box.replaceWith(actions));
      confirm.addEventListener("click", () => {
        confirm.disabled = true;
        change(`/api/data/${encodeURIComponent(record.id)}?expected_version=${record.version}`, { method: "DELETE" },
          "기록을 지웠고 요약을 다시 계산했습니다.");
      });
    });
    return li;
  }

  add.addEventListener("click", () => {
    const value = readValue(addValue);
    if (!addDate.value || value === null) { status.textContent = "날짜와 0 이상의 정수 건수를 입력하세요."; return; }
    change("/api/data", { method: "POST", body: { date: addDate.value, metric_type: addMetric.value, value, memo: addMemo.value } },
      "기록을 추가했고 요약을 다시 계산했습니다.");
    addValue.value = "";
    addMemo.value = "";
  });
  go.addEventListener("click", () => load());
  csv.addEventListener("click", downloadCsv);
  source.addEventListener("change", () => load());
  metric.addEventListener("change", () => { addMetric.value = metric.value; load(); });

  load();
  return { reload: load };
}
