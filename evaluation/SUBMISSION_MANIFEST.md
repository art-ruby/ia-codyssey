# Evaluation 제출 패키지 목록

## 제출 단위

`evaluation/` 폴더 전체

이 폴더만으로 과제 설명, 입력 자료, 프롬프트, 모델 결과, 평가표, 개선 기록,
대화 로그, 최종 보고서와 웹 열람 페이지를 확인할 수 있다.

## 시작 위치

1. 웹 열람: `index.html`
2. 평가 설명: `reports/evaluator_guide.html`
3. 전체 상태: `reports/mission_completion_report.html`
4. 폴더 안내: `README.md`

## 필수 구성

| 경로 | 내용 |
|---|---|
| `docs/` | 공개 미션, 공통 프롬프트 전략, 실행 계획 |
| `prompts/` | 모델별 프롬프트와 공통 비교 프롬프트 |
| `benchmarks/` | 형식·콘텐츠 벤치마크와 원문 기록 |
| `test_inputs/` | 기사 원문, 출처, 기대 사실, 테스트 케이스 |
| `model_outputs/` | ChatGPT·Claude·Gemini 결과와 이미지 |
| `scores/` | 가중 평가표와 HTML |
| `prompt_iterations/` | v1→v2 프롬프트 및 비교 |
| `few_shot/` | 입력 유형별 Few-shot 3종 |
| `logs/` | 11턴 대화형 개선 기록 |
| `reports/` | 최종 보고서 3종, 설명서, 완료 보고서, 증빙 |

## 완결성 기준

- 세 모델의 마크다운·HTML·이미지 결과가 있다.
- 공통 입력과 공통 프롬프트가 폴더 안에 있다.
- 모델 평가 점수와 실제 근거가 있다.
- 환각 검증 질문의 Pass/Fail 기록이 있다.
- v1→v2 개선 근거가 있다.
- 11턴 대화 로그와 최종 조건 검증이 있다.
- 평가자가 브라우저로 확인할 HTML 문서가 있다.

## 외부 요소

`.github/workflows/pages.yml`은 무료 공개 사이트 배포를 위한 저장소 자동화 설정이며
평가 내용 자체에는 필요하지 않다. 평가 자료와 증빙은 모두 `evaluation/` 안에 있다.
