// 나중에 볼 자료는 서버에서 접수 최신순으로 페이지를 받는다. 모든 페이지를 합친 뒤
// 다시 볼 날짜가 지난 자료를 먼저 표시한다(한 페이지 안에서만 정렬하면 오래된 후보가 숨는다).
export function sortLater(items) {
  return [...items].sort((a, b) => (Number(b.revisit_due) - Number(a.revisit_due))
    || (a.revisit_on || "9999-12-31").localeCompare(b.revisit_on || "9999-12-31"));
}

export async function loadAllLaterPages(fetchPage) {
  const items = [];
  const ids = new Set();
  const cursors = new Set();
  let cursor = null;
  do {
    const page = await fetchPage(cursor);
    for (const item of page.items) {
      if (!ids.has(item.id)) {
        ids.add(item.id);
        items.push(item);
      }
    }
    cursor = page.next_cursor;
    if (cursor && cursors.has(cursor)) throw new Error("나중에 보기 페이지 커서가 반복됩니다");
    if (cursor) cursors.add(cursor);
  } while (cursor);
  return sortLater(items);
}
