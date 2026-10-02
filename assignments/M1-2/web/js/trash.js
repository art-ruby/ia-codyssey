// 웹 자료 휴지통(T05.03): 휴지통 이동 버튼, 휴지통 탭(목록·복원·영구 삭제 확인), 요청 형식.
// 영구 삭제는 확인 단계에서 지워지는 범위와 이전 대화 인용문 안내를 보여준 뒤에만 보낸다.
// 모든 문자열은 textContent로만 넣는다.
import { el } from "./priority.js";

const SEOUL = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "short" });
const STEP = { intake: "접수 기록", url_index: "같은 URL 예약", links: "관련 자료 연결", requests: "요청 기록 정리", material: "자료 본문" };

export const DELETE_SCOPE = [
  "자료의 제목·설명·본문·저장 이유·메모·AI 분석 결과",
  "접수 기록(접수 건수에서 빠집니다)",
  "같은 URL 확인용 예약",
  "관련 자료 연결·관련 없음 기록",
  "요청 기록에 남은 이 자료의 내용(기록 자체는 비운 채 남깁니다)",
];
export const CHAT_NOTICE = "이전 대화에 인용된 문장은 그 대화를 따로 지우기 전까지 대화 기록에 남을 수 있습니다.";

export function trashItem(material) {
  return { material_id: material.id, expected_version: material.version, action: "trash" };
}

export function deletePath(material) {
  return `/api/trash/${encodeURIComponent(material.id)}?expected_version=${material.version}&confirm=permanent`;
}

export function trashStateText(material) {
  if (material.lifecycle === "deleting") {
    return material.deletion_failed_step
      ? `영구 삭제 일부 실패(${STEP[material.deletion_failed_step] || material.deletion_failed_step}) · 다시 시도하세요`
      : "영구 삭제 진행 중 · 끝나지 않았으면 다시 시도하세요";
  }
  return material.review_status === "approved" ? "휴지통 · 보관했던 자료" : "휴지통 · 미승인 자료(복원해도 미승인)";
}

// 상세 화면의 '휴지통으로 이동'. 성공하면 onDone(옮겨진 자료).
export function trashButton(material, { api, onDone, onError }) {
  const button = el("button", { class: "button secondary small", type: "button", text: "휴지통으로 이동" });
  const status = el("span", { class: "form-status", role: "status" });
  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "옮기는 중…";
    try {
      const res = await api("/api/reviews/approve", { method: "POST", body: { items: [trashItem(material)] } });
      const result = res.results[0];
      if (result.status === "trashed") {
        status.textContent = "휴지통으로 옮겼습니다. 지식 보관함의 휴지통 탭에서 복원할 수 있습니다.";
        onDone(result.material);
        return;
      }
      status.textContent = result.status === "conflict" ? "다른 곳에서 먼저 바뀌었습니다. 새로 불러온 뒤 다시 시도하세요."
        : "이미 휴지통에 있거나 옮길 수 없는 자료입니다.";
    } catch (error) {
      status.textContent = "";
      if (error.kind === "http" && [404, 409, 422].includes(error.status)) status.textContent = error.detail;
      else onError(error, () => button.click());
    }
    button.disabled = false;
  });
  return el("span", { class: "trash-action" }, button, status);
}

// 지식 보관함의 휴지통 탭. onChanged(): 복원 등으로 보관 자료 목록이 바뀌었을 때.
// opts: { api, isCurrent(), onError(error, retry), onChanged() }
export function renderTrashTab(root, opts) {
  const status = el("p", { class: "form-status", role: "status" });
  const list = el("ul", { class: "material-list" });
  root.replaceChildren(el("p", { class: "field-note", text: "휴지통 자료는 검색·채팅·오늘 화면에 나오지 않습니다. 자동으로 지워지지 않습니다." }),
    status, list);

  async function load(message = "") {
    status.textContent = "불러오는 중…";
    try {
      const view = await opts.api("/api/trash");
      if (!opts.isCurrent()) return;
      list.replaceChildren(...(view.items.length ? view.items.map(row)
        : [el("li", { class: "empty-row", text: "휴지통이 비어 있습니다." })]));
      status.textContent = [message, view.truncated ? "최근 500건까지만 표시합니다." : ""].filter(Boolean).join(" ");
    } catch (error) {
      if (!opts.isCurrent()) return;
      status.textContent = "휴지통을 불러오지 못했습니다.";
      opts.onError(error, () => load(message));
    }
  }

  async function send(path, options, done) {
    try {
      const res = await opts.api(path, options);
      if (!opts.isCurrent()) return;
      await load(done(res));
    } catch (error) {
      if (!opts.isCurrent()) return;
      if (error.kind === "http" && [404, 409, 422].includes(error.status)) await load(error.detail);
      else opts.onError(error, () => load());
    }
  }

  function row(material) {
    const restore = el("button", { class: "button secondary small", type: "button", text: "복원" });
    const remove = el("button", { class: "button secondary small danger", type: "button",
      text: material.lifecycle === "deleting" ? "영구 삭제 다시 시도" : "영구 삭제" });
    const actions = el("div", { class: "form-actions" }, material.lifecycle === "deleting" ? null : restore, remove);
    const li = el("li", { "data-id": material.id },
      el("strong", { text: material.display_title || "(제목 없음)" }),
      el("div", { class: "material-meta" },
        el("span", { class: `tag ${material.lifecycle === "deleting" ? "amber" : ""}`, text: trashStateText(material) }),
        material.trashed_at ? el("span", { text: `${SEOUL.format(new Date(material.trashed_at))} 휴지통으로 이동` }) : null),
      actions);

    restore.addEventListener("click", () => {
      restore.disabled = true;
      remove.disabled = true;
      send(`/api/trash/${encodeURIComponent(material.id)}/restore`,
        { method: "POST", body: { expected_version: material.version } },
        () => { opts.onChanged(); return "복원했습니다. 원래 검토·보관 상태로 돌아갔습니다."; });
    });
    remove.addEventListener("click", () => {
      const confirmBtn = el("button", { class: "button primary small danger", type: "button", text: "영구 삭제 확인" });
      const cancel = el("button", { class: "button secondary small", type: "button", text: "취소" });
      const box = el("div", { class: "analysis-confirm" },
        el("p", { text: "영구 삭제하면 되돌릴 수 없습니다. 지워지는 것:" }),
        el("ul", {}, ...DELETE_SCOPE.map((t) => el("li", { text: t }))),
        el("p", { text: CHAT_NOTICE }),
        el("div", { class: "form-actions" }, confirmBtn, cancel));
      actions.replaceWith(box);
      cancel.addEventListener("click", () => box.replaceWith(actions));
      confirmBtn.addEventListener("click", () => {
        confirmBtn.disabled = true;
        cancel.disabled = true;
        send(deletePath(material), { method: "DELETE" }, (res) => (res.status === "deleted"
          ? "영구 삭제했습니다."
          : `일부 단계(${STEP[res.failed_step] || res.failed_step})에서 실패해 삭제를 끝내지 못했습니다. 다시 시도하세요.`));
      });
    });
    return li;
  }

  load();
  return { reload: load };
}
