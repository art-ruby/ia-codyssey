# Hermes Agent 평가 출처 목록

## 출처 계층

| 우선순위 | 출처 | 역할 |
|---:|---|---|
| 1 | Hermes Agent 공식 문서·공식 저장소 | 기능, 설치, 라이선스, 지원 환경의 최종 검증 |
| 2 | OpenClaw 공식 문서·공식 저장소 | 비교 대상 기능과 제약의 최종 검증 |
| 3 | Nick Spisak X 아티클 | 핀테크 창업자 사례와 작성자 평가의 원출처 |
| 4 | GPTERS 분석 글 | 한국어 분석 기사와 콘텐츠 구성 |
| 5 | 사용자 제공 고정 입력 | 세 모델에 동일하게 제공하는 평가 원문 |

## 평가 입력 출처

### GPTERS

- 제목: Hermes Agent 완벽 정리 — Hermes vs OpenClaw 비교
- URL: https://www.gpters.org/nocode/post/hermes-agent-complete-summary-2PZjC5NJi81cwNK
- 용도: 분석 기사 원문과 콘텐츠 전개

### X 원문

- 작성자: Nick Spisak
- URL: https://x.com/NickSpisak_/status/2042664522151006664
- 용도: 5개 에이전트 실패·단일 통합 사례와 개인 평가

## 사용 규칙

- 모델 입력에는 `article_source.md`만 고정 원문으로 제공한다.
- 모델이 기사 밖의 정보를 추가하면 별도 근거가 없는 한 감점한다.
- 개인 사례와 평가는 출처 작성자에게 귀속해야 한다.
- 공식 사실처럼 보이는 수치와 명령은 공식 자료 확인 전까지 “확인 필요”로 판정한다.
- 평가 중 원문 오류를 수정해 모델마다 다른 입력을 제공하지 않는다.

## 공식 검증 출처

- Hermes Agent 저장소: https://github.com/NousResearch/hermes-agent
- Hermes Agent 라이선스: https://github.com/NousResearch/hermes-agent/blob/main/LICENSE
- Hermes Agent README: https://github.com/NousResearch/hermes-agent/blob/main/README.md
- OpenClaw 마이그레이션: https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw
- Google Gemma 3 모델 카드: https://ai.google.dev/gemma/docs/core/model_card_3
- 검증 결과 문서: `../../reports/evidence/hallucination_test_results.md`
