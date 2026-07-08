# v1→v2 프롬프트 개선 증빙

## 비교 정의

- v1: 기사 입력 후 콘텐츠를 직접 생성한 초기 방식
- v2: v1 결과를 기반으로 사실 검토, 불확실성 표시, 구조 설계, HTML 표준화와 자체 검수를 추가한 개선 방식
- 모델과 기사: Claude Sonnet 5, 동일 Hermes Agent 기사

v2는 완전히 별개의 신규 주제가 아니라 v1 결과를 반복 검토하고 보완한 최종 방식이다.

## 결과 연결

| 구분 | 프롬프트 | 마크다운 결과 | HTML 결과 |
|---|---|---|---|
| v1 | `evaluation/prompt_iterations/hermes_agent/v1/prompt.md` | `evaluation/model_outputs/claude/article.md` | `evaluation/model_outputs/claude/index.html` |
| v2 | `evaluation/prompt_iterations/hermes_agent/v2/prompt.md` | `evaluation/model_outputs/claude/package.md` | `evaluation/model_outputs/claude/blog.html` |

위 결과 경로는 각 버전의 `result_manifest.md`에 고정되어 있다. 동일 파일을 v1·v2 폴더에 중복 복사하지 않고 매니페스트로 원본성과 경로를 관리한다.

## 주요 개선

| 항목 | v1 | v2 |
|---|---|---|
| 사실 검토 | 별도 섹션 없음 | 확인 필요 정보 분리 |
| 변동 수치 | 현재 사실처럼 사용 | 최신 공식 확인 필요 표시 |
| HTML | style 블록·외부 폰트 | 인라인 CSS |
| SEO meta | 없음 | 있음 |
| 이미지 연계 | 개별 주제 | 실패→메모리→비교 흐름 |
| 운영 구조 | 파일명 불일치 | 표준 결과와 메타데이터 연결 |

상세 점수와 실제 문장 근거:

`evaluation/prompt_iterations/hermes_agent/comparison_report.md`

