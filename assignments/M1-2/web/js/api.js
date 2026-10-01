// 공통 API 요청: 오류 분류·느린 응답 안내·중복 요청 키.
// 로그인 자체는 auth.js가 맡고, 여기서는 그 위에서 요청 결과를 화면이 다루기 쉬운 형태로 바꾼다.
import { apiFetch } from "./auth.js";

const SLOW_AFTER_MS = 3000;
const GIVE_UP_AFTER_MS = 90000; // 무료 서버의 첫 연결은 오래 걸릴 수 있다.

// kind: auth(401) | forbidden(403) | unavailable(503) | network(연결 실패·시간 초과) | http(그 외)
export class ApiError extends Error {
  constructor(kind, status, detail, retry) {
    super(detail || kind);
    this.kind = kind;
    this.status = status;
    this.detail = detail;
    this.retry = retry; // 같은 요청을 같은 Idempotency-Key로 다시 보내는 함수
  }
}

const listeners = { slow: new Set() };
let slowRequests = 0;

// 느린 응답 안내: callback(true)는 대기 시작, callback(false)는 끝.
export function onSlowRequest(callback) {
  listeners.slow.add(callback);
  return () => listeners.slow.delete(callback);
}

function emitSlow(active) {
  slowRequests += active ? 1 : -1;
  for (const callback of listeners.slow) callback(slowRequests > 0);
}

function classify(status) {
  if (status === 401) return "auth";
  if (status === 403) return "forbidden";
  if (status === 503) return "unavailable";
  return "http";
}

// mode는 필수다(auth.js와 같은 규칙). 변경 요청에는 Idempotency-Key를 자동으로 붙이고,
// 실패하면 error.retry()로 같은 키를 다시 보낸다. 서버는 같은 키의 작업을 한 번만 실행한다.
export function request(path, { mode, method = "GET", body } = {}) {
  if (mode !== "personal" && mode !== "sample") {
    // 연결 오류로 잘못 분류되지 않게 요청 전에 바로 실패시킨다.
    throw new Error(`request: mode는 "personal" 또는 "sample"이어야 합니다 (받은 값: ${mode})`);
  }
  const upper = method.toUpperCase();
  const idempotencyKey = upper === "GET" ? undefined : crypto.randomUUID();

  async function send() {
    const controller = new AbortController();
    let isSlow = false;
    const slowTimer = setTimeout(() => {
      isSlow = true;
      emitSlow(true);
    }, SLOW_AFTER_MS);
    const abortTimer = setTimeout(() => controller.abort(), GIVE_UP_AFTER_MS);
    let response;
    let text;
    try {
      response = await apiFetch(path, {
        mode,
        idempotencyKey,
        method: upper,
        signal: controller.signal,
        headers: body === undefined ? {} : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      text = await response.text();
    } catch {
      const detail = response ? "응답을 받는 중 연결이 끊겼습니다" : "서버에 연결하지 못했습니다";
      throw new ApiError("network", 0, detail, send);
    } finally {
      clearTimeout(slowTimer);
      clearTimeout(abortTimer);
      if (isSlow) emitSlow(false);
    }
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = null;
    }
    if (!response.ok) {
      const detail = data && typeof data.detail === "string" ? data.detail : `HTTP ${response.status}`;
      throw new ApiError(classify(response.status), response.status, detail, send);
    }
    return data;
  }

  return send();
}
