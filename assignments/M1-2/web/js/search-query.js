// 보관함 검색 요청·범위 문구(T05.01). 화면(knowledge.js)과 테스트가 함께 쓰는 순수 함수만 둔다.

export const KIND_OPTIONS = [["", "전체 종류"], ["article", "글"], ["document", "문서"], ["note", "메모"],
  ["reference", "참고 자료"], ["tool", "도구"], ["other", "기타"]];
export const SOURCE_OPTIONS = [["", "링크·텍스트 모두"], ["url", "링크"], ["text", "텍스트"]];
export const FIELD_LABELS = { title: "제목", description: "설명", body: "본문", save_reason: "저장 이유", memo: "메모", url: "URL" };

// 검색 조건 → 쿼리 문자열. 빈 값은 보내지 않는다. 커서는 같은 조건에서만 이어 쓴다.
export function searchQuery(conditions, cursor = null, limit = 20) {
  const params = new URLSearchParams();
  for (const [name, value] of Object.entries(conditions)) {
    const text = (value || "").trim();
    if (text) params.set(name, text);
  }
  params.set("limit", String(limit));
  if (cursor) params.set("cursor", cursor);
  return `/api/materials/search?${params.toString()}`;
}

// 실제로 검색한 범위. 한도 때문에 일부만 검색했으면 분명히 알린다(검색 결과 0건과 구분).
export function scopeText(page) {
  const head = `보관 자료 ${page.scope.kept_scanned}건 중 ${page.total_matches}건 일치`;
  return page.scope.truncated
    ? `${head} · 최근 접수 ${page.scope.scan_limit}건까지만 검색했습니다. 더 오래된 자료는 결과에 없을 수 있습니다.`
    : head;
}

// 이어 받은 페이지를 붙인다. 같은 자료가 다시 와도 한 번만 남긴다(중복 요청·페이지 사이 변경 대비).
export function mergePage(items, pageItems) {
  const seen = new Set(items.map((m) => m.id));
  return [...items, ...pageItems.filter((m) => !seen.has(m.id))];
}
