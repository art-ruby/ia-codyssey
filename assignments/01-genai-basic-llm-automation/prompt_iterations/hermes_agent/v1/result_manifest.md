# v1 결과 매니페스트

- 모델: Claude Sonnet 5
- 입력: `../../../test_inputs/hermes_agent/article_source.md`
- 마크다운 결과: `../../../model_outputs/claude/article.md`
- HTML 결과: `../../../model_outputs/claude/index.html`
- 이미지:
  - `../../../model_outputs/claude/image1.png`
  - `../../../model_outputs/claude/image2.png`
  - `../../../model_outputs/claude/image3.png`

## 관찰된 대표 문제

- GitHub 스타 72,000개를 현재 사실처럼 본문에 사용
- `$5 VPS` 운영과 MIT 라이선스를 확인 안내 없이 확정
- 별도 사실 확인 필요 섹션 없음
- `<style>` 블록과 외부 Google Fonts 사용
- 모델별 표준 파일명 미준수

