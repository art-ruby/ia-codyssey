# Hermes Agent 미션 최종 제출 구조

## 1. 제출 패키지의 세 계층

최종 제출물은 다음 세 계층으로 구분한다.

1. **최종 보고서 3종**: 실험의 결론과 설계·수행 과정을 설명하는 문서
2. **모델별 결과물**: ChatGPT·Claude·Gemini가 실제로 생성한 블로그 패키지
3. **부속 증빙**: 보고서의 주장과 점수를 재검증할 수 있는 원자료

모델별 블로그 HTML 3건은 최종 보고서가 아니라 **실험 결과물**이다. 보고서에서 해당 HTML을 비교·인용하고, 원본은 증빙으로 함께 제출한다.

## 2. 최종 보고서 3종

### 2.1 LLM 모델 비교 평가 보고서

권장 파일:

`evaluation/reports/01_llm_model_comparison_report.md`

목적:

- ChatGPT·Claude·Gemini 결과를 같은 평가 기준으로 비교
- 모델별 장단점과 점수 근거 제시
- 최종 선정 모델과 선정 이유 설명

포함 내용:

1. 실험 목적과 비교 모델
2. 동일 입력·동일 프롬프트 조건
3. 평가 항목과 가중치
4. 모델별 점수와 실제 근거
5. 사실성·형식·가독성·HTML 비교
6. 최종 순위
7. 최종 선정 모델과 활용 권고
8. 실험 한계

핵심 증빙:

- `evaluation/scores/hermes_agent/05_model_evaluation_table.md`
- 모델별 `package.md` 또는 대응 마크다운
- 모델별 HTML
- 모델별 `run_metadata.md`
- `evaluation/reports/evidence/hallucination_test_results.md`

### 2.2 시스템 프롬프트 설계 보고서

권장 파일:

`evaluation/reports/02_system_prompt_design_document.md`

목적:

- 최종 프롬프트가 어떤 문제를 해결하도록 설계됐는지 설명
- v1에서 v2로 바뀐 통제 규칙과 개선 효과 기록
- 다른 기사에도 반복 적용할 수 있는 생성 절차 제시

포함 내용:

1. 프롬프트 설계 목표
2. 입력 자료 구조
3. 사실과 해석의 구분 규칙
4. 불확실한 정보 처리 규칙
5. 마크다운·HTML 출력 계약
6. 이미지·영상 프롬프트 연계 방식
7. 자체 검수 항목
8. Few-shot 예시 3종의 역할
9. v1→v2 개선 비교
10. 재사용 절차와 한계

핵심 증빙:

- 공통 v6 Final 프롬프트
- `evaluation/few_shot/`의 예시 3종
- `evaluation/prompt_iterations/hermes_agent/comparison_report.md`
- v1·v2 프롬프트와 결과 매니페스트

### 2.3 대화 실행 및 수정 이력 보고서

권장 파일:

`evaluation/reports/03_conversation_execution_log.md`

목적:

- 최초 생성본이 사용자 피드백을 거쳐 어떻게 수정됐는지 설명
- 최종 결과가 누적 조건을 유지했는지 증명
- 실제 운영 과정에서 필요한 수정량과 유형 기록

포함 내용:

1. 실행 모델과 날짜
2. 대화 목적
3. 11턴 흐름 요약
4. 독자층·제목·문체 수정
5. 비교표·수치 검증 수정
6. 티스토리 HTML 변환
7. 이미지 위치 조정
8. 최종 조건 유지 Pass/Fail
9. 문제·수정 결과 요약
10. 최종 결과물 경로

핵심 증빙:

- `evaluation/logs/hermes_agent_chatgpt_conversation.md`
- ChatGPT 최초 응답
- ChatGPT 최종 `package.md`
- ChatGPT 최종 `blog.html`

## 3. 모델별 블로그 결과물 3건

블로그 HTML 3건은 모델 비교의 직접 대상이다.

| 모델 | HTML 결과 | 마크다운 결과 |
|---|---|---|
| ChatGPT | `evaluation/model_outputs/chatgpt/blog.html` | `evaluation/model_outputs/chatgpt/package.md` |
| Claude | `evaluation/model_outputs/claude/blog.html` | `evaluation/model_outputs/claude/package.md` |
| Gemini | `evaluation/model_outputs/gemini/index.html` | `evaluation/model_outputs/gemini/index.md` |

각 모델 폴더에는 다음 자료를 함께 유지한다.

- 블로그 HTML
- 마크다운 패키지
- 이미지 3개
- 실행 메타데이터
- 가능한 경우 원본 응답 또는 출처 기록

권장 보완:

- Gemini의 `index.html`, `index.md`를 공통 명칭인 `blog.html`, `package.md`로 복제하거나 매핑표에 명시
- 모델별 파일명이 다른 이유를 실행 메타데이터에 기록

## 4. 부속 증빙 문서

