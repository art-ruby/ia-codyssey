import { test } from "node:test";
import assert from "node:assert/strict";

import { splitBatches, processBatches } from "../js/review-batches.js";

test("51건을 50건과 1건으로 순서대로 나눈다", () => {
  const items = Array.from({ length: 51 }, (_, index) => index);
  const batches = splitBatches(items);
  assert.deepEqual(batches.map((batch) => batch.length), [50, 1]);
  assert.deepEqual(batches.flat(), items);
});

test("중간 묶음 실패 후 다음 묶음을 멈추고 같은 요청으로 재개한다", async () => {
  const batches = splitBatches(Array.from({ length: 101 }, (_, index) => index));
  const attempted = [];
  const applied = [];
  const failure = Object.assign(new Error("network"), { retry: async () => "retried" });

  const send = async (_batch, index) => {
    attempted.push(index);
    if (index === 1) throw failure;
    return `sent-${index}`;
  };
  const onResult = async (result, _batch, index) => applied.push([index, result]);

  const stopped = await processBatches(batches, send, onResult);
  assert.equal(stopped.error, failure);
  assert.equal(stopped.nextIndex, 1);
  assert.deepEqual(attempted, [0, 1]);
  assert.deepEqual(applied, [[0, "sent-0"]]);

  const resumed = await processBatches(batches, send, onResult, {
    startAt: stopped.nextIndex,
    retryFirst: failure.retry,
  });
  assert.equal(resumed.error, null);
  assert.deepEqual(attempted, [0, 1, 2]);
  assert.deepEqual(applied, [[0, "sent-0"], [1, "retried"], [2, "sent-2"]]);
});
