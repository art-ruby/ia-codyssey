# 최종 제출 보고서

## 1. 과제 개요

Make와 n8n을 사용해 경제 뉴스레터 자동 분류 및 핫이슈 감지 워크플로우를 구현했다. HTTP Webhook으로 테스트 데이터를 먼저 처리하고, 이후 Gmail Trigger로 전환 가능한 구조를 별도 JSON과 문서로 제시했다.

## 2. 자동화 대상 업무

뉴스레터 수신 데이터에서 뉴스레터명, 발신자, 제목, 본문, 수신일, 메시지 ID를 받아 경제 키워드를 추출하고 Google Sheets에 저장한다. 같은 날짜에 같은 주제가 서로 다른 뉴스레터에서 반복되면 핫이슈로 판단한다.

## 3. 문제 정의

여러 경제 뉴스레터를 사람이 직접 확인하면 같은 이슈가 반복되는지 판단하기 어렵고, 중복 저장과 알림 누락 가능성이 높다. 이 과제는 수집, 분류, 저장, 중복 방지, 핫이슈 감지를 자동화해 반복 업무를 줄이는 것을 목표로 한다.

## 4. HTTP Webhook을 먼저 사용한 이유

Gmail 인증과 실제 메일 수신 상태에 의존하지 않고 고정된 JSON으로 로직을 검증하기 위해 HTTP Webhook을 먼저 사용했다. 이 방식은 테스트 재현성이 높고, Make와 n8n을 같은 입력으로 비교하기 쉽다.

## 5. 프로젝트 1 Make 구현

Make는 Custom Webhook, Router, Filter, Tools Set Variables, Google Sheets Add a Row, Discord/Gmail 알림, Webhook Response, Error Handler로 구성했다. 모듈별 설정은 `make/project1_build_guide.md`와 `make/filters_and_mappings.md`에 정리했다.

## 6. 프로젝트 1 n8n 구현

n8n은 `n8n/project1_webhook_classification.json`으로 구현했다. 필수값 검증, 뉴스레터 그룹 분류, 경제 키워드 분류, Google Sheets 저장, 중요 뉴스 응답까지 포함한다.

## 7. Make와 n8n 비교

Make는 비개발자가 화면 흐름을 이해하고 빠르게 구축하기 좋다. n8n은 Code 노드를 사용해 키워드 우선순위와 source_count 계산 같은 복잡한 로직을 구현하기 좋다. 상세 비교는 `reports/make_vs_n8n_comparison.md`에 작성했다.

## 8. 프로젝트 2 핫이슈 감지 구현

`n8n/project2_hot_issue_detection.json`은 프로젝트 1을 확장해 `message_id` 중복 확인과 같은 날짜/같은 주제 기준 source_count 계산을 추가했다. `source_count >= 2`이면 핫이슈로 분류한다.

## 9. Google Sheets 구조

Google Sheets는 `뉴스수집`, `핫이슈`, `키워드목록`, `오류로그` 4개 시트로 구성한다. 필드 구조는 `sheets/sheet_structure.md`에 정의했다.

## 10. 테스트 과정

`tests/test_requests.md`의 5개 요청을 순서대로 전송한다. 테스트 1과 2는 금리 이슈가 서로 다른 뉴스레터에서 반복되는지 확인하고, 테스트 4는 중복 메시지 방지를 확인한다.

## 11. 테스트 결과

예상 결과는 `tests/expected_results.md`에 정리했다. 핵심 기대값은 테스트 2에서 `source_count=2`, `issue_level=관심`, `hot_issue=true`가 나오는 것이다.

## 12. Gmail Trigger 전환

HTTP 기반 프로젝트 2가 정상 동작한 뒤 `n8n/gmail_trigger_version.json`을 사용해 Gmail Trigger 출력을 공통 JSON으로 변환한다. 이후 분류, 중복 확인, Sheets 저장, 핫이슈 계산은 HTTP 버전과 동일한 로직을 사용한다.

## 13. 오류 처리

필수값 누락은 HTTP 400과 `VALIDATION_ERROR`로 응답한다. 중복 메시지는 신규 행을 만들지 않고 `duplicate` 응답을 반환한다. Google Sheets나 알림 발송 오류는 `오류로그` 시트에 기록하도록 설계했다.

## 14. 보안 대책

실제 API Key, Gmail Credential, Google Sheets ID, Discord Webhook URL은 산출물에 포함하지 않았다. 모든 민감 정보는 각 도구의 Credential 또는 Connection 기능에 저장한다.

## 15. 개선 방향

Google Sheets 대신 데이터베이스를 사용하면 조회와 집계 안정성이 올라간다. 키워드 포함 여부만으로 분류하기보다 AI 분류나 임베딩 유사도를 도입하면 같은 이슈를 더 정확하게 묶을 수 있다.

## 16. 결론

단순 분류와 빠른 시연은 Make가 적합하고, 중복 방지와 핫이슈 감지처럼 로직이 복잡한 자동화는 n8n이 적합하다. 본 산출물은 두 도구의 구현 방식을 모두 제시하고, 최종적으로 n8n에서 확장 자동화가 가능한 구조를 제공한다.

## 17. 스크린샷 첨부

실제 캡처 항목과 파일명은 `docs/screenshot_guide.md`에 정리했다. 캡처 시 인증값과 개인 정보는 반드시 마스킹한다.
