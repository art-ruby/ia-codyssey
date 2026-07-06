# AI Tech News Blog Automation

뉴스기사 원문 또는 요약 1개를 기반으로 AI 테크 뉴스 블로그, 이미지 프롬프트,
Sora 숏츠 구성, HTML 및 SEO 결과물을 생성하는 자동화 프로젝트입니다.

## 주요 문서

- `PROJECT_RULES_v1.md`: 최상위 운영 기준
- `docs/00_project_overview_v1.md`: 프로젝트 개요
- `docs/01_requirements_spec_v1.md`: 요구사항
- `docs/04_generation_pipeline_v1.md`: 생성 파이프라인
- `docs/05_prompt_design_v1.md`: 프롬프트 설계
- `docs/06_model_comparison_plan_v1.md`: 모델 비교 계획
- `docs/07_html_template_spec_v1.md`: HTML 템플릿 기준
- `docs/09_risk_and_limitations_v1.md`: 리스크와 한계
- `docs/10_execution_log_v1.md`: 실행 로그 기준
- `docs/11_workflow_checklist_v1.md`: 운영 체크리스트
- `docs/12_manual_review_guide_v1.md`: 수동 검수 가이드
- `docs/13_posting_ready_criteria_v1.md`: 게시 승인 기준
- `docs/14_prompt_tuning_log_v1.md`: 프롬프트 튜닝 로그
- `docs/15_public_mission_summary_v1.md`: 공개용 맞춤 미션
- `docs/16_common_prompt_strategy_v1.md`: 공통 프롬프트 통합 전략
- `docs/17_mission_execution_plan_v1.md`: 미션 실행 계획

## 최종 통합 프롬프트

`prompts/prompt_blog_generation_v1.md`

입력값은 `{{NEWS_ARTICLE}}` 하나만 사용합니다. 프롬프트는 기사에서 주제와
핵심 관점을 자동 추출하고 제목, 썸네일, 대표 이미지, Sora 숏츠, 내레이션,
자막, HTML 본문, SEO 메타 설명과 해시태그를 한 번에 생성합니다.

## AI 뉴스 콘텐츠 패키지 프롬프트

- ChatGPT: `prompts/prompt_ai_news_content_package_chatgpt_v3.md`
- Gemini: `prompts/prompt_ai_news_content_package_gemini_v4.md`
- Claude: `prompts/prompt_ai_news_content_package_claude_v5.md`
- 이전 버전: `prompts/prompt_ai_news_content_package_v1.md`, `prompts/prompt_ai_news_content_package_v2.md`

세 모델별 프롬프트는 발전 과정과 모델별 출력 차이를 보존합니다. 공정한 모델
평가에는 별도의 공통 프롬프트를 사용하고, 모델별 프롬프트 결과와 구분합니다.

- 공통 비교 프롬프트: `prompts/comparison/prompt_ai_news_content_package_common_v6_final.md`

## 디렉터리

- `docs/`: 기준 및 운영 문서
- `prompts/`: 단계별 프롬프트
- `evaluation/`: 벤치마크, 공통 입력, 모델별 출력, 평가표, 보고서
- `templates/`: HTML/CSS 템플릿
- `data/`: 입력 및 중간 데이터
- `outputs/`: 생성 결과물
- `outputs/videos/`: 생성된 블로그 숏츠 영상
- `logs/`: 실행 및 변경 기록
