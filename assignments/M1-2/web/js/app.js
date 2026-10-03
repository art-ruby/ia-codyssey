// 웹 셸: 로그인 확인·10개 메뉴·화면 전환·자료 모드·공통 오류 안내.
// 각 화면의 실제 기능은 이후 Task에서 이 셸의 screen 영역에 연결한다.
// 모든 문자열은 textContent로 넣어 HTML로 실행되지 않게 한다.
import { onUserChanged, signIn, signOut } from "./auth.js";
import { onSlowRequest, request } from "./api.js";
import { renderAsk } from "./views/ask.js";
import { renderConversations } from "./views/conversations.js";
import { renderInbox } from "./views/inbox.js";
import { renderKnowledge } from "./views/knowledge.js";
import { renderReview } from "./views/review.js";
import { renderSettings } from "./views/settings.js";
import { renderToday } from "./views/today.js";
import { renderTrends } from "./views/trends.js";

// 실제 기능이 연결된 화면. 나머지는 빈 상태로 둔다.
const VIEWS = { today: renderToday, inbox: renderInbox, knowledge: renderKnowledge, trends: renderTrends, ask: renderAsk,
  conversations: renderConversations, review: renderReview, settings: renderSettings };

// PRD §5의 화면 키. stage가 "expansion"인 화면은 MVP에서 예정 표시만 한다.
const SCREENS = [
  { key: "today", title: "오늘", group: "user", desc: "우선 확인할 자료와 이유를 모아 보여줍니다." },
  { key: "inbox", title: "받은 자료", group: "user", desc: "URL과 텍스트 자료를 접수하고 확인 범위를 봅니다." },
  { key: "knowledge", title: "지식 보관함", group: "user", desc: "보관한 자료를 찾고, 활동 기록과 휴지통을 관리합니다." },
  { key: "trends", title: "AI 동향", group: "user", desc: "내가 제공한 자료 중 대응이 필요한 변화와 학습 자료를 구분합니다." },
  { key: "ask", title: "비서에게 묻기", group: "user", desc: "보관한 자료와 숫자 요약을 근거로 질문에 답합니다." },
  { key: "conversations", title: "대화 기록", group: "user", desc: "이전 대화를 다시 열고 근거 자료의 현재 상태를 봅니다." },
  { key: "review", title: "검토·승인", group: "admin", desc: "자료의 보관·연결·휴지통 이동을 검토하고 승인합니다." },
  { key: "screenshots", title: "스크린샷 정리", group: "admin", stage: "expansion", desc: "PC의 작업용 스크린샷을 묶어 정리합니다." },
  { key: "downloads", title: "Downloads 정리", group: "admin", stage: "expansion", desc: "다운로드한 파일의 이름과 보관 위치를 제안합니다." },
  { key: "settings", title: "프로젝트·설정", group: "admin", desc: "관심 분야·프로젝트와 자료 모드를 관리합니다." },
];
const BY_KEY = Object.fromEntries(SCREENS.map((s) => [s.key, s]));
const MODE_KEY = "ai-secretary.mode";

const $ = (id) => document.getElementById(id);
const state = { mode: loadMode(), user: null, loginMessage: "" };

// ── 작은 DOM 도우미 ────────────────────────────────────────────────
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (name === "text") node.textContent = value;
    else node.setAttribute(name, value);
  }
  for (const child of children) if (child) node.append(child);
  return node;
}

// ── 자료 모드: 요청마다 X-Data-Mode로 보내며, 마지막 선택은 이 브라우저에만 기억한다 ──
// (서버에는 저장하지 않는다. docs/decisions.md·features/settings/service.py 참고)
function loadMode() {
  try {
    return localStorage.getItem(MODE_KEY) === "sample" ? "sample" : "personal";
  } catch {
    return "personal";
  }
}

function setMode(mode) {
  state.mode = mode === "sample" ? "sample" : "personal";
  try {
    localStorage.setItem(MODE_KEY, state.mode);
  } catch {
    /* 저장할 수 없어도 이번 세션 동안은 동작한다 */
  }
  syncModeUi();
  renderScreen();
  checkServer();
}

function syncModeUi() {
  $("mode-select").value = state.mode;
  $("sample-badge").hidden = state.mode !== "sample";
}

// ── 안내 배너 ─────────────────────────────────────────────────────
const SLOW_TEXT = "서버 연결을 기다리고 있습니다. 첫 연결은 시간이 걸릴 수 있습니다.";
let retryAction = null;
let serverCheckId = 0;

function showBanner(text, retry = null) {
  $("banner-text").textContent = text;
  retryAction = retry;
  $("banner-retry").hidden = !retry;
  $("banner").hidden = false;
}

function hideBanner() {
  $("banner").hidden = true;
  retryAction = null;
}

onSlowRequest((active) => {
  // 원인이나 완료 시간을 단정하지 않는다(PRD §14).
  if (active) showBanner(SLOW_TEXT);
  else if ($("banner-text").textContent === SLOW_TEXT) hideBanner();
});

// ── 서버·소유자 확인(/api/me) ──────────────────────────────────────
async function checkServer() {
  if (!state.user) return;
  const checkId = ++serverCheckId;
  const user = state.user;
  try {
    await request("/api/me", { mode: state.mode });
    if (checkId === serverCheckId && state.user === user) hideBanner();
  } catch (error) {
    if (checkId === serverCheckId && state.user === user) handleApiError(error, checkServer);
  }
}

