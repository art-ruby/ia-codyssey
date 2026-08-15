# Gmail Trigger 전환 가이드

HTTP 기반 프로젝트 2가 정상 동작한 뒤 n8n 입력부를 Gmail Trigger로 전환한다.

## 전환 원칙

Webhook 이후 로직은 그대로 유지하고, Gmail Trigger의 출력만 공통 입력 JSON으로 변환한다.

## 공통 JSON 변환

```json
{
  "newsletter_name": "감지된 뉴스레터명",
  "sender": "Gmail 발신자",
  "subject": "Gmail 제목",
  "body": "정리된 메일 본문",
  "received_date": "Gmail 수신 날짜",
  "message_id": "Gmail 메시지 ID"
}
```

## 뉴스레터명 감지 기준

| 조건 | newsletter_name |
|---|---|
| 발신자 또는 제목에 `nugget` 포함 | 너겟레터 |
| 발신자 또는 제목에 `soonsal` 포함 | 순살브리핑 |
| 발신자 또는 제목에 `newneek` 포함 | 뉴닉 |
| 발신자 또는 제목에 `daily-byte` 포함 | 데일리바이트 |
| 발신자 또는 제목에 `uppity` 포함 | 어피티 |
| 발신자 또는 제목에 `mk.co.kr` 또는 `dig` 포함 | 디그 |

## 제공 파일

`n8n/gmail_trigger_version.json`은 Gmail Trigger -> Normalize Gmail Data -> Project 2 HTTP Workflow 호출 구조다. 실제 운영에서는 HTTP 호출 대신 Project 2의 내부 노드들과 직접 연결해도 된다.
