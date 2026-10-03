import { apiFetch, onUserChanged, signIn, signOut } from "./auth.js";

const $ = (id) => document.getElementById(id);
const show = (id, text) => { $(id).textContent = text; };

onUserChanged((user) => {
  $("sign-in").disabled = Boolean(user);
  $("sign-out").disabled = !user;
  // 첫 로그인 뒤 이 UID를 서버 .env의 OWNER_UID에 넣는다.
  show("user", user ? `로그인됨\nUID: ${user.uid}\n이메일: ${user.email ?? "-"}` : "로그인하지 않음");
});

$("sign-in").addEventListener("click", () => signIn().catch((e) => show("user", `로그인 실패: ${e.code ?? e.message}`)));
$("sign-out").addEventListener("click", () => signOut());
$("call-me").addEventListener("click", async () => {
  try {
    const res = await apiFetch("/api/me", { mode: $("mode").value });
    show("result", `HTTP ${res.status}\n${await res.text()}`);
  } catch (e) {
    show("result", `요청 실패: ${e.message} (서버 실행·ALLOWED_ORIGINS 확인)`);
  }
});
