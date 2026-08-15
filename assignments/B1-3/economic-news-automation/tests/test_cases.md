# 테스트 케이스

| ID | 목적 | 입력 | 확인 항목 |
|---|---|---|---|
| TC-01 | 금리 단일 뉴스 처리 | 테스트 1 | `main_topic=금리`, `source_count=1`, `hot_issue=false` |
| TC-02 | 같은 날짜/같은 주제 반복 감지 | 테스트 2 | `main_topic=금리`, `source_count=2`, `issue_level=관심`, `hot_issue=true` |
| TC-03 | 다른 주제 일반 처리 | 테스트 3 | `main_topic=부동산`, `source_count=1`, `hot_issue=false` |
| TC-04 | 중복 메시지 차단 | 테스트 4 | 신규 행 없음, `status=duplicate` |
| TC-05 | 미분류/기타 처리 | 테스트 5 | `newsletter_group=미분류`, `main_topic=기타`, `hot_issue=false` |
| TC-06 | 필수값 누락 오류 | `subject`, `message_id` 제거 | `status=error`, `error_type=VALIDATION_ERROR` |

## 분기 커버리지

- 경제전문: 테스트 1, 2
- 종합시사: 테스트 3
- 미분류: 테스트 5
- 중요 뉴스: 테스트 1, 2, 3
- 중요 뉴스 아님: 테스트 5
- 중복: 테스트 4
- 입력 오류: 테스트 6
