# HTTP 테스트 요청

아래 요청은 n8n 프로젝트 2 Webhook 또는 Make Custom Webhook에 그대로 전송한다.

## 테스트 1

```json
{
  "newsletter_name": "어피티",
  "sender": "sample1@example.com",
  "subject": "미국 기준금리 인하 가능성이 커진 이유",
  "body": "연준의 통화정책과 FOMC 전망을 다룹니다.",
  "received_date": "2026-07-14",
  "message_id": "test-rate-001"
}
```

## 테스트 2

```json
{
  "newsletter_name": "순살브리핑",
  "sender": "sample2@example.com",
  "subject": "연준은 왜 금리를 내릴까",
  "body": "미국 물가와 FOMC 결과가 관심을 받고 있습니다.",
  "received_date": "2026-07-14",
  "message_id": "test-rate-002"
}
```

## 테스트 3

```json
{
  "newsletter_name": "뉴닉",
  "sender": "sample3@example.com",
  "subject": "수도권 주택 공급 대책이 발표됐어요",
  "body": "정부가 아파트와 주택 공급 방안을 발표했습니다.",
  "received_date": "2026-07-14",
  "message_id": "test-realestate-001"
}
```

## 테스트 4

테스트 1과 같은 `message_id`를 다시 전송한다.

```json
{
  "newsletter_name": "어피티",
  "sender": "sample1@example.com",
  "subject": "미국 기준금리 인하 가능성이 커진 이유",
  "body": "연준의 통화정책과 FOMC 전망을 다룹니다.",
  "received_date": "2026-07-14",
  "message_id": "test-rate-001"
}
```

## 테스트 5

```json
{
  "newsletter_name": "알수없음",
  "sender": "unknown@example.com",
  "subject": "이번 주 문화 소식",
  "body": "공연과 전시 소식을 소개합니다.",
  "received_date": "2026-07-14",
  "message_id": "test-unknown-001"
}
```

## curl 템플릿

```bash
curl -X POST "$N8N_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d @request.json
```
