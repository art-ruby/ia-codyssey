// Firebase Google 로그인과 인증된 API 호출. T02.03의 웹 화면도 이 모듈을 쓴다.
// 앱 코드는 ID 토큰을 직접 저장하지 않는다. 로그인 상태는 Firebase 기본값(브라우저 로컬 유지)을 따르며,
// 새로고침·페이지 이동 후에도 로그인이 유지된다. 공용 PC 등에서는 로그아웃해야 상태가 지워진다.
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
// mode는 기본값 없이 반드시 받는다. 누락 시 개인 자료로 조회되는 사고를 막기 위해서다.
export async function apiFetch(path, { mode, idempotencyKey, ...init } = {}) {
  if (mode !== "personal" && mode !== "sample") {
    throw new Error(`apiFetch: mode는 "personal" 또는 "sample"이어야 합니다 (받은 값: ${mode})`);
  }
  const headers = new Headers(init.headers || {});
  headers.set("X-Data-Mode", mode);
  if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);
  if (auth.currentUser) {
    headers.set("Authorization", `Bearer ${await auth.currentUser.getIdToken()}`);
  }
  return fetch(new URL(path, config.apiBaseUrl), { ...init, headers });
}
