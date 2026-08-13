# Hermes Agent Few-shot 예시

동일한 Hermes Agent 소재를 입력 품질에 따라 세 가지로 구성한 예시다.

| 파일 | 입력 상태 | 기대 동작 |
|---|---|---|
| `01_complete_article_example.md` | 충분한 기사 | 추가 질문 없이 전체 콘텐츠 패키지 생성 |
| `02_mixed_fact_opinion_example.md` | 사실·의견 혼합 | 사실, 원문 주장, 확인 필요 항목 분리 |
| `03_insufficient_input_example.md` | 정보 부족 | 콘텐츠 생성 중단 후 추가 정보 요청 |

새로운 뉴스 기사 세 개를 수집하는 것이 아니다. 동일한 소재를 사용해 시스템 프롬프트가 입력 품질에 따라 올바르게 행동하는지 검증한다.

