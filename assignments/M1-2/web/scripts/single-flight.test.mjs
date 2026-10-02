import { test } from "node:test";
import assert from "node:assert/strict";

import { singleFlight } from "../js/single-flight.js";

test("중복 선택 중 재클릭은 새 요청을 시작하지 않고 버튼 상태를 되돌린다", async () => {
  const run = singleFlight();
  const buttons = [{ disabled: false }, { disabled: true }];
  let resolve;
  let calls = 0;
  const first = run(buttons, () => {
    calls += 1;
    return new Promise((done) => { resolve = done; });
  });

  assert.deepEqual(buttons.map((button) => button.disabled), [true, true]);
  await run(buttons, () => { calls += 1; });
  assert.equal(calls, 1);

  resolve();
  await first;
  assert.deepEqual(buttons.map((button) => button.disabled), [false, true]);

  await run(buttons, () => { calls += 1; });
  assert.equal(calls, 2);
});

test("선택 요청이 실패해도 다시 시도할 수 있다", async () => {
  const run = singleFlight();
  const button = { disabled: false };
  await assert.rejects(run([button], () => { throw new Error("network"); }), /network/);
  assert.equal(button.disabled, false);
  assert.equal(await run([button], () => "retried"), "retried");
});
