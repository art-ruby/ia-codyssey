// 프로젝트·설정의 '소식 출처' 칸(설계 §8). 기본 출처는 끄기만, 직접 추가한 출처는 삭제할 수 있다.
import { request } from "../api.js";
import { kindLabel } from "../news.js";
import { el } from "../priority.js";

// ctx: { mode, isCurrent(), onError(error, retry) }. 개인 모드에서만 부른다.
export function newsSourcesPanel(ctx) {
  const api = (path, options = {}) => request(path, { mode: ctx.mode, ...options });
  const list = el("ul", { class: "project-list" });
  const name = el("input", { type: "text", placeholder: "이름", "aria-label": "새 소식 출처 이름" });
  const url = el("input", { type: "text", placeholder: "RSS·Atom 주소 (https://…)", "aria-label": "피드 주소" });
  const add = el("button", { class: "button primary small", type: "button", text: "추가" });
  const status = el("p", { class: "form-status", role: "status" });
  const panel = el("section", { class: "panel form" },
    el("h2", { text: "소식 출처" }),
    el("p", { text: "AI 동향의 '새 소식'을 가져올 곳입니다. 끄면 읽지 않습니다. 최대 20곳까지 RSS·Atom 주소를 추가할 수 있습니다." }),
    list, el("div", { class: "inline-form" }, name, url, add), status);

  const alive = () => ctx.isCurrent() && panel.isConnected;

  function fail(error, retry) {
    if (error.kind === "http" && ([404, 409, 422].includes(error.status) || error.data?.reason)) {
      status.textContent = String(error.detail).startsWith("HTTP ")
        ? "입력 내용을 확인하세요. 이름은 40자까지, 주소는 http·https만 됩니다." : error.detail;
      return;
    }
    ctx.onError(error, retry);
  }

  function row(source) {
    const toggle = el("input", { type: "checkbox", "aria-label": `${source.name} 켜기` });
    toggle.checked = source.enabled;
    const remove = source.builtin ? null : el("button", { class: "button secondary small danger", type: "button", text: "삭제" });
    const li = el("li", {}, el("div", { class: "project-view" },
      el("label", { class: "check" }, toggle,
        el("span", {}, el("strong", { text: source.name }), el("span", { class: "tag", text: kindLabel(source.kind) }),
          el("small", { class: "news-feed-url", text: source.feed_url }))),
      remove ? el("div", { class: "row-actions" }, remove) : null));

    toggle.addEventListener("change", async () => {
      toggle.disabled = true;
      try {
        await api(`/api/news/sources/${encodeURIComponent(source.id)}`,
          { method: "PUT", body: { enabled: toggle.checked, expected_version: source.version } });
        if (!alive()) return;
        status.textContent = toggle.checked ? `${source.name}을(를) 켰습니다.` : `${source.name}을(를) 껐습니다.`;
        await load();
      } catch (error) {
        toggle.checked = !toggle.checked;
        toggle.disabled = false;
        fail(error, () => load());
      }
    });
    remove?.addEventListener("click", async () => {
      remove.disabled = true;
      try {
        await api(`/api/news/sources/${encodeURIComponent(source.id)}`, { method: "DELETE" });
        if (!alive()) return;
        status.textContent = `${source.name}을(를) 삭제했습니다.`;
        await load();
      } catch (error) {
        remove.disabled = false;
        fail(error, () => remove.click());
      }
    });
    return li;
  }

  async function load() {
    try {
      const data = await api("/api/news/sources");
      if (!alive()) return;
      list.replaceChildren(...data.items.map(row));
    } catch (error) {
      if (!alive()) return;
      fail(error, load);
    }
  }

  add.addEventListener("click", async () => {
    add.disabled = true;
    status.textContent = "피드를 확인하는 중…";
    try {
      await api("/api/news/sources", { method: "POST", body: { name: name.value, feed_url: url.value } });
      if (!alive()) return;
      name.value = "";
      url.value = "";
      status.textContent = "추가했습니다. 다음 새로고침부터 읽습니다.";
      await load();
    } catch (error) {
      fail(error, () => add.click());
    } finally {
      add.disabled = false;
    }
  });

  load();
  return panel;
}
