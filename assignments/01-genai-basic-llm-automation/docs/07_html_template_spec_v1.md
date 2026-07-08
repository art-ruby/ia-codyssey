# 07_html_template_spec_v1.md

## 1. 문서 목적
이 문서는 **AI 테크 뉴스 블로그 자동화 프로젝트의 HTML 출력 템플릿 기준 문서**이다.  
생성된 제목, 요약, 본문, 비교 표, 해시태그 등을 티스토리 업로드용 HTML로 일관되게 변환하기 위한 구조와 스타일 기준을 정의한다.

이 문서의 목적은 다음과 같다.

- 티스토리 편집기에 바로 붙여넣기 가능한 HTML 구조를 표준화한다.
- 블로그 글의 가독성과 일관성을 유지한다.
- AI가 생성한 본문을 안정적으로 HTML로 렌더링하는 기준을 만든다.
- 모델별 HTML 출력 결과를 비교할 때 기준 템플릿으로 활용한다.

---

## 2. 적용 범위

이 문서는 아래 산출물에 적용된다.

- 블로그 본문 HTML
- 요약 박스 HTML
- 강조 박스 HTML
- 비교 표 HTML
- 소제목 구조
- 마무리 문단 구조

아래 항목은 현재 범위에서 제외한다.

- 티스토리 스킨 전체 수정
- 외부 JavaScript 삽입
- 동적 UI 컴포넌트
- 광고 코드 삽입
- 댓글/공유 버튼 커스텀 코드

---

## 3. HTML 설계 원칙

### 3.1 단순 구조 원칙
티스토리 편집기에서 깨질 가능성을 줄이기 위해 복잡한 중첩 구조를 피한다.

### 3.2 가독성 우선 원칙
화려한 효과보다 제목, 문단, 요약 박스, 표가 읽기 쉬운 구조를 우선한다.

### 3.3 붙여넣기 안정성 원칙
외부 CSS/JS 의존 없이 인라인 스타일 또는 최소 구조로 동작해야 한다.

### 3.4 재사용성 원칙
같은 주제뿐 아니라 다른 AI/IT 뉴스 글에도 그대로 적용 가능해야 한다.

### 3.5 섹션 일관성 원칙
각 글은 가능한 한 같은 구조를 유지하여 자동화 품질을 높인다.

---

## 4. 기본 문서 구조

최종 HTML은 기본적으로 아래 순서를 따른다.

1. 제목
2. 메타성 리드 문단
3. 3줄 요약 박스
4. 도입
5. 핵심 뉴스 요약 섹션
6. 기업별 동향 섹션
7. 비교 표 섹션
8. 실무적 의미 섹션
9. 결론
10. 해시태그 또는 마무리 정보

### 권장 구조 예시
```html
<h1>제목</h1>
<p>리드 문단</p>

<div class="summary-box">
  <ul>
    <li>요약 1</li>
    <li>요약 2</li>
    <li>요약 3</li>
  </ul>
</div>

<h2>왜 이 이슈가 중요한가</h2>
<p>...</p>

<h2>최신 뉴스 핵심 요약</h2>
<p>...</p>

<h2>OpenAI 동향</h2>
<p>...</p>

<h2>Google 동향</h2>
<p>...</p>

<h2>한눈에 보는 비교</h2>
<table>...</table>

<div class="highlight-box">
  핵심 문장
</div>

<h2>실무적으로 보면</h2>
<p>...</p>

<h2>마무리</h2>
<p>...</p>
```

---

## 5. 필수 HTML 구성 요소

## 5.1 제목 영역

### 목적
글의 핵심 주제를 즉시 보여준다.

### 규칙
- `h1` 태그 사용
- 제목은 문서 내 1회만 사용
- 과도한 장식 태그 사용 금지

### 예시
```html
<h1>OpenAI와 Google, 생성형 AI 경쟁은 어디로 가고 있나</h1>
```

---

## 5.2 리드 문단

### 목적
독자가 글 전체 맥락을 빠르게 이해하도록 돕는다.