부속 증빙은 보고서의 결론을 제3자가 다시 확인할 수 있게 하는 자료다.

### 4.1 공통 테스트 프롬프트

권장 파일:

`evaluation/reports/evidence/common_test_prompt.md`

증명하는 내용:

- 세 모델에 동일한 지시가 사용됐음
- 출력 규칙과 사실 검증 조건이 같았음

원본을 새로 작성하기보다 공통 v6 Final 프롬프트의 경로와 버전, 해시 또는 사본을 기록한다.

### 4.2 평가 시트

권장 파일:

`evaluation/reports/evidence/evaluation_sheet.md`

증명하는 내용:

- 점수와 순위가 어떤 항목·가중치·근거로 계산됐는지
- 평가자의 자의적 판단만으로 순위를 정하지 않았는지

기존 `05_model_evaluation_table.md`를 제출용 증빙으로 연결하거나 사본을 둔다.

### 4.3 환각 검증 결과

현재 파일:

`evaluation/reports/evidence/hallucination_test_results.md`

증명하는 내용:

- 라이선스, GitHub 스타, 지원 환경, 설치 명령, 마이그레이션 명령, 모델명, VPS 비용을 검증했음
- 모델별 Pass/Fail과 실패 이유가 있음

### 4.4 v1→v2 개선 비교

권장 파일:

`evaluation/reports/evidence/prompt_v1_v2_comparison.md`

증명하는 내용:

- 최종 프롬프트가 최초 방식보다 무엇을 개선했는지
- 사실성·HTML 이식성·형식 준수·운영 편의성이 실제 결과에서 좋아졌는지

기존 `evaluation/prompt_iterations/hermes_agent/comparison_report.md`를 핵심 증빙으로 사용한다. v2는 완전히 새로운 실험이라기보다 v1 결과를 대화형 검토로 보완한 개선본이라는 점을 명시한다.

### 4.5 모델 실행 메타데이터

권장 파일:

`evaluation/reports/evidence/model_run_metadata.md`

증명하는 내용:

- 사용 모델, 요금제, 웹 사용 여부, 실행일, 주요 제한 조건
- 비교 조건이 어디까지 동일했고 무엇이 달랐는지

모델별 `run_metadata.md`와 `execution_conditions.md`를 하나의 표로 통합한다. 기록하지 않은 시각·응답 시간은 추정하지 않고 “미측정”으로 표시한다.

### 4.6 대화 로그

현재 파일:

`evaluation/logs/hermes_agent_chatgpt_conversation.md`

증명하는 내용:

- 11턴의 실제 개선 흐름
- 누적 조건 유지 여부
- 문제와 수정 결과

## 5. 최종 제출 체크리스트

| 확인 항목 | 기준 |
|---|---|
| 보고서 3종 | 평가·설계·대화 실행 보고서가 각각 존재 |
| 모델 결과 3종 | 각 모델의 HTML·마크다운·이미지가 존재 |
| 공통 조건 | 동일 입력과 공통 프롬프트 경로가 명시됨 |
| 평가 근거 | 점수마다 실제 문장 또는 구조 근거가 있음 |
| 사실 검증 | 환각 검증 Pass/Fail과 출처가 있음 |
| 개선 증빙 | v1→v2 차이와 대화형 수정 과정이 연결됨 |
| 재현성 | 모델·실행 조건·날짜·미측정 항목이 기록됨 |
| 링크 검수 | 보고서에서 참조하는 모든 파일이 실제로 존재 |
| HTML 검수 | 한글, 이미지, 표, CSS, 마크다운 혼입 여부 확인 |

## 6. 권장 제출 폴더

```text
evaluation/
├── reports/
│   ├── 01_llm_model_comparison_report.md
│   ├── 02_system_prompt_design_document.md
│   ├── 03_conversation_execution_log.md
│   ├── mission_completion_report.html
│   ├── final_submission_structure.md
│   └── evidence/
│       ├── common_test_prompt.md
│       ├── evaluation_sheet.md
│       ├── hallucination_test_results.md
│       ├── prompt_v1_v2_comparison.md
│       └── model_run_metadata.md
├── model_outputs/
│   ├── chatgpt/
│   ├── claude/
│   └── gemini/
└── logs/
    └── hermes_agent_chatgpt_conversation.md
```

## 7. 결론

사용자가 제안한 “평가보고서 1건 + 수행 정리 보고서 2건 + 모델별 HTML 3건”의 큰 방향은 맞다. 다만 제출 역할을 다음처럼 명확히 구분해야 한다.

- 평가보고서 1건: 모델 비교와 최종 선정
- 수행 정리 보고서 2건: 시스템 프롬프트 설계, 대화 실행·수정 이력
- 블로그 HTML 3건: 보고서가 아니라 모델별 실험 결과물
- 부속 증빙: 점수, 사실 검증, 개선 효과, 실행 조건을 재검증하는 원자료
