import { test } from "node:test";
import assert from "node:assert/strict";

import { editableOrigin, periodText, sourceOptions, statsText, trendText } from "../js/activity-format.js";

test("모드별 출처 선택지는 서버 허용 조합과 같고 첫 항목이 기본값이다", () => {
  assert.deepEqual(sourceOptions("personal").map(([v]) => v), ["actual", "manual"]);
  assert.deepEqual(sourceOptions("sample").map(([v]) => v), ["sample", "actual"]);
});

test("실제 값은 고칠 수 있는 기록이 아니다", () => {
  assert.equal(editableOrigin("personal", "actual"), null);
  assert.equal(editableOrigin("personal", "manual"), "manual");
  assert.equal(editableOrigin("sample", "sample"), "sample");
});

test("추세 문구: 증가·감소·유지·새 보관·양쪽 0·비교 부족", () => {
  const base = { recent_average: 3, previous_average: 2 };
  assert.match(trendText({ ...base, status: "increase", change_rate: 50 }), /증가 \+50%/);
  assert.match(trendText({ ...base, status: "decrease", change_rate: -12.5 }), /감소 -12.5%/);
  assert.match(trendText({ ...base, status: "flat", change_rate: 4.3 }), /유지 \+4.3%/);
  assert.match(trendText({ recent_average: 2, previous_average: 0, status: "new", change_rate: null }), /새 보관 발생/);
  assert.match(trendText({ recent_average: 0, previous_average: 0, status: "both_zero" }), /모두 0건/);
  assert.match(trendText({ recent_average: null, previous_average: null, status: "insufficient" }), /비교 부족/);
  assert.equal(trendText(null), "추세: 기록 없음");
});

test("통계 문구와 기록 없음", () => {
  assert.equal(statsText({ days: 14, total: 35, average: 2.5, min: 2, max: 3 }), "합계 35건 · 일평균 2.5 · 최소 2 · 최대 3 · 14일");
  assert.equal(statsText({ days: 0, total: 0 }), "기록 없음(합계 0건)");
  assert.equal(periodText({ period: null }), "기간 없음");
});
