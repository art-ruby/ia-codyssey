import { test } from "node:test";
import assert from "node:assert/strict";

import { analysisState, sendScope, usageLine } from "../js/analysis.js";

const base = { lifecycle: "active", ai_excluded: false };

test("분석 시작은 내용이 있는 활성 자료에서만 보인다", () => {
  assert.equal(analysisState({ ...base, analysis_status: "awaiting_start" }).action, "start");
  assert.equal(analysisState({ ...base, analysis_status: "link_only" }).action, null);
  assert.equal(analysisState({ ...base, analysis_status: "awaiting_start", ai_excluded: true }).action, null);
  assert.equal(analysisState({ ...base, analysis_status: "awaiting_start", lifecycle: "trash" }).action, null);
});

test("분석 중에는 조회만 하고, 기한이 지나면 확인 필요와 재시도를 보인다", () => {
  const running = analysisState({ ...base, analysis_status: "analyzing", analysis_stale: false });
  assert.equal(running.polling, true);
  assert.equal(running.action, null);
  const stale = analysisState({ ...base, analysis_status: "analyzing", analysis_stale: true });
  assert.equal(stale.label, "결과 확인 필요");
  assert.equal(stale.action, "retry");
  assert.equal(stale.polling, undefined);
});

test("실패는 오류 종류를 알리고 사용자가 재시도한다", () => {
  const failed = analysisState({ ...base, analysis_status: "failed", analysis_error: "ungrounded_output" });
  assert.equal(failed.action, "retry");
  assert.match(failed.note, /자료 내용과 맞지 않아/);
});

test("완료 후 내용을 고치면 이전 결과를 보이되 다시 분석을 권한다", () => {
  assert.equal(analysisState({ ...base, analysis_status: "done" }).action, null);
  const outdated = analysisState({ ...base, analysis_status: "done", analysis_outdated: true });
  assert.equal(outdated.action, "reanalyze");
  assert.equal(outdated.result, true);
});

test("분석 중 내용 변경으로 버린 결과를 알린다", () => {
  assert.match(analysisState({ ...base, analysis_status: "awaiting_start", analysis_error: "input_changed" }).note,
    /내용이 바뀌어/);
});

test("분석 중 제외를 켜서 버린 결과는 제외를 끈 뒤에 사유를 알린다", () => {
  const m = { ...base, analysis_status: "awaiting_start", analysis_error: "ai_excluded" };
  assert.equal(analysisState({ ...m, ai_excluded: true }).label, "AI 분석 제외");
  assert.match(analysisState(m).note, /AI 분석 제외를 켜서/);
});

test("전송 범위는 값이 있는 입력 필드만 센다", () => {
  assert.deepEqual(sendScope({ title: "제목", body: "본문 내용", description: "", save_reason: "이유", memo: null }),
    { labels: ["제목", "본문", "저장 이유"], chars: 9 });
});

test("한도 대기는 실패가 아니며 사용자가 다시 시작한다", () => {
  const waiting = analysisState({ ...base, analysis_status: "quota_waiting" });
  assert.equal(waiting.label, "호출 한도 대기");
  assert.equal(waiting.action, "resume");
  assert.match(waiting.note, /저절로 시작하지 않으니/);
  assert.match(analysisState({ ...base, analysis_status: "quota_waiting", analysis_error: "rate_limited" }).note, /429/);
});

test("사용량 줄은 요청 수와 자료 건수를 구분하고 금액을 만들지 않는다", () => {
  const line = usageLine({ used: 37, limit: 50, remaining: 13, pending_count: 42, pending_capped: false });
  assert.equal(line, "오늘 AI 요청 37/50 · 남은 요청 13 · 한도 대기 자료 42건 · 비용: 구독 경로, 금액 미확인");
  assert.match(usageLine({ used: 0, limit: 50, remaining: 50, pending_count: 100, pending_capped: true }), /100건 이상/);
});
