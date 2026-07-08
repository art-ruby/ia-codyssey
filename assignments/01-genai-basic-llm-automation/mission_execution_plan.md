# Hermes Agent LLM 비교 평가 미션 실행 계획

## 1. 확정된 업무 과업

> Hermes Agent 관련 원문과 벤치마크를 바탕으로 한국어 AI 뉴스 블로그 콘텐츠 패키지를 자동 생성하고, ChatGPT·Claude·Gemini 결과를 동일 기준으로 평가한다.

## 2. 입력 자료

- Hermes Agent GPTERS 분석 글
- Nick Spisak X 원문 링크
- Hermes Agent와 OpenClaw 비교 내용
- 네이버 블로그 형식 벤치마크
- AI 도구 소개 콘텐츠 구성 벤치마크

## 3. 출력 자료

- 마크다운 기획·메타 문서
- 게시 가능한 완결형 HTML
- 제목과 썸네일 문구
- 이미지 프롬프트 3개와 각각의 alt 텍스트
- Sora 2 영상 프롬프트, 내레이션, 자막
- SEO 설명과 해시태그

## 4. 실험 입력

고정 입력 패키지:

```text
evaluation/test_inputs/hermes_agent/
├── README.md
├── article_source.md
├── source_manifest.md
├── expected_facts.md
└── test_case.md
```

`expected_facts.md`의 검증 항목:

- 개발 주체
- 라이선스
- 지원 환경
- 설치 명령
- 메모리 및 스킬 기능
- 메시징 지원 범위
- OpenClaw 비교 주장
- 확인되지 않은 숫자와 표현

현재 상태: **완료**

## 5. 공통 프롬프트

세 모델에 동일하게 적용한 프롬프트:

```text
evaluation/prompts/comparison/prompt_ai_news_content_package_common_v6_final.md
```

통일한 요소:

- 입력 기사
- 형식 벤치마크
- 콘텐츠 벤치마크
- 출력 항목과 순서
- HTML 구조와 길이
- 사실 검증 규칙
- 출력 구분자

현재 상태: **완료**

## 6. 모델별 결과

```text
evaluation/model_outputs/
├── execution_conditions.md
├── chatgpt/
│   ├── raw_response.md
│   ├── package.md
│   ├── blog.html
│   ├── image1.png
│   ├── image2.png
│   ├── image3.png
│   └── run_metadata.md
├── claude/
│   ├── package.md
│   ├── blog.html
│   ├── image1.png
│   ├── image2.png
│   ├── image3.png
│   ├── source_record.md
│   └── run_metadata.md
└── gemini/
    ├── index.md
    ├── index.html
    ├── image1.png
    ├── image2.png
    ├── image3.png
    └── run_metadata.md
```

실행 모델:

| 모델 | 실행 조건 | 프롬프트 |
|---|---|---|
| ChatGPT 5.5 | 중간, ChatGPT Pro, 웹 | 공통 v6 Final |
| Claude Sonnet 5 | 무료 시험, 웹 | 공통 v6 Final |
| Gemini 3.1 Pro | Gemini Pro, 웹 | 공통 v6 Final |

공통 실행 정보:

- 실행 날짜: 2026-07-06
- 정확한 실행 시각: 기록 없음
- 주요 설정: 별도 설정 없음
- 응답 생성 시간: 미측정
- Claude 무료 버전 제한사항: 프로젝트 기능을 이용한 작업에 제한이 있음

현재 상태: **결과 및 제공된 실행 메타데이터 저장 완료**

## 7. 자동 검증

기계적으로 확인할 항목:

- 필수 섹션 존재 여부
- 이미지 프롬프트 3개 여부
- 이미지 위치 또는 실제 이미지 태그 3개
- HTML 시작·종료 태그
- HTML 내부 마크다운 혼입 여부
- 해시태그 10개 이상
- Sora 필수 문구
- 출력 구분자
- SEO meta description
- 인라인 CSS 준수

현재 상태: **완료**

## 8. 수동 검증

사람이 평가할 항목:

- 사실성
- 기사 충실도
- 한국어 자연스러움
- 콘텐츠 전개력
- 형식 벤치마크 반영
- HTML 완성도
- 비교의 균형성
- 실무 수정량

현재 상태: **완료**

## 9. 비교 평가표

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

각 항목은 1~5점과 결과물의 실제 문장·구조를 근거로 기록한다.

최종 평가 결과:

