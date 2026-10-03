// 새 소식 화면의 순수 함수(브라우저 DOM 없이 Node 테스트한다).
const KIND_LABELS = { official: "공식", community: "커뮤니티", custom: "직접 추가" };
const DATE = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium" });

// 외부 피드의 링크는 http·https만 연다. 그 밖(javascript: 등)은 null.
export function safeLink(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}

export function kindLabel(kind) {
  return KIND_LABELS[kind] || "";
}

export function relativeTime(iso, now) {
  const time = Date.parse(iso || "");
  if (Number.isNaN(time)) return "";
  const seconds = Math.max(0, Math.round((now.getTime() - time) / 1000));
  if (seconds < 60) return "방금 전";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}일 전`;
  return DATE.format(new Date(time));
}

export function failureText(failures) {
  if (!failures?.length) return "";
  const detail = failures.map((f) => `${f.source_name}: ${f.error}`).join(" / ");
  return `${failures.length}곳을 읽지 못했습니다 (${detail})`;
}
