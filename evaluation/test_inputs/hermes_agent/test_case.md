# Hermes Agent 모델 평가 테스트 케이스

## 테스트 ID

`HERMES-BLOG-001`

## 목적

동일한 분석 기사 입력으로 세 모델이 사실성을 유지하면서 마크다운 콘텐츠 패키지와 게시 가능한 HTML을 생성하는지 평가한다.

## 공통 입력

- 기사: `article_source.md`
- 출처 목록: `source_manifest.md`
- 사실 판정 기준: `expected_facts.md`
- 형식 벤치마크: `../../benchmarks/format/naver_ninestonelee/format_benchmark.md`
- 콘텐츠 벤치마크: `../../benchmarks/content/hermes_agent_gpters/content_benchmark.md`

## 실험 A — 공정 비교

- 공통 프롬프트: `../../prompts/comparison/prompt_ai_news_content_package_common_v6_final.md`
- ChatGPT, Gemini, Claude에 동일한 프롬프트와 동일한 기사 입력 사용
- 추가 대화나 수동 수정 없이 첫 응답을 저장

## 실험 B — 실무 비교

- ChatGPT: `../../prompts/prompt_ai_news_content_package_chatgpt_v3.md`
- Gemini: `../../prompts/prompt_ai_news_content_package_gemini_v4.md`
- Claude: `../../prompts/prompt_ai_news_content_package_claude_v5.md`
- 모델별 최적화 프롬프트와 동일한 기사 입력 사용

## 필수 출력

- 원본 응답
- 마크다운 패키지
- 완결형 HTML
- 대표 이미지 프롬프트 3개
- alt 텍스트 3개
- Sora 2 12초 프롬프트
- 내레이션과 자막
- SEO meta 설명
- 해시태그 10개 이상

## 자동 검사

| 검사 | 합격 기준 |
|---|---|
| 출력 분리 | 마크다운과 HTML을 명확히 분리 |
| HTML 완결성 | doctype, html, head, body, 종료 태그 존재 |
| 이미지 | 이미지 위치 또는 실제 이미지 태그 3개 |
| alt 텍스트 | 서로 다른 alt 텍스트 3개 |
| 해시태그 | 10개 이상 |
| Sora | 12초, 9:16, 필수 스타일 문구 포함 |
| 마크다운 혼입 | HTML 내부에 마크다운 문법 없음 |
| CSS | 프로젝트 계약에 맞는 인라인 CSS |

## 수동 평가

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

## 결과 저장

```text
evaluation/model_outputs/hermes_agent/
├── common/
│   ├── chatgpt/
│   ├── gemini/
│   └── claude/
└── optimized/
    ├── chatgpt/
    ├── gemini/
    └── claude/
```

현재 루트의 결과는 다음과 같이 공통 v6 최종 비교 결과로 취급한다.

- `evaluation/model_outputs/chatgpt`: ChatGPT 5.5 중간, 공통 v6 Final
- `evaluation/model_outputs/gemini`: Gemini 3.1 Pro, 공통 v6 Final
- `evaluation/model_outputs/claude/package.md`, `blog.html`: Claude Sonnet 5 무료 시험, 공통 v6 Final

Claude의 `article.md`, `index.html`은 이전 v5 실행 결과이며 최종 공정 비교 점수에는 사용하지 않는다.
