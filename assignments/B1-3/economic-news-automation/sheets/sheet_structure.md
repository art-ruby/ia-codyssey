# Google Sheets 구조

하나의 Google Sheets 문서 안에 아래 4개 시트를 생성한다.

## 뉴스수집

| 필드명 | 설명 |
|---|---|
| collected_at | 자동화 실행 시각 |
| received_date | 뉴스 수신 날짜 |
| newsletter_name | 뉴스레터명 |
| newsletter_group | 경제전문, 종합시사, 미분류 |
| sender | 발신자 |
| subject | 제목 |
| body_preview | 본문 일부 |
| main_topic | 대표 경제 키워드 |
| secondary_keywords | 추가 키워드 |
| source_count | 서로 다른 뉴스레터 수 |
| issue_level | 일반, 관심, 핵심 |
| hot_issue | TRUE/FALSE |
| message_id | 고유 메시지값 |
| processing_status | SUCCESS, DUPLICATE, ERROR |
| error_message | 오류 내용 |

## 핫이슈

| 필드명 |
|---|
| detected_at |
| issue_date |
| main_topic |
| source_count |
| issue_level |
| newsletters |
| related_subjects |
| notification_sent |
| last_updated_at |

## 키워드목록

| 필드명 |
|---|
| main_topic |
| keyword |
| active |
| priority |

## 오류로그

| 필드명 |
|---|
| error_time |
| workflow_name |
| node_name |
| message_id |
| error_type |
| error_message |
| retry_status |
