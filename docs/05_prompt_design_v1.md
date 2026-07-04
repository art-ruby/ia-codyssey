## 6.12 영상 프롬프트 생성 프롬프트

### 목적
쇼츠 또는 짧은 영상 제작용 콘셉트 프롬프트를 만든다.

### 출력 형식
단일 프롬프트

### 프롬프트 예시
```text
너는 짧은 영상 콘셉트 기획자다.

주어진 블로그 주제를 바탕으로 30~45초 길이의 짧은 영상 제작용 프롬프트 1개를 작성하라.

작성 규칙:
1. 영상은 뉴스 브리핑 + 비교 분석 톤으로 구성한다.
2. 첫 3초 안에 시선을 끌 수 있는 오프닝 장면을 포함한다.
3. OpenAI와 Google의 경쟁 구도가 드러나야 한다.
4. 장면 흐름이 순서대로 보이도록 작성한다.
5. 자막용 핵심 문구 3개를 함께 제안한다.
6. 과장되거나 선정적인 연출은 피한다.

입력:
- 주제: {topic}
- 핵심 메시지: {main_message}
- 핵심 뉴스: {selected_news_summary}

출력 형식:
[영상 프롬프트]
...

[자막 핵심 문구]
1. ...
2. ...
3. ...
```

---

## 6.13 HTML 변환 프롬프트

### 목적
생성된 블로그 콘텐츠를 티스토리 업로드용 HTML로 변환한다.

### 입력
- 제목
- 메타 설명
- 3줄 요약
- 본문
- 비교 표
- 강조 문장

### 출력 형식
HTML

### 프롬프트 예시
```text
너는 티스토리용 HTML 블로그 편집자다.

주어진 블로그 콘텐츠를 가독성 좋은 HTML 구조로 변환하라.

작성 규칙:
1. HTML만 출력한다.
2. h1, h2, p, ul, li, table, div 등 기본 태그 중심으로 작성한다.
3. 티스토리 편집기에서 깨질 수 있는 복잡한 스크립트나 외부 의존성은 사용하지 않는다.
4. 3줄 요약은 summary-box 형태의 div로 감싼다.
5. 핵심 문장은 highlight-box 형태의 div로 강조한다.
6. 비교 표는 table 태그로 구성한다.
7. 문단 간 가독성이 좋도록 구조를 단순하게 유지한다.

스타일 가이드:
- 강조색: #FF6B6B
- 배경색: #E8F5F0
- 박스색: #E3F2FD
- 테두리: #4A90E2

입력:
- 제목: {title}
- 메타 설명: {meta_description}
- 3줄 요약: {three_line_summary}
- 본문: {body_markdown_or_text}
- 비교 표: {comparison_table}
- 강조 문장: {highlight_sentence}

출력 형식:
HTML 전체만 출력
```

---

## 6.14 최종 패키지 조합 프롬프트

### 목적
개별 산출물을 하나의 최종 결과 묶음으로 정리한다.

### 출력 형식
구조화된 Markdown 또는 JSON

### 프롬프트 예시
```text
너는 최종 산출물 편집자다.

주어진 결과 조각들을 하나의 게시용 패키지로 정리하라.

작성 규칙:
1. 제목, 메타 설명, 3줄 요약, 본문, 비교 표, 해시태그, 이미지 프롬프트, 영상 프롬프트, HTML 결과를 빠짐없이 포함한다.
2. 각 항목은 구분이 잘 되도록 섹션 제목을 붙인다.
3. 누락 항목이 있으면 "확인 필요"로 표시한다.
4. 출력 형식을 일관되게 유지한다.

입력:
- 제목 목록: {titles}
- 메타 설명: {meta_description}
- 3줄 요약: {three_line_summary}
- 본문: {body}
- 비교 표: {comparison_table}
- 해시태그: {hashtags}
- 이미지 프롬프트: {image_prompts}
- 영상 프롬프트: {video_prompt}
- HTML: {html_output}

출력 형식:
## 제목 후보
...
## 메타 설명
...
## 3줄 요약
...
```

