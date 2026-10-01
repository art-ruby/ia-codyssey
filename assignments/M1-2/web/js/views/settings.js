// S10 프로젝트·설정 화면: 자료 모드 안내, 관심·활동 분야와 기본 프로젝트, 프로젝트 관리.
// 모든 문자열은 textContent·value로만 넣는다. 확인 대화상자(alert/confirm)는 쓰지 않는다.
import { request } from "../api.js";

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

const lines = (text) => text.split("\n").map((s) => s.trim()).filter(Boolean);

// root: 화면 영역, ctx: { mode, isCurrent(), onError(error, retry) }
export function renderSettings(root, ctx) {
  const { mode } = ctx;
  const api = (path, options = {}) => request(path, { mode, ...options });

  // 모드 전환·화면 이동 뒤 늦게 도착한 응답은 버린다(이전 모드 자료가 보이지 않게).
  async function guarded(promise) {
    const result = await promise;
    if (!ctx.isCurrent()) throw new Error("stale");
    return result;
  }

  function fail(error, statusNode, retry) {
    if (error.message === "stale") return;
    if (error.kind === "http" && (error.status === 409 || error.status === 422)) {
      // 입력 형식 오류(422)는 서버가 필드별 목록으로 돌려주므로 공통 문구로 안내한다.
      statusNode.textContent = String(error.detail).startsWith("HTTP ")
        ? "입력 내용을 확인하세요. 이름은 1~50자, 설명은 500자, 분야는 한 줄에 50자·최대 20개입니다."
        : error.detail;
      return;
    }
    ctx.onError(error, retry);
  }

  // ── 자료 모드 ──
  const modeSection = el("section", { class: "panel" },
    el("h2", { text: "자료 모드" }),
    el("p", { text: mode === "sample"
      ? "지금은 표본 자료를 보고 있습니다. 표본 모드의 프로젝트·설정은 개인 자료와 따로 저장됩니다."
      : "지금은 내 자료를 보고 있습니다. 상단의 '자료' 선택으로 표본 자료로 바꿀 수 있습니다." }));

  // ── 관심·활동 분야 ──
  const interests = el("textarea", { rows: "5", "aria-label": "관심 분야" });
  const activities = el("textarea", { rows: "5", "aria-label": "활동 분야" });
  const defaultProject = el("select", { "aria-label": "기본 프로젝트" });
  const saveBtn = el("button", { class: "button primary small", type: "button", text: "설정 저장" });
  const settingsNote = el("p", { class: "field-note" });
  const settingsStatus = el("p", { class: "form-status", role: "status" });
  let settingsVersion = 0;

  const settingsSection = el("section", { class: "panel form" },
    el("h2", { text: "관심 분야·활동 분야" }),
    el("p", { text: "자료를 분석할 때 나에게 중요한 이유를 판단하는 기준입니다. 한 줄에 하나씩 적습니다(최대 20개, 각 50자)." }),
    settingsNote,
    el("label", {}, el("span", { text: "관심 분야" }), interests),
    el("label", {}, el("span", { text: "활동 분야" }), activities),
    el("label", {}, el("span", { text: "기본 프로젝트" }), defaultProject),
    el("div", { class: "form-actions" }, saveBtn, settingsStatus));

  // ── 프로젝트 ──
  const projectList = el("ul", { class: "project-list" });
  const newName = el("input", { type: "text", maxlength: "50", placeholder: "프로젝트 이름", "aria-label": "새 프로젝트 이름" });
  const newDesc = el("input", { type: "text", maxlength: "500", placeholder: "설명(선택)", "aria-label": "새 프로젝트 설명" });
  const addBtn = el("button", { class: "button primary small", type: "button", text: "추가" });
  const projectStatus = el("p", { class: "form-status", role: "status" });
  let projects = [];

  const projectSection = el("section", { class: "panel form" },
    el("h2", { text: "프로젝트" }),
    el("p", { text: "자료를 연결할 프로젝트입니다. 지우지 않고 비활성화하면 기존 자료의 연결이 유지됩니다." }),
    projectList,
    el("div", { class: "inline-form" }, newName, newDesc, addBtn),
    projectStatus);

  root.append(modeSection, settingsSection, projectSection);

  function fillDefaultProject(selectedId) {
    const active = projects.filter((p) => p.active);
    defaultProject.replaceChildren(el("option", { value: "", text: "없음" }),
      ...active.map((p) => el("option", { value: p.id, text: p.name })));
    defaultProject.value = active.some((p) => p.id === selectedId) ? selectedId : "";
  }

  function renderProjects() {
    if (!projects.length) {
      projectList.replaceChildren(el("li", { class: "empty-row", text: "아직 프로젝트가 없습니다." }));
      return;
    }
    projectList.replaceChildren(...projects.map(projectRow));
  }

  function projectRow(project) {
    const row = el("li", { class: project.active ? "" : "inactive" });
    const edit = el("button", { class: "button secondary small", type: "button", text: "수정" });
    const toggle = el("button", { class: "button secondary small", type: "button",
      text: project.active ? "비활성화" : "다시 활성화" });
    row.append(el("div", { class: "project-view" },
      el("div", {},
        el("strong", { text: project.name }),
        project.active ? null : el("span", { class: "tag", text: "비활성" }),
        project.description ? el("p", { text: project.description }) : null),
      el("div", { class: "row-actions" }, edit, toggle)));

    toggle.addEventListener("click", () => saveProject(project, { active: !project.active }));
    edit.addEventListener("click", () => {
      const name = el("input", { type: "text", maxlength: "50", value: project.name, "aria-label": "프로젝트 이름" });
      const desc = el("input", { type: "text", maxlength: "500", value: project.description || "", "aria-label": "프로젝트 설명" });
      const save = el("button", { class: "button primary small", type: "button", text: "저장" });
      const cancel = el("button", { class: "button secondary small", type: "button", text: "취소" });
      row.replaceChildren(el("div", { class: "inline-form" }, name, desc, save, cancel));
      name.focus();
      cancel.addEventListener("click", renderProjects);
      save.addEventListener("click", () => saveProject(project, { name: name.value, description: desc.value }));
    });
    return row;
  }

  async function loadAll() {
    settingsStatus.textContent = "불러오는 중…";
    projectStatus.textContent = "";
    try {
      const [projectData, settings] = await guarded(Promise.all([
        api("/api/projects?include_inactive=true"), api("/api/settings")]));
      projects = projectData.items;
      renderProjects();
      settingsVersion = settings.version;
      interests.value = settings.interests.join("\n");
      activities.value = settings.activities.join("\n");
      fillDefaultProject(settings.default_project_id);
      settingsNote.textContent = settings.saved ? "" : "아직 저장하지 않은 기본값입니다. 저장하면 이 값이 기준이 됩니다.";
      settingsStatus.textContent = "";
    } catch (error) {
      fail(error, settingsStatus, loadAll);
    }
  }

  async function saveSettings() {
    saveBtn.disabled = true;
    settingsStatus.textContent = "저장하는 중…";
    try {
      const saved = await guarded(api("/api/settings", { method: "PUT", body: {
        expected_version: settingsVersion,
        interests: lines(interests.value),
        activities: lines(activities.value),
        default_project_id: defaultProject.value || null,
      } }));
      settingsVersion = saved.version;
      interests.value = saved.interests.join("\n");
      activities.value = saved.activities.join("\n");
      settingsNote.textContent = "";
      settingsStatus.textContent = "저장했습니다.";
    } catch (error) {
      if (error.kind === "http" && error.status === 409) {
        await loadAll();
        settingsStatus.textContent = "다른 곳에서 먼저 바뀌어 최신 설정을 다시 불러왔습니다. 확인 후 다시 저장하세요.";
      } else {
        fail(error, settingsStatus, saveSettings);
      }
    } finally {
      saveBtn.disabled = false;
    }
  }

  async function saveProject(project, changes) {
    projectStatus.textContent = "저장하는 중…";
    try {
      const updated = await guarded(api(`/api/projects/${encodeURIComponent(project.id)}`, {
        method: "PUT", body: { expected_version: project.version, ...changes } }));
      projects = projects.map((p) => (p.id === updated.id ? updated : p));
      renderProjects();
      fillDefaultProject(defaultProject.value);
      projectStatus.textContent = "저장했습니다.";
    } catch (error) {
      // 이름 중복(409)은 메시지만, 버전 충돌(409)은 최신 목록을 다시 불러온다.
      if (error.kind === "http" && error.status === 409 && !String(error.detail).includes("이름")) {
        await loadAll();
        projectStatus.textContent = "다른 곳에서 먼저 바뀌어 목록을 다시 불러왔습니다.";
      } else {
        fail(error, projectStatus, () => saveProject(project, changes));
      }
    }
  }

  async function addProject() {
    addBtn.disabled = true;
    projectStatus.textContent = "추가하는 중…";
    try {
      const created = await guarded(api("/api/projects", { method: "POST",
        body: { name: newName.value, description: newDesc.value } }));
      projects = [...projects, created];
      renderProjects();
      fillDefaultProject(defaultProject.value);
      newName.value = "";
      newDesc.value = "";
      projectStatus.textContent = "추가했습니다.";
    } catch (error) {
      fail(error, projectStatus, addProject);
    } finally {
      addBtn.disabled = false;
    }
  }

  saveBtn.addEventListener("click", saveSettings);
  addBtn.addEventListener("click", addProject);
  newName.addEventListener("keydown", (event) => {
    if (event.key === "Enter") addProject();
  });
  loadAll();
}
