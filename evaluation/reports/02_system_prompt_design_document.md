# Hermes Agent 시스템 프롬프트 설계 보고서

## 1. 설계 목표

기사 내용을 블로그로 바로 변환하는 방식의 환각과 형식 편차를 줄이고, 다른 AI 기사에도 재사용할 수 있는 단계적 생성 절차를 설계했다.

## 2. 입력 구조

고정 입력 패키지는 기사 원문, 출처 목록, 기대 사실, 테스트 케이스로 구성한다.

```text
evaluation/test_inputs/hermes_agent/
├── article_source.md
├── source_manifest.md
├── expected_facts.md
└── test_case.md
```

## 3. v2 처리 흐름

```text
기사 입력
→ 핵심 사실과 원문 주장 구분
→ 불확실성 및 최신 확인 필요 항목 표시
→ 독자와 콘텐츠 구조 설계
→ 마크다운과 HTML 분리 생성
→ 이미지·영상·본문 메시지 일치 확인
→ HTML·필수 섹션 자체 검수
→ 최종 결과 출력
```

## 4. 핵심 통제 규칙

- 기사에 없는 기능을 추가하지 않는다.
- 변동 가능한 수치와 공식 확인이 필요한 정보는 별도 표시한다.
- 사실, 기사 주장, 해석을 구분한다.
- 마크다운과 HTML 출력 영역을 명확히 분리한다.
- HTML은 게시 가능한 구조와 인라인 CSS 조건을 따른다.
- 이미지 3개의 위치와 본문 역할을 연결한다.
- Sora 영상 프롬프트, 내레이션, 자막의 핵심 메시지를 통일한다.
- 출력 전 필수 항목을 자체 검수한다.

## 5. Few-shot 구성

| 예시 | 목적 | 파일 |
|---|---|---|
| 충분한 기사 | 정상적인 완결형 생성 방식 제시 | `evaluation/few_shot/01_complete_article_example.md` |
| 사실·해석 혼합 | 확정 사실과 해석 분리 방법 제시 | `evaluation/few_shot/02_mixed_fact_opinion_example.md` |
| 정보 부족 | 확인 질문과 생성 보류 기준 제시 | `evaluation/few_shot/03_insufficient_input_example.md` |

## 6. v1→v2 개선

v1은 기사 입력 후 마크다운과 HTML을 바로 생성했다. v2는 사실 검토, 불확실성 표시, 구조 설계와 자체 검수를 추가했다.

주요 개선:

- GitHub 스타·라이선스·비용을 확정 표현에서 확인 필요로 변경
- SEO meta description 추가
- HTML을 인라인 CSS 중심으로 표준화
- 이미지와 본문 흐름 연결
- 자동 파싱용 출력 구조 정리
- 결과 파일명과 메타데이터 관리 강화

증빙: `evaluation/reports/evidence/prompt_v1_v2_comparison.md`

## 7. 재사용 절차

1. 새 기사와 출처를 입력 패키지에 저장한다.
2. 공식 사실과 기사 주장을 `expected_facts.md`에 구분한다.
3. 공통 프롬프트로 모델 결과를 생성한다.
4. 자동 형식 검사와 수동 품질 평가를 수행한다.
5. 환각 위험 항목을 공식 출처로 검증한다.
6. 사용자 피드백을 반영하고 누적 조건을 최종 확인한다.

## 8. 한계와 보완

- 최신 사실 확인은 웹 접근과 공식 출처 가용성에 의존한다.
- 자체 검수는 모델의 선언만으로 끝내지 말고 결과 파일을 별도 검사해야 한다.
- 모델별 서비스 조건 차이는 실행 메타데이터에서 명시해야 한다.

## 9. 관련 파일

- `evaluation/model_outputs/prompt_ai_news_content_package_common_v6_final.md`
- `evaluation/few_shot/`
- `evaluation/prompt_iterations/hermes_agent/`
- `evaluation/reports/evidence/common_test_prompt.md`

