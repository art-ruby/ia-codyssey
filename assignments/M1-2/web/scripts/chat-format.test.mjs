import { test } from "node:test";
import assert from "node:assert/strict";

import {
  basisText, chatFailureText, relatedText, sourceStatus, summaryCondition, summaryHeading, toTurns,
} from "../js/chat-format.js";

test("URL만 있는 자료는 본문 미확인으로 표시한다", () => {
  assert.equal(basisText("link_only"), "링크만 · 본문 미확인");
  assert.equal(basisText("content"), "본문 확인");
});

test("AI 제안 관계는 사용자 확정 관계와 다른 문구다", () => {
  assert.equal(relatedText("user_confirmed"), "내가 연결한 관련 자료");
  assert.match(relatedText("ai_suggested"), /확정 아님/);
});

test("출처의 현재 상태: 삭제·휴지통은 경고색, 방금 받은 답은 상태 없음", () => {
  assert.deepEqual(sourceStatus("deleted"), ["삭제된 자료", "amber"]);
  assert.deepEqual(sourceStatus("trashed"), ["지금은 휴지통", "amber"]);
  assert.deepEqual(sourceStatus("available"), ["현재 보관 중", "mint"]);
  assert.equal(sourceStatus(undefined), null);
});

test("기본 요약과 질문 조건 요약을 출처·지표·기간으로 구분한다", () => {
  const base = { role: "default", source: "actual", metric_type: "kept_count", period: null };
  const asked = { role: "question", source: "manual", metric_type: "kept_count", period: { start: "2026-09-01", end: "2026-09-30" } };
  assert.equal(summaryHeading(base), "기본 요약");
  assert.equal(summaryHeading(asked), "질문 조건 요약");
  assert.equal(summaryCondition(base), "출처 실제 값 · 지표 보관 건수 · 기간 없음");
  assert.equal(summaryCondition(asked), "출처 사용자 입력 기록 · 지표 보관 건수 · 2026-09-01 ~ 2026-09-30");
  assert.match(summaryCondition({ ...asked, source: "sample" }), /가상 기록/);
});

test("실패 원인별 문구: 검색 실패는 '자료 없음'이 아니다", () => {
  assert.match(chatFailureText({ kind: "unavailable", status: 503, data: { reason: "search_failed" } }), /없다는 뜻이 아닙니다/);
  assert.match(chatFailureText({ kind: "http", status: 502, data: { reason: "provider_failed", kind: "timeout" } }), /timeout/);
  assert.match(chatFailureText({ kind: "http", status: 429, data: { reason: "quota_exceeded" } }), /한도/);
  assert.equal(chatFailureText({ kind: "http", status: 422, detail: "질문은 2000자까지", data: {} }), "질문은 2000자까지");
  assert.equal(chatFailureText({ kind: "network", status: 0, data: null }), null);
});

test("대화 메시지를 질문·답변 묶음으로", () => {
  const turns = toTurns([
    { role: "user", content: "q1" }, { role: "assistant", content: "a1" }, { role: "user", content: "q2" },
  ]);
  assert.deepEqual(turns.map((t) => [t.question, t.answer && t.answer.content]), [["q1", "a1"], ["q2", null]]);
});
