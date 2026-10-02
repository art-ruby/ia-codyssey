import { test } from "node:test";
import assert from "node:assert/strict";

import { actionText, importanceText, stateTags, todayPicks, trendGroups } from "../js/priority.js";

const m = (id, final_importance, needs_action = null, extra = {}) =>
  ({ id, final_importance, needs_action, importance_source: "ai", review_status: "unreviewed", ...extra });

test("최종 중요도는 출처와 함께, 없으면 판단 보류로 표시한다", () => {
  assert.equal(importanceText(m("a", "high")), "높음 · AI 제안");
  assert.equal(importanceText(m("a", "low", null, { importance_source: "user" })), "낮음 · 내가 정함");
  assert.equal(importanceText(m("a", null)), "판단 보류");
});

test("대응 필요·학습 자료·미확인을 구분한다", () => {
  assert.deepEqual([true, false, null].map((v) => actionText(m("a", "high", v))), ["대응 필요", "학습 자료", "대응 여부 미확인"]);
});

test("미승인 자료에는 검토 대기를 붙인다", () => {
  assert.deepEqual(stateTags(m("a", "high")), [["검토 대기", "amber"]]);
  assert.deepEqual(stateTags(m("a", "high", null, { review_status: "approved", ai_excluded: true })),
    [["보관됨", "mint"], ["AI 분석 제외", ""]]);
});

test("오늘은 서버 순서에서 높음·보통만 최대 3건", () => {
  const items = [m("1", "high"), m("2", "high"), m("3", "medium"), m("4", "medium"), m("5", "low")];
  assert.deepEqual(todayPicks(items).map((x) => x.id), ["1", "2", "3"]);
  assert.deepEqual(todayPicks([m("1", "low")]), []);
  assert.deepEqual(todayPicks([]), []);
});

test("AI 동향은 서버 순서를 유지한 채 대응 필요와 나머지로 나눈다", () => {
  const items = [m("1", "high", true), m("2", "high", false), m("3", "medium", true), m("4", "low", null)];
  const { action, learning } = trendGroups(items);
  assert.deepEqual(action.map((x) => x.id), ["1", "3"]);
  assert.deepEqual(learning.map((x) => x.id), ["2", "4"]);
});
