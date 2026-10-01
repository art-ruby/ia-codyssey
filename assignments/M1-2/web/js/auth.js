// Firebase Google 로그인과 인증된 API 호출. T02.03의 웹 화면도 이 모듈을 쓴다.
// ID 토큰은 메모리에서만 다루고 localStorage 등에 직접 저장하지 않는다.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const config = window.AI_SECRETARY_CONFIG;
if (!config || !config.firebase || !config.firebase.apiKey) {
  throw new Error("web/js/config.js가 없거나 Firebase 공개 설정이 비어 있습니다 (config.example.js 참고)");
}

const auth = getAuth(initializeApp(config.firebase));

export function onUserChanged(callback) {
  return onAuthStateChanged(auth, callback);
}

export function signIn() {
  return signInWithPopup(auth, new GoogleAuthProvider());
}

export function signOut() {
  return firebaseSignOut(auth);
}

// 로그인하지 않았으면 Authorization 헤더 없이 보낸다(서버가 401로 응답).
export async function apiFetch(path, { mode = "personal", idempotencyKey, ...init } = {}) {
  const headers = new Headers(init.headers || {});
  headers.set("X-Data-Mode", mode);
  if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);
  if (auth.currentUser) {
    headers.set("Authorization", `Bearer ${await auth.currentUser.getIdToken()}`);
  }
  return fetch(new URL(path, config.apiBaseUrl), { ...init, headers });
}