// 모든 화면이 같은 규칙으로 오류를 안내한다.
export function handleApiError(error, retry) {
  switch (error.kind) {
    case "auth":
      endSession("로그인이 만료되었습니다. 다시 로그인하세요.");
      break;
    case "forbidden":
      endSession("이 계정은 사용할 수 없습니다. 허용된 소유자 계정으로 로그인하세요.");
      break;
    case "unavailable":
      showBanner("서버 설정 문제로 지금은 사용할 수 없습니다. 잠시 후 다시 시도하세요.", retry);
      break;
    case "network":
      showBanner("서버에 연결하지 못했습니다. 네트워크를 확인한 뒤 다시 시도하세요.", retry);
      break;
    default:
      showBanner(`요청을 처리하지 못했습니다 (${error.detail || error.message}).`, retry);
  }
}

function endSession(message) {
  state.loginMessage = message;
  signOut();
}

// ── 메뉴와 화면 ───────────────────────────────────────────────────
function buildNav() {
  const nav = $("nav");
  nav.replaceChildren();
  for (const [group, label] of [["user", "사용자 화면"], ["admin", "관리 화면"]]) {
    nav.append(el("div", { class: "nav-label", text: label }));
    for (const screen of SCREENS.filter((s) => s.group === group)) {
      nav.append(el("a", { class: "nav-item", href: `#${screen.key}`, "data-key": screen.key },
        el("span", { text: screen.title }),
        screen.stage === "expansion" ? el("small", { text: "확장 예정" }) : null));
    }
  }
}

function currentKey() {
  const key = location.hash.replace(/^#/, "");
  return Object.hasOwn(BY_KEY, key) ? key : "today";
}

let renderToken = 0;

function renderScreen() {
  const token = ++renderToken;
  const screen = BY_KEY[currentKey()];
  document.title = `${screen.title} · AI Secretary`;
  $("current-title").textContent = screen.title;
  for (const link of document.querySelectorAll(".nav-item")) {
    if (link.dataset.key === screen.key) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }

  const head = el("div", { class: "page-head" },
    el("span", { class: "eyebrow", text: state.mode === "sample" ? "표본 자료 보기" : "내 자료" }),
    el("h1", { text: screen.title }),
    el("p", { text: screen.desc }));

  const view = VIEWS[screen.key];
  if (view && state.user) {
    const container = el("div", { class: "view" });
    $("screen").replaceChildren(head, container);
    const mode = state.mode;
    // 화면을 다시 그리거나 모드를 바꾸면 이전 화면의 늦은 응답은 버린다.
    view(container, {
      mode,
      isCurrent: () => token === renderToken && state.mode === mode,
      onError: handleApiError,
    });
    closeMenu();
    return;
  }

  // 예시 숫자·가짜 카드는 넣지 않는다. 실제 데이터가 연결되기 전에는 빈 상태만 보인다.
  const body = screen.stage === "expansion"
    ? el("section", { class: "panel notice" },
        el("strong", { text: "확장 단계 예정 · PC 연결 안 됨" }),
        el("p", { text: "이 기능은 PC 연결 프로그램이 준비되는 확장 단계에서 제공됩니다. 지금은 연결된 PC가 없습니다." }))
    : el("section", { class: "panel empty" },
        el("strong", { text: "아직 표시할 내용이 없습니다" }),
        el("p", { text: "이 화면의 기능은 준비 중입니다." }));

  $("screen").replaceChildren(head, body);
  closeMenu();
}

// ── 모바일 메뉴 ───────────────────────────────────────────────────
function closeMenu() {
  $("sidebar").classList.remove("open");
  $("scrim").classList.remove("open");
  $("menu-toggle").setAttribute("aria-expanded", "false");
}

function toggleMenu() {
  const open = !$("sidebar").classList.contains("open");
  $("sidebar").classList.toggle("open", open);
  $("scrim").classList.toggle("open", open);
  $("menu-toggle").setAttribute("aria-expanded", String(open));
}

// ── 로그인 상태 전환 ──────────────────────────────────────────────
function showLogin(message) {
  $("boot").hidden = true;
  $("app-view").hidden = true;
  $("login-view").hidden = false;
  $("login-message").textContent = message;
}

function showApp(user) {
  $("boot").hidden = true;
  $("login-view").hidden = true;
  $("app-view").hidden = false;
  $("user-email").textContent = user.email || "";
  hideBanner();
  renderScreen();
}

// ── 시작 ─────────────────────────────────────────────────────────
buildNav();
syncModeUi();

$("login-btn").addEventListener("click", () => {
  $("login-message").textContent = "";
  signIn().catch((error) => {
    $("login-message").textContent = `로그인하지 못했습니다 (${error.code || error.message}).`;
  });
});
$("logout-btn").addEventListener("click", () => signOut());
$("mode-select").addEventListener("change", (event) => setMode(event.target.value));
$("menu-toggle").addEventListener("click", toggleMenu);
$("scrim").addEventListener("click", closeMenu);
$("banner-retry").addEventListener("click", () => retryAction && retryAction());
window.addEventListener("hashchange", renderScreen);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMenu();
});

onUserChanged((user) => {
  serverCheckId++;
  state.user = user;
  if (!user) {
    showLogin(state.loginMessage);
    state.loginMessage = "";
    return;
  }
  showApp(user);
  checkServer();
});
