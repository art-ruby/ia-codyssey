import { test } from "node:test";
import assert from "node:assert/strict";

import { CHAT_NOTICE, DELETE_SCOPE, deletePath, trashItem, trashStateText } from "../js/trash.js";

test("휴지통 이동은 승인 API의 trash 항목이다", () => {
  assert.deepEqual(trashItem({ id: "a", version: 3 }), { material_id: "a", expected_version: 3, action: "trash" });
});

test("영구 삭제는 버전과 별도 확인 값을 함께 보낸다", () => {
  assert.equal(deletePath({ id: "a b", version: 4 }), "/api/trash/a%20b?expected_version=4&confirm=permanent");
});

test("상태 문구: 보관했던 자료·미승인·삭제 일부 실패", () => {
  assert.match(trashStateText({ lifecycle: "trash", review_status: "approved" }), /보관했던/);
  assert.match(trashStateText({ lifecycle: "trash", review_status: "unreviewed" }), /복원해도 미승인/);
  assert.match(trashStateText({ lifecycle: "deleting", deletion_failed_step: "url_index" }), /같은 URL 예약.*다시 시도/);
});

test("확인 단계는 지워지는 범위와 대화 인용문 안내를 담는다", () => {
  assert.ok(DELETE_SCOPE.some((t) => t.includes("접수 기록")));
  assert.match(CHAT_NOTICE, /이전 대화에 인용된 문장/);
});
