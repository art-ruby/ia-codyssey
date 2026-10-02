import { test } from "node:test";
import assert from "node:assert/strict";

import { mergePage, scopeText, searchQuery } from "../js/search-query.js";

test("빈 조건은 보내지 않고, 커서는 같은 조건에 붙인다", () => {
  const url = searchQuery({ q: "  결제 개편 ", date_from: "2026-10-01", date_to: "", kind: "", project_id: "p1" }, "c1", 20);
  const params = new URL(url, "http://x").searchParams;
  assert.equal(params.get("q"), "결제 개편");
  assert.equal(params.get("date_from"), "2026-10-01");
  assert.equal(params.has("date_to"), false);
  assert.equal(params.has("kind"), false);
  assert.equal(params.get("project_id"), "p1");
  assert.equal(params.get("cursor"), "c1");
  assert.equal(params.get("limit"), "20");
});

test("일부만 검색했으면 범위를 분명히 알린다", () => {
  const full = { total_matches: 2, scope: { kept_scanned: 30, truncated: false, scan_limit: 1000 } };
  assert.equal(scopeText(full), "보관 자료 30건 중 2건 일치");
  const partial = { total_matches: 0, scope: { kept_scanned: 900, truncated: true, scan_limit: 1000 } };
  assert.match(scopeText(partial), /최근 접수 1000건까지만 검색했습니다/);
});

test("이어 받은 페이지는 이미 있는 자료를 다시 붙이지 않는다", () => {
  const merged = mergePage([{ id: "a" }, { id: "b" }], [{ id: "b" }, { id: "c" }]);
  assert.deepEqual(merged.map((m) => m.id), ["a", "b", "c"]);
});
