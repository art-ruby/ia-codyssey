// 활동 기록·숫자 요약 표시용 순수 함수(T06.04). 화면(activity.js·today.js)과 테스트가 함께 쓴다.
// 지표·출처 이름은 서버 요약의 label을 그대로 쓰고, 여기서는 선택지와 추세 문구만 만든다.

// 모드별로 고를 수 있는 출처(서버 허용 조합과 같다, T06.02). 첫 항목이 기본값.
export function sourceOptions(mode) {
  return mode === "sample"
    ? [["sample", "가상 기록(표본)"], ["actual", "실제 값(표본 자료에서 계산)"]]
    : [["actual", "실제 값(자료에서 계산)"], ["manual", "사용자 입력 기록"]];
}

export const METRIC_OPTIONS = [["kept_count", "보관 건수"], ["received_count", "접수 건수"]];

// 이 출처일 때 직접 고칠 수 있는 기록의 출처. 실제 값은 저장된 기록이 아니므로 null.
export function editableOrigin(mode, source) {
  if (source === "actual") return null;
  return mode === "sample" ? "sample" : "manual";
}

export function trendText(trend) {
  if (!trend) return "추세: 기록 없음";
  const avg = trend.previous_average === null ? "" : ` (최근 7일 평균 ${trend.recent_average}, 이전 7일 ${trend.previous_average})`;
  switch (trend.status) {
    case "increase": return `추세: 증가 +${trend.change_rate}%${avg}`;
    case "decrease": return `추세: 감소 ${trend.change_rate}%${avg}`;
    case "flat": return `추세: 유지 ${trend.change_rate > 0 ? "+" : ""}${trend.change_rate}%${avg}`;
    case "new": return `추세: 새 보관 발생(이전 7일 0건)${avg}`;
    case "both_zero": return "추세: 최근·이전 7일 모두 0건";
    case "insufficient": return "추세: 비교 부족(관측 14일 미만)";
    default: return `추세: ${trend.status}`;
  }
}

// "합계 35건 · 일평균 2.5 · 최소 2 · 최대 3 · 14일" / 기록이 없으면 안내
export function statsText(summary) {
  if (!summary.days) return "기록 없음(합계 0건)";
  return `합계 ${summary.total}건 · 일평균 ${summary.average} · 최소 ${summary.min} · 최대 ${summary.max} · ${summary.days}일`;
}

export function periodText(summary) {
  return summary.period ? `${summary.period.start} ~ ${summary.period.end}` : "기간 없음";
}
