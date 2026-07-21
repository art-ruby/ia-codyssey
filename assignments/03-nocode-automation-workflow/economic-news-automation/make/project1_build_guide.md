# 프로젝트 1 Make 구현 가이드

## 목표

HTTP Webhook으로 뉴스레터 JSON을 받고, 뉴스레터 그룹과 경제 키워드를 분류한 뒤 Google Sheets에 저장하고 중요 뉴스일 때 알림을 보낸다.

## 모듈 구성

| 순서 | 앱/모듈 | 기능 이름 | 입력값 | 매핑값 | 예상 출력값 |
|---:|---|---|---|---|---|
| 1 | Webhooks | Custom Webhook | 요청 JSON | 전체 body | `newsletter_name`, `sender`, `subject`, `body`, `received_date`, `message_id` |
| 2 | Router | Route Split | Webhook output | 3개 경로 | 경제전문, 종합시사, 미분류 |
| 3 | Filter | 경제전문 | `newsletter_name` | 너겟레터/순살브리핑/데일리바이트/어피티 포함 | `newsletter_group=경제전문` |
| 4 | Filter | 종합시사 | `newsletter_name` | 뉴닉/디그 포함 | `newsletter_group=종합시사` |
| 5 | Filter | 미분류 | 위 조건 불일치 | 기본 경로 | `newsletter_group=미분류` |
| 6 | Tools | Set Variables | subject/body | 키워드 우선순위 배열 | `main_topic`, `secondary_keywords`, `important_news` |
| 7 | Google Sheets | Add a Row | 정규화 결과 | 뉴스수집 컬럼 | 저장된 행 |
| 8 | Filter | 중요 뉴스 | `important_news=true` | 키워드가 1개 이상 | 알림 경로 진입 |
| 9 | Discord 또는 Gmail | Send a Message | 중요 뉴스 메시지 | 알림 템플릿 | 발송 결과 |
| 10 | Webhooks | Webhook Response | 처리 결과 | JSON 응답 | 성공/오류 응답 |
| 11 | Error Handler | Break/Resume | 모듈 오류 | 오류로그 시트 | 재시도 또는 관리자 확인 |

## Router 조건

- 경제전문: `newsletter_name` is one of `너겟레터`, `순살브리핑`, `데일리바이트`, `어피티`
- 종합시사: `newsletter_name` is one of `뉴닉`, `디그`
- 미분류: 위 조건에 모두 해당하지 않음

## 키워드 분류 구현

Make의 Set Variables 또는 Text Parser에서 다음 우선순위로 `subject + body`를 검사한다.

1. 금리
2. 환율
3. 주식시장
4. 부동산
5. 반도체
6. AI
7. 물가
8. 관세
9. 가상자산
10. 경기

첫 번째로 발견한 주제를 `main_topic`으로 저장하고, 발견된 모든 키워드를 `secondary_keywords`에 쉼표로 저장한다. 키워드가 없으면 `main_topic=기타`, `important_news=false`로 처리한다.

## 인증 정보

Google Sheets Connection, Gmail Connection, Discord Webhook URL은 Make Connection 또는 변수 저장소에만 보관한다. 제출 파일에는 실제 인증값을 포함하지 않는다.
