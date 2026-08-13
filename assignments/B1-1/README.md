# GenAI 기초 1: LLM 기반 업무 자동화

## Assignment 01: AI Tech News Blog Automation

이 저장소의 1번 과제는 AI 뉴스 기사 하나를 입력해 ChatGPT, Claude, Gemini 3개 모델로 블로그 콘텐츠 패키지를 만들고, 결과를 비교 평가한 자동화 실험입니다.

평가자가 외부 링크를 열지 않아도 핵심 기준을 확인할 수 있도록 아래 문서에 과제 제출 항목별 근거를 본문으로 정리했습니다.

- 평가 기준 대응 정리: `EVALUATION_RESPONSE.md`
- 과제 01 메인 페이지: `index.html`
- 모델 비교 평가표: `scores/hermes_agent/05_model_evaluation_table.md`
- 최종 비교 보고서: `reports/01_llm_model_comparison_report.md`
- 시스템 프롬프트 설계 보고서: `reports/02_system_prompt_design_document.md`
- 10턴 이상 대화 로그 요약: `reports/03_conversation_execution_log.md`

## 제출물 핵심 요약

| 항목 | 제출 내용 |
|---|---|
| 업무 과업 | AI 뉴스 기사를 블로그 게시용 마크다운, HTML, 이미지 프롬프트, 영상 프롬프트, SEO 패키지로 변환 |
| 타겟 사용자 | 1인 창업자, AI 콘텐츠 제작자, 기술 블로그 운영자 |
| 입력 템플릿 | 기사 정보, 작성 조건, 사실 검증, 출력 요청을 분리한 복사 가능 템플릿 |
| 사용 모델 | ChatGPT 5.5, Claude Sonnet 5, Gemini 3.1 Pro |
| 최종 선정 | ChatGPT 5.5 |
| 선정 이유 | 총점 86.5점으로 1위이며 사실성, 형식 준수, HTML 이식성, 누적 수정 유지가 가장 안정적 |
| 환각 검증 | 라이선스, 스타 수, 설치 명령, 마이그레이션 명령, 모델명, 비용, 보안 주장 검증 |
| 대화 로그 | 11턴 대화로 독자층, 제목, 문체, 수치, HTML, 이미지 위치 조건을 순차 개선 |

## 모델 비교 결과

| 순위 | 모델 | 점수 | 주요 근거 |
|---:|---|---:|---|
| 1 | ChatGPT 5.5 | 86.5 | 위험한 수치를 보수적으로 처리하고 인라인 HTML 구조가 안정적 |
| 2 | Claude Sonnet 5 | 84.0 | 사실 확인 섹션과 SEO 구조가 좋으나 일부 표현 강도 보완 필요 |
| 3 | Gemini 3.1 Pro | 75.5 | 구성은 완결적이나 입력 밖 추론과 CSS 형식 위반 수정 필요 |

## 주요 산출물 위치

| 항목 | 위치 |
|---|---|
| 평가 기준 대응 정리 | `EVALUATION_RESPONSE.md` |
| 과제 진입 페이지 | `index.html` |
| 평가자 안내서 | `evaluator_guide.html` |
| 미션 완료 보고서 | `mission_completion_report.html` |
| 실행 계획 | `mission_execution_plan.md` |
| 제출 매니페스트 | `SUBMISSION_MANIFEST.md` |
| 벤치마크 | `benchmarks/` |
| 문서 | `docs/` |
| Few-shot 예시 | `few_shot/` |
| 실행 및 대화 로그 | `logs/` |
| 모델별 결과 | `model_outputs/` |
| 프롬프트 | `prompts/` |
| 프롬프트 개선 비교 | `prompt_iterations/` |
| 최종 보고서와 증빙 | `reports/` |
| 평가표 | `scores/` |
| 테스트 입력 | `test_inputs/` |

## 완료 상태

- 세 모델 결과물 정리 완료
- 공통 프롬프트 정리 완료
- 평가표 및 근거 정리 완료
- 환각 검증 정리 완료
- v1 to v2 프롬프트 개선 비교 정리 완료
- 11턴 대화 로그 정리 완료
- 최종 보고서 및 제출 문서 정리 완료
