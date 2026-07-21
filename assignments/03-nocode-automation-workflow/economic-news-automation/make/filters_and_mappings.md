# Make 필터와 매핑 상세

## 입력값 검증

필수 필드:

- `newsletter_name`
- `sender`
- `subject`
- `received_date`
- `message_id`

필수 필드 누락 시 Webhook Response:

```json
{
  "status": "error",
  "error_type": "VALIDATION_ERROR",
  "missing_fields": ["subject", "message_id"]
}
```

## Google Sheets Add a Row 매핑

| Sheets 컬럼 | Make 매핑 |
|---|---|
| collected_at | `now` |
| received_date | `received_date` |
| newsletter_name | `newsletter_name` |
| newsletter_group | Router 경로별 고정값 |
| sender | `sender` |
| subject | `subject` |
| body_preview | `substring(body; 0; 200)` |
| main_topic | Set Variables 결과 |
| secondary_keywords | Set Variables 결과 |
| source_count | 프로젝트 1은 `1` |
| issue_level | 프로젝트 1은 `일반` |
| hot_issue | 프로젝트 1은 `FALSE` |
| message_id | `message_id` |
| processing_status | `SUCCESS` |
| error_message | 빈 문자열 |

## 알림 템플릿

```text
[중요 경제뉴스 감지]

뉴스레터: {{newsletter_name}}
대표 키워드: {{main_topic}}
제목: {{subject}}
수신일: {{received_date}}
```

## 오류 처리

- Google Sheets 저장 실패: 오류로그 시트에 `workflow_name`, `node_name`, `message_id`, `error_message` 저장
- 알림 발송 실패: 뉴스수집 행은 유지하고 `notification_sent=false`로 후속 점검
- 입력 검증 실패: Google Sheets 저장 없이 HTTP 400 반환
