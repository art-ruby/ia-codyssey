# Hermes Agent 모델 출력 실행 조건

## 공통 입력

- 기사: `../test_inputs/hermes_agent/article_source.md`
- 주제: Hermes Agent 완벽 정리 — Hermes vs OpenClaw 비교

## 모델별 프롬프트

| 결과 폴더 | 사용 프롬프트 | 비교 상태 |
|---|---|---|
| `chatgpt/` | `../../prompts/comparison/prompt_ai_news_content_package_common_v6_final.md` | ChatGPT 5.5, 중간, Pro, 웹 |
| `gemini/` | `../../prompts/comparison/prompt_ai_news_content_package_common_v6_final.md` | Gemini 3.1 Pro, Pro, 웹 |
| `claude/` | `../../prompts/comparison/prompt_ai_news_content_package_common_v6_final.md` | Claude Sonnet 5, 무료 시험, 웹 |

## 현재 판정

- 세 모델 모두 동일 기사와 공통 v6 Final로 실행한 결과를 확보했다.
- Claude의 `article.md`와 `index.html`은 이전 v5 결과로 보존한다.
- Claude의 공통 v6 결과는 `package.md`와 `blog.html`이다.
- 현재 세 모델 결과를 최종 공정 비교에 사용한다.

## 공통 실행 정보

- 실행 날짜: 2026-07-06
- 정확한 실행 시각: 기록 없음
- 주요 설정: 별도 설정 없음
- 응답 생성 시간: 미측정
- 무료 버전 제한: Claude 프로젝트 기능을 이용한 작업에 제한이 있음
