import { test } from "node:test";
import assert from "node:assert/strict";

import { loadAllLaterPages } from "../js/later-list.js";

test("21번째 페이지의 기한 지난 자료도 목록 맨 위에 표시한다", async () => {
  const recent = Array.from({ length: 20 }, (_, i) => ({ id: `recent-${i}`, revisit_due: false, revisit_on: "2099-01-01" }));
  const due = { id: "old-due", revisit_due: true, revisit_on: "2020-01-01" };
  const cursors = [];
  const items = await loadAllLaterPages(async (cursor) => {
    cursors.push(cursor);
    return cursor === null ? { items: recent, next_cursor: "second" } : { items: [due], next_cursor: null };
  });

  assert.deepEqual(cursors, [null, "second"]);
  assert.equal(items.length, 21);
  assert.equal(items[0].id, "old-due");
});
