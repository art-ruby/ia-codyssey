# 예상 결과

## 테스트 1

```json
{
  "status": "success",
  "message_id": "test-rate-001",
  "newsletter_name": "어피티",
  "main_topic": "금리",
  "source_count": 1,
  "issue_level": "일반",
  "hot_issue": false,
  "notification_sent": false
}
```

## 테스트 2

```json
{
  "status": "success",
  "message_id": "test-rate-002",
  "newsletter_name": "순살브리핑",
  "main_topic": "금리",
  "source_count": 2,
  "issue_level": "관심",
  "hot_issue": true,
  "notification_sent": true
}
```

## 테스트 3

```json
{
  "status": "success",
  "message_id": "test-realestate-001",
  "newsletter_name": "뉴닉",
  "main_topic": "부동산",
  "source_count": 1,
  "issue_level": "일반",
  "hot_issue": false,
  "notification_sent": false
}
```

## 테스트 4

```json
{
  "status": "duplicate",
  "message_id": "test-rate-001",
  "message": "이미 처리된 메시지입니다."
}
```

## 테스트 5

```json
{
  "status": "success",
  "message_id": "test-unknown-001",
  "newsletter_name": "알수없음",
  "main_topic": "기타",
  "source_count": 1,
  "issue_level": "일반",
  "hot_issue": false,
  "notification_sent": false
}
```
