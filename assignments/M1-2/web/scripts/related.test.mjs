import { test } from "node:test";
import assert from "node:assert/strict";

import { evidenceText, linkItem, resultMessage } from "../js/related.js";

test("근거는 종류별로 화면에 그대로 보여준다", () => {
  assert.equal(evidenceText([{ label: "같은 프로젝트", values: ["결제 개편"] }, { label: "함께 나오는 단어", values: ["정산", "oauth"] }]),
    "같은 프로젝트: 결제 개편 · 함께 나오는 단어: 정산, oauth");
  assert.equal(evidenceText([]), "");
});

test("판단은 두 자료의 ID·버전을 담아 승인 API로 보낸다", () => {
  assert.deepEqual(linkItem({ id: "a", version: 3 }, { id: "b", version: 7 }, "unrelated"),
    { material_id: "a", expected_version: 3, action: "link", link: { target_id: "b", target_version: 7, decision: "unrelated" } });
});

test("결과별 안내 문구", () => {
  assert.match(resultMessage({ status: "linked" }), /연결했습니다/);
  assert.match(resultMessage({ status: "marked_unrelated" }), /다시 제안하지 않습니다/);
  assert.match(resultMessage({ status: "conflict" }), /다시 불러왔습니다/);
  assert.match(resultMessage({ status: "invalid", reason: "same_url" }), /중복 확인/);
});
