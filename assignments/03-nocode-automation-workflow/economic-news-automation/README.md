# 경제 뉴스레터 자동화

Make와 n8n으로 같은 입력 JSON을 받아 경제 뉴스레터를 분류하고, 경제 키워드를 추출하며, Google Sheets 저장과 중요 뉴스 알림까지 처리하는 과제 산출물입니다. 프로젝트 2는 n8n 워크플로우를 확장해 여러 뉴스레터에서 같은 날짜와 같은 주제가 반복될 때 핫이슈로 판정합니다.

## 구현 범위

- HTTP Webhook 기반 Make 구현 가이드
- HTTP Webhook 기반 n8n import JSON 2종
- Gmail Trigger 전환용 n8n import JSON
- Google Sheets 테이블 설계
- 키워드 매핑 CSV와 테스트 데이터
- 중복 `message_id` 방지 로직
- 서로 다른 뉴스레터 기준 `source_count` 계산 로직
- Make vs n8n 비교 보고서
- 최종 제출 보고서와 스크린샷 가이드

## 폴더 구조

```text
economic-news-automation/
├── README.md
├── .env.example
├── n8n/
├── make/
├── sheets/
├── tests/
├── docs/
└── reports/
```

## 빠른 테스트 순서

1. `n8n/project2_hot_issue_detection.json`을 n8n에 import합니다.
2. Webhook URL을 복사합니다.
3. `tests/test_requests.md`의 요청 1, 2, 4, 5를 순서대로 전송합니다.
4. Google Sheets에는 `sheets/sheet_structure.md` 기준으로 4개 시트를 만듭니다.
5. 실제 인증값은 `.env.example`의 플레이스홀더만 참고하고 문서나 JSON에 직접 넣지 않습니다.

## 인증 정보 처리

워크플로우 JSON에는 실제 Google Sheets ID, Gmail Credential, Discord Webhook URL, API Key를 넣지 않았습니다. 모든 민감 정보는 n8n Credential 또는 Make Connection에 저장하고, 산출물에는 플레이스홀더만 남겼습니다.
