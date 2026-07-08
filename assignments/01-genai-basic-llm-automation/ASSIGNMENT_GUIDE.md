# AI Tech News Blog Automation 과제 안내

## 한 줄 설명

AI 기술 뉴스 원문을 한국어 블로그 콘텐츠로 자동 생성하고, ChatGPT, Claude, Gemini 결과를 비교 평가한 LLM 기반 업무 자동화 과제입니다.

## 평가자가 먼저 볼 파일

1. `index.html`  
   과제 전체를 브라우저에서 확인하는 시작 페이지입니다.

2. `model_outputs/chatgpt/blog.html`  
   최종 게시용으로 선정한 블로그 결과물입니다.

3. `reports/01_llm_model_comparison_report.md`  
   세 모델을 비교하고 ChatGPT 결과를 최종 선정한 근거입니다.

4. `reports/02_system_prompt_design_document.md`  
   환각 억제, 출력 형식 통제, 재사용 가능한 프롬프트 설계 기준입니다.

5. `scores/hermes_agent/05_model_evaluation_table.md`  
   모델별 점수와 평가 기준입니다.

## 과제 산출물 흐름

```text
뉴스 원문 입력
→ 프롬프트 설계
→ ChatGPT / Claude / Gemini 결과 생성
→ 모델별 결과 비교
→ 환각 위험 검토
→ 최종 블로그 HTML 선정
```

## 폴더 역할

| 폴더 | 역할 |
|---|---|
| `test_inputs/` | 원문, 출처, 기대 사실, 테스트 케이스 |
| `prompts/` | 모델별 프롬프트와 공통 프롬프트 |
| `model_outputs/` | 모델별 생성 결과 |
| `reports/` | 비교 보고서, 시스템 프롬프트 문서, 실행 로그 |
| `scores/` | 모델 평가표 |
| `benchmarks/` | 참고한 블로그 형식과 콘텐츠 벤치마크 |
| `prompt_iterations/` | 프롬프트 개선 과정 |
| `few_shot/` | 입력 유형별 예시 |
| `logs/` | 실행 기록과 대화 로그 |

## 이번 과제의 핵심

- 단순히 블로그 글 하나를 만든 것이 아니라, 뉴스 입력부터 결과 평가까지 반복 가능한 자동화 절차를 만들었다.
- 모델별 결과를 같은 기준으로 비교해 최종 결과물을 선정했다.
- 사실과 해석을 구분하고, 불확실한 정보는 확정 표현으로 쓰지 않도록 통제했다.
