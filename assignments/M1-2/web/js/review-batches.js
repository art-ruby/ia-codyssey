// 검토 API의 한 요청 상한과 같은 크기로 나누고, 응답을 받은 묶음만 적용한다.
export const REVIEW_BATCH_LIMIT = 50;

export function splitBatches(items) {
  const batches = [];
  for (let offset = 0; offset < items.length; offset += REVIEW_BATCH_LIMIT) {
    batches.push(items.slice(offset, offset + REVIEW_BATCH_LIMIT));
  }
  return batches;
}

export async function processBatches(batches, send, onResult, { startAt = 0, retryFirst = null } = {}) {
  for (let index = startAt; index < batches.length; index += 1) {
    let result;
    try {
      result = await (index === startAt && retryFirst ? retryFirst() : send(batches[index], index));
    } catch (error) {
      return { error, nextIndex: index };
    }
    await onResult(result, batches[index], index);
  }
  return { error: null, nextIndex: batches.length };
}
