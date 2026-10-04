import { test } from "node:test";
import assert from "node:assert/strict";

import {
  editableOrigin, periodText, sourceOptions, statsText, summaryCsv, summaryFilename, trendText,
} from "../js/activity-format.js";

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

test("요약 CSV는 메타 정보와 일별 값을 내려받을 수 있는 형식으로 만든다", () => {
  const summary = {
    label: "현재 보관 자료 수", mode: "personal", source: "actual", metric_type: "kept_count",
    period: { start: "2026-10-01", end: "2026-10-02" },
    days: 2, total: 3, average: 1.5, min: 1, max: 2,
    trend: { status: "increase", recent_average: 2, previous_average: 1, change_rate: 100 },
    daily: [{ date: "2026-10-01", value: 1 }, { date: "2026-10-02", value: 2 }],
  };
  assert.equal(summaryFilename(summary), "ai-secretary-personal-actual-kept_count-2026-10-01-2026-10-02.csv");
  assert.equal(summaryCsv(summary), [
    "label,현재 보관 자료 수",
    "mode,personal",
    "source,actual",
    "metric_type,kept_count",
    "period_start,2026-10-01",
    "period_end,2026-10-02",
    "days,2",
    "total,3",
    "average,1.5",
    "min,1",
    "max,2",
    "trend_status,increase",
    "trend_recent_average,2",
    "trend_previous_average,1",
    "trend_change_rate,100",
    "",
    "date,value",
    "2026-10-01,1",
    "2026-10-02,2",
    "",
  ].join("\r\n"));
});

test("요약 CSV는 쉼표와 따옴표를 안전하게 이스케이프한다", () => {
  const csv = summaryCsv({ label: '보관, "중요"', daily: [{ date: "2026-10-01", value: 1 }] });
  assert.match(csv, /^label,"보관, ""중요"""/);
});
