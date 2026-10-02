import { test } from "node:test";
import assert from "node:assert/strict";

import { analysisState, sendScope } from "../js/analysis.js";

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

test("전송 범위는 값이 있는 입력 필드만 센다", () => {
  assert.deepEqual(sendScope({ title: "제목", body: "본문 내용", description: "", save_reason: "이유", memo: null }),
    { labels: ["제목", "본문", "저장 이유"], chars: 9 });
});