### 규칙
- 제목 직후 `p` 태그로 배치
- 2~4문장 권장
- 글의 주제, 비교 관점, 독자 기대값 포함

### 예시
```html
<p>최근 생성형 AI 시장에서는 OpenAI와 Google의 경쟁이 더욱 분명해지고 있습니다. 
이번 글에서는 최신 뉴스 흐름을 바탕으로 두 기업이 어떤 방향으로 움직이고 있는지, 그리고 이 경쟁이 실제 사용자와 실무 환경에 어떤 의미를 갖는지 정리해보겠습니다.</p>
```

---

## 5.3 3줄 요약 박스

### 목적
본문을 읽기 전에 핵심 내용을 빠르게 전달한다.

### 규칙
- `div` + `ul` 구조 사용
- 요약은 3개 불릿 고정 권장
- 박스 스타일은 눈에 띄되 과하지 않게 유지

### 권장 클래스명
- `summary-box`

### 예시
```html
<div class="summary-box" style="background:#E8F5F0; border:1px solid #4A90E2; padding:16px; margin:20px 0;">
  <strong>핵심 요약</strong>
  <ul>
    <li>OpenAI와 Google 모두 생성형 AI 경쟁을 빠르게 확장하고 있습니다.</li>
    <li>차이는 제품 전략, 생태계 연결 방식, 사용자 접점에서 드러납니다.</li>
    <li>실무적으로는 어떤 서비스가 더 잘 연결되고 활용되는지가 중요해지고 있습니다.</li>
  </ul>
</div>
```

---

## 5.4 소제목 섹션

### 목적
본문 흐름을 구분하고 스캔 읽기를 쉽게 만든다.

### 규칙
- 주요 섹션은 `h2`
- 필요 시 하위 섹션은 `h3`
- 제목 길이는 너무 길지 않게 유지
- 물음형/설명형 혼합 가능

### 권장 섹션명
- 왜 이 이슈가 중요한가
- 최신 뉴스 핵심 요약
- OpenAI 동향
- Google 동향
- 한눈에 보는 비교
- 실무적으로 보면
- 마무리

---

## 5.5 일반 본문 문단

### 목적
핵심 정보와 해설을 자연스럽게 전달한다.

### 규칙
- `p` 태그 사용
- 문단 하나당 2~4문장 권장
- 지나치게 긴 문단은 분리
- 기사 나열형보다 해설형 문장 우선

### 예시
```html
<p>이번 경쟁에서 중요한 점은 단순히 누가 더 강한 모델을 내놓았느냐가 아닙니다. 
실제로는 어떤 서비스 안에 AI 기능을 더 자연스럽게 녹여내고, 사용자가 더 자주 쓰게 만드느냐가 핵심 경쟁력으로 작동하고 있습니다.</p>
```

---

## 5.6 강조 박스

### 목적
독자가 꼭 기억해야 할 핵심 문장을 시각적으로 강조한다.

### 규칙
- `div` 사용
- 문장 1~2개 권장
- 본문 중간 또는 비교 표 아래 배치 가능

### 권장 클래스명
- `highlight-box`

### 예시
```html
<div class="highlight-box" style="background:#E3F2FD; border-left:6px solid #FF6B6B; padding:16px; margin:24px 0; font-weight:600;">
  지금의 생성형 AI 경쟁은 모델 성능 자체보다, 사용자의 실제 업무와 생활에 얼마나 자연스럽게 연결되느냐로 이동하고 있습니다.
</div>
```

---

## 5.7 비교 표

### 목적
기업 간 차이를 한눈에 비교한다.

### 규칙
- `table` 태그 사용
- 열 수는 3개 고정 권장: 비교 항목 / OpenAI / Google
- 행 수는 4~6개 권장
- 셀 내용은 짧고 명확하게 작성
- 우열 단정보다 차이 설명 중심