---

## 7. 프롬프트 변수 설계 규칙

프롬프트 안에 들어가는 동적 값은 일관된 변수명으로 관리한다.

### 7.1 권장 변수명
- `{keyword}`: 검색어
- `{topic}`: 주제
- `{purpose}`: 작성 목적
- `{audience}`: 타겟 독자
- `{tone}`: 작성 톤
- `{platform}`: 출력 플랫폼
- `{date_range}`: 뉴스 검색 기간
- `{preferred_sources}`: 우선 출처 목록
- `{news_items}`: 뉴스 후보 배열
- `{normalized_news_json}`: 정규화된 뉴스 JSON
- `{selected_news_json}`: 선별된 핵심 뉴스 JSON
- `{selected_news_summary}`: 핵심 뉴스 요약 텍스트
- `{comparison_points}`: 비교 포인트 배열
- `{main_message}`: 블로그 핵심 메시지
- `{title}`: 최종 제목
- `{meta_description}`: 메타 설명
- `{three_line_summary}`: 3줄 요약
- `{body_markdown_or_text}`: 본문
- `{comparison_table}`: 비교 표
- `{highlight_sentence}`: 강조 문장
- `{keywords}`: 해시태그용 키워드 목록

### 7.2 변수 설계 원칙
1. 변수명은 의미가 명확해야 한다.
2. 한 프롬프트 안에서 같은 뜻의 변수명을 여러 개 쓰지 않는다.
3. JSON 전체를 넣는지, 요약 텍스트를 넣는지 구분한다.
4. 모델 비교 시 같은 변수 구조를 유지한다.

---

## 8. 프롬프트 작성 시 금지사항

### 8.1 모호한 지시 금지
예:
- “좋게 써줘”
- “알아서 정리해줘”
- “대충 예쁘게 만들어줘”

이런 표현은 결과 편차를 키운다.

### 8.2 한 프롬프트에 과도한 작업 몰아넣기 금지
예:
- 뉴스 수집
- 기사 선별
- 본문 작성
- HTML 변환
을 한 번에 시키지 않는다.

### 8.3 출력 형식 생략 금지
형식을 지정하지 않으면 모델마다 결과 차이가 커진다.

### 8.4 근거 없는 사실 생성 유도 금지
예:
- “비어 있는 내용은 적당히 채워라”
- “가능한 사실적으로 추정해라”

이런 문장은 환각 가능성을 높인다.

### 8.5 비교 강요 금지
실제 입력 데이터에 비교 가능한 근거가 없으면 억지 비교를 만들지 않는다.

---

## 9. 품질 향상을 위한 프롬프트 보강 기법

### 9.1 출력 형식 강제
- “JSON만 출력”
- “Markdown 본문만 출력”
- “설명 없이 HTML만 출력”

이처럼 출력 형식을 강하게 제한한다.

### 9.2 길이 제한
예:
- “2문장 이내”
- “최대 5개”
- “120~160자 내외”

길이 제한은 응답 일관성을 높인다.

### 9.3 평가 기준 내장
프롬프트 안에 “최신성, 관련성, 영향도 고려” 같은 평가 기준을 넣는다.

### 9.4 금지사항 명시
하지 말아야 할 행동을 분명히 써야 결과 품질이 안정된다.

### 9.5 중간 산출물 분리
최종 결과만 받지 말고, 선별 결과나 비교 포인트 같은 중간 산출물을 따로 받는다.

---

## 10. 모델 비교를 위한 프롬프트 고정 규칙

GPT / Claude / Gemini 비교 시 아래 항목은 최대한 동일하게 유지한다.

1. 역할 정의
2. 작업 목표
3. 입력 데이터
4. 출력 형식
5. 평가 기준
6. 금지사항
7. 동일 뉴스 입력 데이터
8. 동일 비교 포인트 요구사항

### 주의
모델마다 문장 스타일 차이는 허용하되, 작업 조건이 달라지면 공정 비교가 어려워진다.

---

