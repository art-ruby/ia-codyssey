# 모델 테스트 및 평가

이 디렉터리는 AI 뉴스 콘텐츠 패키지를 ChatGPT, Gemini, Claude에서 생성하고 비교하기 위한 모든 평가 자산을 관리한다.

- 전체 미션 실행 계획: `mission_execution_plan.md`

## 평가 제출 패키지

이 폴더는 단독으로 제출·검토할 수 있는 완결형 평가 패키지다.

- 시작 페이지: `index.html`
- 평가 설명서: `reports/evaluator_guide.html`
- 미션 완료 보고서: `reports/mission_completion_report.html`
- 모델 결과: `model_outputs/`
- 평가표: `scores/hermes_agent/`
- 프롬프트: `prompts/`
- 미션 설계 문서: `docs/`

## 디렉터리

| 경로 | 내용 |
|---|---|
| `benchmarks/` | 형식, 콘텐츠, 인용 사이트 벤치마크 |
| `test_inputs/` | 세 모델에 공통으로 제공할 원문과 정답 기준 |
| `model_outputs/` | 모델별 원본 응답, 마크다운, HTML |
| `scores/` | 평가표, 점수, 판정 근거 |
| `reports/` | 모델 비교 보고서와 최종 선정 문서 |
| `logs/` | 실행 환경, 오류, 수정, 반복 대화 기록 |
| `few_shot/` | 입력 품질별 Few-shot 예시 3개 |
| `prompt_iterations/` | 동일 모델의 v1→v2 개선 비교 |

## 실험 구분

### 공정 비교

동일한 공통 프롬프트와 동일 입력을 세 모델에 사용한다.

- 공통 프롬프트: `prompts/comparison/prompt_ai_news_content_package_common_v6_final.md`

### 최적화 비교

모델별 프롬프트를 사용한다.

- ChatGPT: `prompts/prompt_ai_news_content_package_chatgpt_v3.md`
- Gemini: `prompts/prompt_ai_news_content_package_gemini_v4.md`
- Claude: `prompts/prompt_ai_news_content_package_claude_v5.md`

두 실험의 결과와 점수를 합치지 않는다.

## 권장 테스트 단위

```text
evaluation/
├── test_inputs/hermes_agent/
├── model_outputs/hermes_agent/common/
├── model_outputs/hermes_agent/optimized/
├── scores/hermes_agent/
├── reports/
└── logs/
```

## 현재 평가 세트

- Hermes Agent 입력: `test_inputs/hermes_agent/`
- Hermes Agent 모델 결과: `model_outputs/chatgpt/`, `model_outputs/claude/`, `model_outputs/gemini/`
- Hermes Agent 평가표: `scores/hermes_agent/05_model_evaluation_table.md`
- Hermes Agent HTML 평가 보고서: `scores/hermes_agent/05_model_evaluation_table.html`

현재 실행 조건:

- ChatGPT 5.5 중간: 공통 v6 Final
- Gemini 3.1 Pro: 공통 v6 Final
- Claude Sonnet 5 무료 시험: 공통 v6 Final

세 모델 모두 공통 v6 Final과 동일 기사 입력을 사용했으므로 최종 공정 비교 대상으로 처리한다. Claude의 이전 v5 결과는 별도 파일로 보존한다.