### 예시
```html
<table style="width:100%; border-collapse:collapse; margin:20px 0;">
  <thead>
    <tr>
      <th style="border:1px solid #cccccc; padding:10px; background:#f5f5f5;">비교 항목</th>
      <th style="border:1px solid #cccccc; padding:10px; background:#f5f5f5;">OpenAI</th>
      <th style="border:1px solid #cccccc; padding:10px; background:#f5f5f5;">Google</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="border:1px solid #cccccc; padding:10px;">제품 확장 방식</td>
      <td style="border:1px solid #cccccc; padding:10px;">대화형 서비스 중심 확장</td>
      <td style="border:1px solid #cccccc; padding:10px;">검색·업무도구와의 연결 강화</td>
    </tr>
    <tr>
      <td style="border:1px solid #cccccc; padding:10px;">사용자 접점</td>
      <td style="border:1px solid #cccccc; padding:10px;">직접 사용 경험 강조</td>
      <td style="border:1px solid #cccccc; padding:10px;">기존 서비스 안으로 통합</td>
    </tr>
  </tbody>
</table>
```

---

## 5.8 목록형 정리 섹션

### 목적
포인트를 짧게 정리할 때 사용한다.

### 규칙
- `ul`, `ol`, `li` 사용
- 항목 수는 3~5개 권장
- 한 항목이 너무 길어지지 않게 유지

### 예시
```html
<h2>이 글에서 주목할 포인트</h2>
<ul>
  <li>두 기업의 경쟁은 기능 자체보다 생태계 연결 방식에서 차이가 납니다.</li>
  <li>최신 뉴스는 단기 발표보다 장기 전략을 함께 봐야 이해가 쉽습니다.</li>
  <li>실무 사용자에게는 도구 통합성과 접근성이 더 중요할 수 있습니다.</li>
</ul>
```

---

## 5.9 결론 섹션

### 목적
글의 핵심 메시지를 다시 정리하고 독자의 이해를 마무리한다.

### 규칙
- `h2` + `p` 구조
- 핵심 메시지 재정리
- 과도한 예언형 문장 금지
- “앞으로 지켜볼 점” 정도의 마무리 허용

### 예시
```html
<h2>마무리</h2>
<p>OpenAI와 Google의 생성형 AI 경쟁은 단순한 기술 대결이 아니라, 사용자의 실제 선택을 둘러싼 플랫폼 경쟁으로 확장되고 있습니다. 
앞으로는 새로운 모델 발표 자체보다, 그 기능이 어떤 제품 안에서 얼마나 자주 활용되는지가 더 중요한 판단 기준이 될 가능성이 큽니다.</p>
```

---

## 6. 권장 스타일 가이드

현재 프로젝트의 기본 스타일은 아래 값을 권장한다.

### 6.1 컬러
- 메인 강조색: `#FF6B6B`
- 보조 배경색: `#E8F5F0`
- 정보 박스색: `#E3F2FD`
- 테두리색: `#4A90E2`
- 기본 텍스트색: `#222222`
- 보조 텍스트색: `#666666`

### 6.2 여백
- 섹션 상하 마진: `20px ~ 28px`
- 박스 패딩: `14px ~ 18px`
- 표 셀 패딩: `8px ~ 12px`

### 6.3 글자 강조
- 굵게: 핵심어, 결론 문장
- 밑줄: 되도록 사용 자제
- 색상 강조: 문장 전체보다 핵심 구절 위주

---

## 7. HTML 생성 규칙

AI가 HTML을 생성할 때는 아래 규칙을 반드시 따른다.

### 7.1 출력 형식 규칙
1. HTML만 출력한다.
2. 코드펜스 없이 순수 HTML만 반환하는 것을 기본값으로 한다.
3. 설명 문장, 주석, 메모를 HTML 밖에 덧붙이지 않는다.

### 7.2 구조 규칙
1. `h1`은 1회만 사용한다.
2. 주요 섹션은 `h2` 중심으로 구성한다.
3. 문단은 `p` 태그로 구분한다.
4. 표는 `table`, `thead`, `tbody`, `tr`, `th`, `td`를 사용한다.
5. 요약/강조 영역은 `div`로 감싼다.