## 11. 프롬프트 테스트 체크리스트

각 프롬프트는 아래 항목으로 테스트한다.

| 항목 | 확인 내용 |
|------|-----------|
| 역할 명확성 | 모델이 어떤 역할인지 분명한가 |
| 목표 명확성 | 정확히 무엇을 해야 하는지 보이는가 |
| 입력 충분성 | 작업에 필요한 데이터가 모두 들어있는가 |
| 출력 고정성 | 원하는 형식으로 안정적으로 나오는가 |
| 금지사항 명시 | 하면 안 되는 행동이 적혀 있는가 |
| 재사용성 | 다른 키워드에도 적용 가능한가 |
| 비교 가능성 | 모델 비교에 쓸 수 있을 정도로 고정되어 있는가 |

---

## 12. 프롬프트 운영 전략

### 12.1 초안 프롬프트와 운영 프롬프트 분리
- 초안 프롬프트: 실험용
- 운영 프롬프트: 검증 후 고정본

### 12.2 버전 관리
프롬프트는 수정될 때마다 버전을 관리한다.

예:
- `prompt_news_collect_v1.md`
- `prompt_news_collect_v2.md`

### 12.3 실패 로그 기록
프롬프트가 원하는 결과를 내지 못한 경우 원인을 기록한다.

예:
- 출력 형식 불안정
- 기사 중복 제거 실패
- 본문이 기사 나열형으로 생성됨

### 12.4 점진적 개선
처음부터 완벽한 프롬프트를 만들기보다, 실행 로그를 바탕으로 개선한다.

---

## 13. 권장 프롬프트 파일 구조

### 공통 프롬프트
- `prompts/common/system_policy_v1.md`

### 단계별 프롬프트
- `prompts/pipeline/step_01_input_structuring_v1.md`
- `prompts/pipeline/step_02_news_collection_v1.md`
- `prompts/pipeline/step_03_news_normalization_v1.md`
- `prompts/pipeline/step_04_news_selection_v1.md`
- `prompts/pipeline/step_05_title_generation_v1.md`
- `prompts/pipeline/step_06_meta_description_v1.md`
- `prompts/pipeline/step_07_summary_generation_v1.md`
- `prompts/pipeline/step_08_body_generation_v1.md`
- `prompts/pipeline/step_09_comparison_table_v1.md`
- `prompts/pipeline/step_10_hashtag_generation_v1.md`
- `prompts/pipeline/step_11_image_prompt_generation_v1.md`
- `prompts/pipeline/step_12_video_prompt_generation_v1.md`
- `prompts/pipeline/step_13_html_rendering_v1.md`

### 실험용 프롬프트
- `prompts/experiments/`

---

## 14. 다른 문서와의 연결

이 문서는 아래 문서와 연결된다.

- `PROJECT_RULES_v1.md`
- `docs/01_requirements_spec_v1.md`
- `docs/04_generation_pipeline_v1.md`
- `docs/06_model_comparison_plan_v1.md`
- `docs/07_html_template_spec_v1.md`

연결 관계는 다음과 같다.

- `01_requirements_spec_v1.md`: 무엇을 출력해야 하는지 정의
- `04_generation_pipeline_v1.md`: 어떤 순서로 생성할지 정의
- `05_prompt_design_v1.md`: 각 단계에서 어떻게 지시할지 정의
- `06_model_comparison_plan_v1.md`: 프롬프트를 어떤 기준으로 비교할지 정의
- `07_html_template_spec_v1.md`: HTML 출력 상세 구조 정의

---

## 15. 현재 버전의 한계

이 문서는 프롬프트 설계 초안이므로 아래 항목은 후속 보완이 필요하다.

- 실제 모델별 응답 차이 분석
- 프롬프트 길이에 따른 성능 차이 검증
- JSON 안정 출력 실패 대응 전략
- 단계 병합/분리 최적화
- 자동 평가 프롬프트 설계

---

## 16. 문서 수정 이력
- v1: 프롬프트 설계 기준 문서 초안 작성
