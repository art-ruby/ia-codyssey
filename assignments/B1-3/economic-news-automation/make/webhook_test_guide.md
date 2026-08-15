# Make Webhook 테스트 가이드

## 테스트 준비

1. Make 시나리오의 Custom Webhook URL을 복사한다.
2. Google Sheets 문서에 `뉴스수집`, `핫이슈`, `키워드목록`, `오류로그` 시트를 만든다.
3. `tests/test_requests.md`의 JSON을 순서대로 보낸다.

## curl 예시

```bash
curl -X POST "$MAKE_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "newsletter_name": "어피티",
    "sender": "sample1@example.com",
    "subject": "미국 기준금리 인하 가능성이 커진 이유",
    "body": "연준의 통화정책과 FOMC 전망을 다룹니다.",
    "received_date": "2026-07-14",
    "message_id": "test-rate-001"
  }'
```

## 확인 항목

- 응답 JSON의 `status`가 `success`인지 확인
- `main_topic`이 예상값과 일치하는지 확인
- Google Sheets `뉴스수집` 시트에 행이 추가됐는지 확인
- 중요 뉴스 경로에서 Discord 또는 Gmail 알림이 발송됐는지 확인