### 7.3 호환성 규칙
1. 외부 CSS 링크 사용 금지
2. 외부 JS 사용 금지
3. iframe, script, form 사용 금지
4. 복잡한 class 체계보다 단순 구조 우선
5. 인라인 스타일 사용은 허용하되 최소화

---

## 8. 금지사항

### 8.1 과도한 장식 금지
- 불필요한 이모지 남용
- 과한 색상 혼합
- 과도한 폰트 크기 변화

### 8.2 복잡한 HTML 금지
- 깊은 중첩 div 구조
- CSS Grid/Flex에 지나치게 의존하는 구조
- 티스토리에서 깨질 가능성이 큰 커스텀 코드

### 8.3 의미 없는 태그 금지
- 시각적 목적만 있는 빈 태그
- 구조 없이 줄바꿈만 반복하는 코드
- `<br><br><br>` 식의 과도한 사용

### 8.4 불안정한 표 구조 금지
- 행/열 불일치
- `th`, `td` 개수 불일치
- 지나치게 긴 셀 텍스트

---

## 9. 티스토리 업로드 기준

### 9.1 붙여넣기 기준
- HTML 모드에서 바로 붙여넣기 가능해야 한다.
- 외부 의존 없이 레이아웃이 유지되어야 한다.
- 본문 중 깨지는 태그가 없어야 한다.

### 9.2 실무 사용 기준
- 사람이 약간만 수정해도 게시 가능해야 한다.
- 비교 표와 요약 박스가 눈에 잘 들어와야 한다.
- 모바일에서도 지나치게 답답하지 않아야 한다.

### 9.3 최소 검수 항목
1. 제목이 `h1`인지 확인
2. 요약 박스가 있는지 확인
3. 표가 정상 닫힘 태그로 끝나는지 확인
4. 문단 구분이 과도하게 붙어 있지 않은지 확인
5. HTML 외 텍스트가 섞이지 않았는지 확인

---

## 10. 권장 HTML 템플릿 골격

아래는 운영용으로 재사용 가능한 기본 템플릿이다.

```html
<h1>{title}</h1>

<p>{lead_paragraph}</p>

<div class="summary-box" style="background:#E8F5F0; border:1px solid #4A90E2; padding:16px; margin:20px 0;">
  <strong>핵심 요약</strong>
  <ul>
    <li>{summary_1}</li>
    <li>{summary_2}</li>
    <li>{summary_3}</li>
  </ul>
</div>

<h2>왜 이 이슈가 중요한가</h2>
<p>{importance_paragraph}</p>

<h2>최신 뉴스 핵심 요약</h2>
<p>{news_summary_paragraph}</p>

<h2>OpenAI 동향</h2>
<p>{openai_paragraph}</p>

<h2>Google 동향</h2>
<p>{google_paragraph}</p>

<h2>한눈에 보는 비교</h2>
{comparison_table_html}

<div class="highlight-box" style="background:#E3F2FD; border-left:6px solid #FF6B6B; padding:16px; margin:24px 0; font-weight:600;">
  {highlight_sentence}
</div>

<h2>실무적으로 보면</h2>
<p>{practical_meaning_paragraph}</p>

<h2>마무리</h2>
<p>{closing_paragraph}</p>

<p>{hashtags_line}</p>
```

---

## 11. HTML 템플릿 변수 정의

### 필수 변수
- `{title}`: 최종 제목
- `{lead_paragraph}`: 도입 문단
- `{summary_1}`: 3줄 요약 1
- `{summary_2}`: 3줄 요약 2
- `{summary_3}`: 3줄 요약 3
- `{importance_paragraph}`: 중요성 설명 문단
- `{news_summary_paragraph}`: 최신 뉴스 묶음 요약
- `{openai_paragraph}`: OpenAI 관련 본문
- `{google_paragraph}`: Google 관련 본문
- `{comparison_table_html}`: 비교 표 HTML
- `{highlight_sentence}`: 강조 문장
- `{practical_meaning_paragraph}`: 실무적 의미 설명
- `{closing_paragraph}`: 결론 문단
- `{hashtags_line}`: 해시태그 한 줄

