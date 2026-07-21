# 프로젝트 2 핫이슈 감지 설계 보고서

## 목표

같은 경제 이슈가 서로 다른 뉴스레터에서 반복 등장하면 핫이슈로 분류한다. 동일 뉴스레터의 반복 발송은 여러 번 들어와도 출처 수 1개로 계산한다.

## 처리 흐름

```text
HTTP Webhook
-> 필수값 검증
-> message_id 중복 확인
-> 뉴스레터 분류
-> 경제 키워드 분류
-> Google Sheets 기존 데이터 검색
-> 같은 날짜와 같은 main_topic의 서로 다른 뉴스레터 수 계산
-> 뉴스수집 저장
-> 핫이슈 저장 또는 알림
-> HTTP 응답
```

## 중복 방지

`message_id`를 고유값으로 사용한다. 기존 행에 같은 `message_id`가 있으면 `뉴스수집`과 `핫이슈` 시트에 어떤 행도 추가하지 않는다.

## source_count 계산

조건:

- `received_date`가 같아야 한다.
- `main_topic`이 같아야 한다.
- `processing_status`가 `DUPLICATE`가 아니어야 한다.
- 서로 다른 `newsletter_name`만 Set으로 계산한다.

## 등급 기준

| source_count | issue_level | hot_issue |
|---:|---|---|
| 1 | 일반 | FALSE |
| 2 | 관심 | TRUE |
| 3 이상 | 핵심 | TRUE |

## 핫이슈 알림 문구

```text
[오늘의 경제 핫이슈]

대표 이슈: {{main_topic}}
등급: {{issue_level}}
언급 뉴스레터 수: {{source_count}}
언급 뉴스레터: {{newsletters}}

관련 제목:
{{related_subjects}}
```

## 향후 개선

- Google Sheets lookup 대신 데이터베이스 사용
- 주제 유사도 기반 중복 이슈 병합
- 제목 임베딩 또는 AI 분류 도입
- 알림 중복 발송 방지용 `hot_issue_key` 추가