1. ChatGPT 5.5 중간 — 86.5점
2. Claude Sonnet 5 무료 시험 — 84.0점
3. Gemini 3.1 Pro — 75.5점

평가 문서:

- `scores/hermes_agent/05_model_evaluation_table.md`
- `scores/hermes_agent/05_model_evaluation_table.html`

현재 상태: **완료**

## 10. 추가 미션 과제

### 10.1 Few-shot 예시 3개

최종 시스템 프롬프트 설계 문서에 다음 예시가 필요하다.

1. 충분한 기사 입력
2. 사실과 해석이 섞인 기사
3. 정보가 부족해 확인 질문이 필요한 기사

권장 저장 경로:

```text
evaluation/few_shot/
├── 01_complete_article_example.md
├── 02_mixed_fact_opinion_example.md
└── 03_insufficient_input_example.md
```

현재 상태: **완료**

### 10.2 v1 → v2 개선 비교

- v1: 기사에서 블로그를 바로 생성
- v2: 사실 추출 → 불확실성 표시 → 구조 설계 → HTML 생성 → 자체 검수

같은 모델과 같은 기사로 실행하고 수정 전후 결과와 개선 근거를 남긴다.

권장 저장 경로:

```text
evaluation/prompt_iterations/hermes_agent/
├── v1/
│   ├── prompt.md
│   ├── raw_response.md
│   └── blog.html
├── v2/
│   ├── prompt.md
│   ├── raw_response.md
│   └── blog.html
└── comparison_report.md
```

현재 상태: **완료**

### 10.3 환각 검증 질문

최소 다음 질문을 검증한다.

1. 공식 라이선스는 무엇인가?
2. 현재 GitHub 스타 수는 얼마인가?
3. 공식 지원 운영체제는 무엇인가?
4. 설치 명령은 현재도 유효한가?
5. OpenClaw 마이그레이션 명령이 실제 존재하는가?
6. `Gemma 4 26B`라는 모델명이 정확한가?
7. `$5 VPS` 운영 가능의 공식 근거가 있는가?

각 질문에 다음을 기록한다.

- 기대 정답 또는 판정 기준
- 참고 출처
- 모델 답변
- Pass/Fail
- 실패 이유

권장 저장 경로:

```text
evaluation/reports/evidence/hallucination_test_results.md
```

현재 상태: **완료 — 공식 자료 검증 및 3모델 생성 결과 기반 Pass/Fail 기록 완료**

### 10.4 10턴 이상 대화 로그

최종 선정 모델인 ChatGPT 5.5 중간을 기준으로 다음 흐름을 포함한다.

1. 기사 입력
2. 핵심 주제 확인
3. 독자층 변경
4. 제목 수정
5. 과장 표현 제거
6. 비교표 보완
7. 출처 없는 수치 삭제
8. HTML 형식 변경
9. 이미지 위치 조정
10. 최종 패키지 재생성
11. 이전 조건 유지 여부 확인

권장 저장 경로:

```text
evaluation/logs/hermes_agent_chatgpt_conversation.md
```

현재 상태: **완료 — 11턴 대화, 이전 조건 유지 검증, 문제·수정 요약 기록**

## 11. 최종 제출 문서

```text
evaluation/reports/
├── 01_llm_model_comparison_report.md
├── 02_system_prompt_design_document.md
├── 03_conversation_execution_log.md
└── evidence/
    ├── common_test_prompt.md
    ├── evaluation_sheet.md
    ├── hallucination_test_results.md
    ├── prompt_v1_v2_comparison.md
    └── model_run_metadata.md
```

현재 상태:

- 모델 평가 원본: 완료
- 최종 제출용 보고서 3개: 완료
- 부속 증빙: 완료

## 12. 남은 작업 우선순위

1. 전체 산출물 링크·파일명·HTML 최종 검수
2. 향후 재실행 시 정확한 실행 시각과 응답 시간을 추가 측정

현재 상태: **필수 미션 완료**

## 13. 완료 판정

다음 조건을 모두 만족하면 미션을 완료한 것으로 본다.

- 세 모델 공통 비교 결과와 평가 근거가 있다.
- Few-shot 예시 3개가 있다.
- v1→v2 실행 결과와 개선 근거가 있다.
- 환각 검증 질문 5개 이상에 Pass/Fail 기록이 있다.
- 10턴 이상 대화 원본과 문제·수정 요약이 있다.
- 모델 비교 보고서, 시스템 설계 문서, 실행 로그가 완성됐다.
- 다른 기사에도 동일 과정을 반복할 수 있다.