### 선택 변수
- `{sub_heading_note}`: 소제목 아래 짧은 설명 문구
- `{additional_points_list}`: 추가 포인트 목록 HTML
- `{related_tools_paragraph}`: 관련 서비스/도구 설명 문단
- `{future_watchpoint_paragraph}`: 앞으로 볼 포인트 문단
- `{source_note}`: 출처 또는 참고 메모
- `{cta_paragraph}`: 다음 글 유도 또는 독자 안내 문단

### 변수 사용 원칙
1. 필수 변수는 누락 없이 채운다.
2. 선택 변수는 필요할 때만 추가한다.
3. 값이 비어 있으면 빈 태그를 출력하지 않는다.
4. 변수명은 다른 문서와 동일한 의미 체계를 유지한다.
5. HTML 조립 전 텍스트/HTML 변수 여부를 구분한다.

---

## 12. 컴포넌트 조립 규칙

HTML은 하나의 긴 본문처럼 생성하기보다, 컴포넌트 단위로 나누어 조립하는 것을 권장한다.

### 12.1 권장 컴포넌트 단위
- title_block
- lead_block
- summary_box
- section_importance
- section_news_summary
- section_openai
- section_google
- comparison_table
- highlight_box
- section_practical
- closing_block
- hashtag_block

### 12.2 조립 원칙
1. 각 컴포넌트는 독립적으로 검수 가능해야 한다.
2. 표와 박스는 일반 문단과 분리해 관리한다.
3. 본문 생성과 HTML 렌더링 단계를 분리한다.
4. HTML 조립 시 닫힘 태그 누락 여부를 반드시 확인한다.

### 12.3 조립 예시
```text
title_block
+ lead_block
+ summary_box
+ section_importance
+ section_news_summary
+ section_openai
+ section_google
+ comparison_table
+ highlight_box
+ section_practical
+ closing_block
+ hashtag_block
= final_html
```

---

## 13. 본문 → HTML 매핑 규칙

생성된 텍스트 본문을 HTML로 바꿀 때는 아래 기준을 따른다.

### 13.1 제목 매핑
- 최종 제목 → `<h1>`

### 13.2 요약 매핑
- 3줄 요약 배열 → `summary-box` 내부 `<ul><li>`

### 13.3 본문 섹션 매핑
- 섹션 제목 → `<h2>`
- 섹션 본문 → `<p>`

### 13.4 비교 데이터 매핑
- 비교 항목 배열/표 데이터 → `<table>`

### 13.5 핵심 문장 매핑
- 강조 문장 → `highlight-box`

### 13.6 해시태그 매핑
- 해시태그 목록 → 마지막 `<p>` 또는 별도 `<div>`

---

## 14. 표 생성 세부 규칙

비교 표는 이 프로젝트의 핵심 구성 요소이므로 별도 규칙을 둔다.

### 14.1 기본 열 구조
기본적으로 아래 3열 구조를 사용한다.

- 비교 항목
- OpenAI
- Google

### 14.2 권장 행 항목
아래 항목 중 4~6개를 선택한다.

- 제품 전략
- 사용자 접점
- 생태계 연결
- 기술 방향
- 수익화 가능성
- 실무 활용성

### 14.3 표 작성 원칙
1. 한 셀은 가능하면 1문장 또는 짧은 구로 제한한다.
2. 감정적 우열 표현보다 차이 설명을 우선한다.
3. 같은 톤과 밀도로 작성한다.
4. 기사에 없는 과장 해석은 넣지 않는다.

