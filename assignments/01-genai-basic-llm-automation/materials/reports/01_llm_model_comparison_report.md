# Hermes Agent LLM 모델 비교 평가 보고서

## 1. 평가 목적

동일한 Hermes Agent 기사와 공통 출력 조건을 ChatGPT 5.5 중간, Claude Sonnet 5 무료 시험, Gemini 3.1 Pro에 적용하고 한국어 AI 뉴스 콘텐츠 제작 성능을 비교했다.

## 2. 공통 조건

- 실행일: 2026-07-06
- 입력: `evaluation/test_inputs/hermes_agent/`
- 공통 프롬프트: `evaluation/model_outputs/prompt_ai_news_content_package_common_v6_final.md`
- 출력: 마크다운 패키지, 블로그 HTML, 이미지 3개, 영상 프롬프트, SEO 요소
- 평가 방식: 8개 평가 축의 가중 합산

정확한 실행 시각과 응답 생성 시간은 기록하지 않아 비교 지표에서 제외했다.

## 3. 평가 기준

| 평가 축 | 가중치 |
|---|---:|
| 사실 정확성·환각 억제 | 25% |
| 입력 기사 충실도 | 15% |
| 형식 준수 | 15% |
| 콘텐츠 구조 | 15% |
| 한국어 가독성 | 10% |
| HTML 완성도 | 10% |
| 이미지·영상 프롬프트 연계 | 5% |
| 운영·파싱 편의성 | 5% |

## 4. 최종 결과

| 순위 | 모델 | 점수 | 종합 판단 |
|---:|---|---:|---|
| 1 | ChatGPT 5.5 중간 | 86.5 | 사실성, 구조, 형식 준수의 균형이 가장 안정적 |
| 2 | Claude Sonnet 5 무료 시험 | 84.0 | 한국어 가독성과 콘텐츠 구성은 우수하나 일부 확정 표현 보완 필요 |
| 3 | Gemini 3.1 Pro | 75.5 | 시각적 구성은 활용 가능하나 사실 검증과 출력 표준화에서 추가 수정 필요 |

## 5. 모델별 결과

### ChatGPT

- 장점: 불확실한 수치를 확인 필요 항목으로 분리하고 출력 구조를 비교적 안정적으로 준수했다.
- 보완점: 최초 결과의 과장 표현과 독자층 범위는 대화형 수정 과정에서 조정했다.
- 결과: `evaluation/model_outputs/chatgpt/`

### Claude

- 장점: 문장 흐름과 블로그형 전개가 자연스럽고 이미지 메시지 연결이 명확했다.
- 보완점: 초기 결과에서 GitHub 스타, 라이선스, VPS 비용을 확정적으로 사용한 사례가 있었다.
- 결과: `evaluation/model_outputs/claude/`

### Gemini

- 장점: HTML 및 이미지 결과를 한 세트로 확보했다.
- 보완점: 사실성·형식 준수·운영 편의성에서 상대적으로 수정량이 컸다.
- 결과: `evaluation/model_outputs/gemini/`

## 6. 사실성 검증

라이선스, GitHub 스타, 지원 운영체제, 설치 명령, OpenClaw 마이그레이션, 모델명, VPS 비용을 별도 검증했다. 변동 가능하거나 공식 근거가 부족한 정보는 확정 사실로 사용하지 않는 것을 합격 기준으로 삼았다.

증빙: `evaluation/reports/evidence/hallucination_test_results.md`

## 7. 최종 선정

ChatGPT 5.5 중간을 최종 모델로 선정한다. 최고 점수뿐 아니라 대화형 수정에서 독자층, 문체, 비교표, 수치, HTML, 이미지 위치 조건을 누적 유지할 수 있었기 때문이다.

## 8. 한계

- 모델별 요금제와 웹 접근 조건이 완전히 동일하지 않았다.
- 정확한 실행 시각과 생성 시간은 미측정이다.
- 모델 서비스가 갱신되면 동일 프롬프트의 결과가 달라질 수 있다.

## 9. 근거 문서

- `evaluation/scores/hermes_agent/05_model_evaluation_table.md`
- `evaluation/reports/evidence/evaluation_sheet.md`
- `evaluation/reports/evidence/model_run_metadata.md`
- `evaluation/reports/evidence/hallucination_test_results.md`