### 14.4 표 데이터 예시
```html
<table style="width:100%; border-collapse:collapse; margin:20px 0;">
  <thead>
    <tr>
      <th style="border:1px solid #cccccc; padding:10px; background:#f5f5f5;">비교 항목</th>
      <th style="border:1px solid #cccccc; padding:10px; background:#f5f5f5;">OpenAI</th>
      <th style="border:1px solid #cccccc; padding:10px; background:#f5f5f5;">Google</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="border:1px solid #cccccc; padding:10px;">생태계 연결</td>
      <td style="border:1px solid #cccccc; padding:10px;">독립 서비스 경험 강화</td>
      <td style="border:1px solid #cccccc; padding:10px;">기존 제품군 내 통합 강화</td>
    </tr>
    <tr>
      <td style="border:1px solid #cccccc; padding:10px;">실무 활용 접근</td>
      <td style="border:1px solid #cccccc; padding:10px;">대화형 인터페이스 중심</td>
      <td style="border:1px solid #cccccc; padding:10px;">업무도구 결합 중심</td>
    </tr>
  </tbody>
</table>
```

---

## 15. 요약 박스/강조 박스 운영 규칙

### 15.1 요약 박스 운영 규칙
1. 항상 글 상단에 배치한다.
2. 3개 불릿을 기본값으로 한다.
3. 문장 길이는 짧고 명확하게 유지한다.
4. 본문 전체를 반복하지 말고 핵심만 압축한다.

### 15.2 강조 박스 운영 규칙
1. 글에서 가장 중요한 해석 문장을 담는다.
2. 1개만 사용하는 것을 기본값으로 한다.
3. 비교 표 바로 아래 또는 결론 직전에 배치한다.
4. 과장형 문장보다 해설형 문장을 우선한다.

---

## 16. 해시태그 출력 규칙

### 목적
게시 후 검색 노출 및 주제 묶음 정리에 활용한다.

### 규칙
1. 해시태그는 5~10개 권장
2. 너무 일반적인 태그만 반복하지 않는다.
3. 주제, 기업명, 기술 키워드가 균형 있게 포함되도록 한다.
4. HTML에서는 한 줄 문단으로 출력 가능하다.

### 예시
```html
<p>#OpenAI #GoogleAI #GenerativeAI #AI뉴스 #AI비교 #ChatGPT #Gemini #AI트렌드</p>
```

---

## 17. 모바일 가독성 고려사항

티스토리 유입은 모바일 비중이 높을 수 있으므로 아래 사항을 고려한다.

### 17.1 문단 길이
- 한 문단이 너무 길지 않도록 유지한다.
- 모바일에서 3~4줄 이상 길어지면 분리 검토한다.

### 17.2 표 사용
- 표는 꼭 필요한 정보만 넣는다.
- 셀 내용이 너무 길면 모바일에서 답답해질 수 있으므로 축약한다.

### 17.3 박스 사용
- 요약 박스/강조 박스는 유용하지만 과도하게 많으면 모바일에서 피로하다.
- 기본적으로 각 1개 사용을 권장한다.

### 17.4 시각적 밀도
- 제목, 문단, 표, 박스의 간격이 적절히 분리되어야 한다.
- 한 화면에 요소가 과도하게 몰리지 않게 한다.

---

## 18. 자동 검수 체크리스트

HTML 결과는 아래 항목으로 자동 또는 수동 검수한다.

| 항목 | 확인 내용 |
|------|-----------|
| 제목 존재 | `h1`이 1회 존재하는가 |
| 요약 박스 존재 | `summary-box`가 포함되어 있는가 |
| 본문 구조 | 주요 섹션이 `h2`로 구분되어 있는가 |
| 문단 구조 | 설명 본문이 `p` 태그로 정리되어 있는가 |
| 표 존재 | 비교 표가 정상 생성되었는가 |
| 태그 닫힘 | table/div/p 등 닫힘 태그 누락이 없는가 |
| HTML 순도 | HTML 외 설명 문장이 섞이지 않았는가 |
| 해시태그 출력 | 마지막 부분에 해시태그가 포함되었는가 |
| 과장 표현 점검 | 선정적/과장형 문구가 과도하지 않은가 |

---

## 19. HTML 생성 실패 유형

운영 중 자주 발생할 수 있는 실패 유형을 미리 정의한다.

### 19.1 형식 이탈
- HTML 외 설명 문장 출력
- 코드블록 감싸기
- Markdown과 HTML 혼합 출력

### 19.2 구조 누락
- `h1` 누락
- 비교 표 누락
- 요약 박스 누락

### 19.3 태그 오류
- 닫히지 않은 `div`
- `tr`, `td` 개수 불일치
- 잘못 중첩된 태그 구조

### 19.4 내용 문제
- 본문보다 요약이 더 길어짐
- 표 셀 내용이 지나치게 장문
- 과장형 결론 삽입

### 19.5 티스토리 비호환
- 외부 스크립트 사용
- 불필요한 스타일 남용
- 복잡한 레이아웃 의존

---

## 20. 실패 대응 원칙

### 20.1 형식 오류 시
HTML 렌더링 프롬프트를 다시 실행하되,  
“HTML만 출력”, “설명 금지”, “코드블록 금지”를 더 강하게 명시한다.

### 20.2 표 오류 시
표는 본문 생성 단계와 분리하여 별도 프롬프트로 재생성한다.

### 20.3 내용 과장 시
강조 문장과 결론 문단만 별도 수정 대상으로 분리한다.

### 20.4 길이 과다 시
문단당 문장 수 제한, 표 셀 글자 수 제한을 추가한다.

---

## 21. 프롬프트 연동 기준

이 문서는 `05_prompt_design_v1.md` 의 HTML 변환 프롬프트와 직접 연결된다.

### HTML 변환 프롬프트가 반드시 반영해야 할 것
1. `h1` 1회 사용
2. 요약 박스 포함
3. 비교 표 포함
4. 강조 박스 포함
5. `h2` 중심 섹션 구조
6. HTML 외 텍스트 금지
7. 티스토리 호환성 유지

### 권장 프롬프트 문구 예시
```text
주어진 블로그 콘텐츠를 티스토리 업로드용 HTML로 변환하라.
반드시 h1 1개, summary-box 1개, 비교 table 1개, highlight-box 1개를 포함하라.
설명 없이 HTML만 출력하라.
코드블록은 사용하지 마라.
```

---

## 22. 산출물 저장 위치 권장안

### 템플릿 문서
- `docs/07_html_template_spec_v1.md`

### HTML 프롬프트
- `prompts/pipeline/step_13_html_rendering_v1.md`

### 생성 결과물
- `outputs/html/`
- `outputs/final_packages/`

### 예시 파일명
- `outputs/html/2025-06-12_openai_google_ai_competition_v1.html`
- `outputs/final_packages/2025-06-12_openai_google_ai_competition_package_v1.md`

---

## 23. 다른 문서와의 연결

이 문서는 아래 문서와 연결된다.

- `PROJECT_RULES_v1.md`
- `docs/01_requirements_spec_v1.md`
- `docs/04_generation_pipeline_v1.md`
- `docs/05_prompt_design_v1.md`
- `docs/06_model_comparison_plan_v1.md`

연결 관계는 다음과 같다.

- `01_requirements_spec_v1.md`: 최종 HTML이 어떤 품질을 가져야 하는지 정의
- `04_generation_pipeline_v1.md`: HTML 변환이 어느 단계에서 수행되는지 정의
- `05_prompt_design_v1.md`: HTML 렌더링 지시문 설계 기준 제공
- `06_model_comparison_plan_v1.md`: 모델별 HTML 출력 안정성 비교 기준 제공
- `07_html_template_spec_v1.md`: 실제 HTML 구조 표준 제공

---

## 24. 현재 버전의 한계

이 문서는 HTML 템플릿 기준 초안이므로 아래 항목은 후속 보완이 필요하다.

- 모바일 실제 화면 기준 검증
- 티스토리 에디터별 붙여넣기 차이 검증
- 표가 긴 경우 대응 규칙
- 이미지 삽입 섹션 표준안
- 광고/배너와 충돌 없는 구조 검토

---

## 25. 문서 수정 이력
- v1: 티스토리용 HTML 템플릿 기준 문서 초안 작성
