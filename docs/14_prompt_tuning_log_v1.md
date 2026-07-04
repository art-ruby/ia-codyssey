# 14_prompt_tuning_log_v1.md

## 1. 문서 목적

이 문서는 AI 테크 뉴스 블로그 자동화 프로젝트에서  
프롬프트 수정 이력과 그에 따른 결과 변화를 기록하기 위한 기준 문서이다.

목적은 다음과 같다.

- 프롬프트 변경 이유를 추적 가능하게 만든다.
- 어떤 수정이 품질 개선에 효과적이었는지 기록한다.
- 반복 실패를 감으로 해결하지 않고 로그 기반으로 관리한다.
- 생성 품질 문제를 구조적으로 개선할 수 있게 한다.

---

## 2. 적용 범위

이 문서는 아래 항목에 적용한다.

- 기사 요약 프롬프트
- 비교형 본문 생성 프롬프트
- 제목 생성 프롬프트
- HTML 변환 프롬프트
- 후처리/수정용 프롬프트
- 모델별 프롬프트 차이 실험 기록

---

## 3. 이 문서의 역할

이 문서는 “프롬프트 모음집”이 아니다.  
이 문서의 핵심 역할은 다음과 같다.

1. 어떤 문제가 있었는지 기록한다.
2. 그 문제를 해결하기 위해 프롬프트를 어떻게 바꿨는지 기록한다.
3. 변경 후 결과가 실제로 나아졌는지 확인한다.
4. 효과 없는 수정은 다시 되돌리거나 보완한다.

즉, 이 문서는  
**프롬프트 개선의 실험 로그 문서**이다.

---

## 4. 기본 원칙

### 원칙 1. 문제 없이 프롬프트를 바꾸지 않는다
수정은 구체적 문제를 해결하기 위한 것이어야 한다.

### 원칙 2. 한 번에 너무 많은 요소를 바꾸지 않는다
여러 요소를 동시에 바꾸면 어떤 변화가 효과를 냈는지 알기 어렵다.

### 원칙 3. 프롬프트 변경은 결과물로 검증한다
“좋아 보인다”가 아니라 실제 초안 품질로 확인한다.

### 원칙 4. 실패도 기록한다
효과 없는 수정도 중요한 자산이다.

### 원칙 5. 프롬프트보다 상위 문제도 의심한다
입력 기사 품질, 작업 순서, 모델 특성 문제일 수도 있다.

---

## 5. 프롬프트 튜닝이 필요한 대표 상황

아래 상황이 반복되면 프롬프트 조정을 검토한다.

- 기사 기반성이 약해짐
- 비교 구조가 흐려짐
- 특정 기업/제품 설명이 과도하게 길어짐
- 제목이 자극적으로 생성됨
- 결론이 본문보다 과감해짐
- HTML 출력이 자주 깨짐
- 도입부가 지나치게 일반론적임
- 소제목이 불안정하거나 일관성이 없음
- 표가 불균형하거나 의미 없이 생성됨

---

## 6. 튜닝 로그의 핵심 질문

각 수정 기록은 아래 질문에 답할 수 있어야 한다.

1. 무엇이 문제였는가?
2. 왜 그 문제가 생겼다고 판단했는가?
3. 프롬프트를 어떻게 바꿨는가?
4. 바꾼 뒤 결과는 어떻게 달라졌는가?
5. 이 수정은 유지할 가치가 있는가?

---

## 7. 로그 기록 단위

프롬프트 튜닝 기록은 아래 단위 중 하나로 남긴다.

### 7.1 단일 문구 수정
예:
- “과장 금지” 문구 추가
- “기사에 없는 내용 추정 금지” 문구 강화

### 7.2 섹션 구조 수정
예:
- 도입/비교/결론 구조 명시
- 표 생성 지시 위치 변경

### 7.3 출력 형식 수정
예:
- HTML만 출력하도록 제한
- 마크다운 금지 명시

### 7.4 단계 분리
예:
- 초안 생성과 HTML 변환을 분리
- 제목 생성과 본문 생성을 분리

### 7.5 모델별 조건 분리
예:
- GPT용 프롬프트와 Claude용 프롬프트 차별화
- Codex용 후처리 규칙 별도 관리

---

## 8. 기록해야 하는 최소 항목

모든 튜닝 로그는 최소한 아래 항목을 포함한다.

- 날짜
- 대상 프롬프트
- 문제 유형
- 수정 전 상태
- 수정 내용
- 테스트 결과
- 최종 판단
- 후속 액션

---

## 9. 권장 로그 템플릿

```md
## Prompt Tuning Entry

- Date:
- Prompt ID / Name:
- Stage:
- Model:
- Problem Observed:
- Suspected Cause:
- Prompt Change:
- Test Input:
- Result Summary:
- Quality Impact:
- Decision:
- Next Action:
- Note:
```

---

## 10. 항목별 작성 가이드

### Date
수정 날짜를 기록한다.

예:
- 2026-01-20

### Prompt ID / Name
어떤 프롬프트를 수정했는지 식별 가능해야 한다.

예:
- P03_draft_generation
- P07_html_conversion
- title_generation_prompt_v1

### Stage
파이프라인의 어느 단계인지 적는다.

예:
- article summarization
- comparison drafting
- title generation
- html formatting
- review revision

### Model
어떤 모델 기준 수정인지 적는다.

예:
- GPT-4.1
- Claude
- Codex
- shared prompt

### Problem Observed
실제로 관찰된 문제를 적는다.

좋은 예:
- conclusion repeatedly overstates market impact
- intro is too generic and weakly tied to source articles
- HTML output sometimes includes markdown fences

나쁜 예:
- 품질이 별로임
- 뭔가 이상함

### Suspected Cause
왜 이런 문제가 생겼다고 보는지 적는다.

예:
- prompt encourages broad interpretation in conclusion
- source-grounding constraint is too weak
- output format rule is buried too low in prompt

### Prompt Change
무엇을 어떻게 바꿨는지 구체적으로 적는다.

예:
- added explicit instruction to avoid unsupported future claims
- moved HTML-only rule to top of prompt
- changed comparison section into fixed 3-part structure

### Test Input
가능하면 어떤 기사 묶음/주제로 테스트했는지 적는다.

예:
- OpenAI vs Google model release coverage
- NVIDIA/AMD AI chip news bundle

### Result Summary
수정 후 어떤 변화가 있었는지 적는다.

예:
- conclusion became more cautious
- source references became tighter
- HTML fences disappeared
- however intro became slightly repetitive

### Quality Impact
개선/악화/혼합 중 하나로 간단히 적을 수 있다.

예:
- Improved
- Mixed
- No Clear Change
- Regressed

### Decision
수정 유지 여부를 적는다.

예:
- Keep
- Revert
- Needs More Testing
- Partial Keep

### Next Action
다음 실험이나 보완 방향을 적는다.

예:
- test on 3 more article sets
- shorten intro instruction
- add balance constraint for comparison table

---

## 11. 문제 유형 분류 기준

로그 누적 시 자주 쓰는 문제 유형을 분류해두면 편하다.

### 권장 분류
- Source Grounding
- Comparison Structure
- Tone / Overclaim
- Title Quality
- Readability
- HTML Formatting
- Length Control
- Bias / Balance
- Repetition
- Hallucination Risk

---

## 12. 품질 영향 판정 기준

프롬프트 수정 후 결과 변화는 아래처럼 단순 분류할 수 있다.

### Improved
문제가 눈에 띄게 줄고 품질이 안정됨

### Mixed
좋아진 부분도 있으나 다른 부작용이 생김

### No Clear Change
변화를 확실히 확인하기 어려움

### Regressed
원래보다 품질이 나빠짐

---

## 13. 유지/되돌리기 판단 기준

### Keep
- 문제 완화가 분명함
- 부작용이 크지 않음
- 다른 테스트에서도 유사하게 안정적임

### Partial Keep
- 일부 문구는 효과 있음
- 하지만 전체 수정안은 과도함
- 필요한 부분만 남기고 나머지는 조정

### Revert
- 품질 개선이 없거나 악화됨
- 다른 부작용이 더 큼
- 원인 진단이 틀렸을 가능성이 높음

### Needs More Testing
- 테스트 수가 부족함
- 특정 주제에서만 좋아졌을 수 있음
- 모델별 편차 확인이 더 필요함

---

## 14. 좋은 튜닝 로그 예시

```md
## Prompt Tuning Entry

- Date: 2026-01-20
- Prompt ID / Name: P03_draft_generation
- Stage: comparison drafting
- Model: GPT-4.1
- Problem Observed:
  - conclusions often sound more certain than source articles support
- Suspected Cause:
  - prompt asks for "what this means" without enough caution constraint
- Prompt Change:
  - added instruction:
    "Do not make strong future predictions. Keep conclusions limited to article-supported implications."
- Test Input:
  - OpenAI / Google / Meta model update article set
- Result Summary:
  - conclusions became more grounded and less sensational
  - overall structure remained stable
- Quality Impact: Improved
- Decision: Keep
- Next Action:
  - test same rule on hardware comparison topics
- Note:
  - strong candidate for shared base prompt
```

---

## 15. 혼합 결과 예시

```md
## Prompt Tuning Entry

- Date: 2026-01-21
- Prompt ID / Name: P03_draft_generation
- Stage: comparison drafting
- Model: Claude
- Problem Observed:
  - intros are too broad and not article-led
- Suspected Cause:
  - prompt opens with market-context framing before source framing
- Prompt Change:
  - require intro to start from source article developments first
- Test Input:
  - NVIDIA / AMD / Intel AI chip article set
- Result Summary:
  - intro became more source-tied
  - however first paragraph felt slightly dry and abrupt
- Quality Impact: Mixed
- Decision: Partial Keep
- Next Action:
  - add one sentence bridge rule for intro flow
- Note:
  - source grounding improved, readability slightly weakened
```

---

## 16. 실패 로그 예시도 남겨야 한다

효과 없는 수정도 반드시 남긴다.

```md
## Prompt Tuning Entry

- Date: 2026-01-22
- Prompt ID / Name: P07_html_conversion
- Stage: html formatting
- Model: shared prompt
- Problem Observed:
  - markdown remnants appear in output
- Suspected Cause:
  - output format instruction not strict enough
- Prompt Change:
  - added repeated "HTML only" instruction in three places
- Test Input:
  - 3 existing draft samples
- Result Summary:
  - markdown fences still appeared in 1 of 3 cases
  - no meaningful consistency gain
- Quality Impact: No Clear Change
- Decision: Revert
- Next Action:
  - simplify conversion step and reduce extra explanation text
- Note:
  - repetition alone did not solve formatting leakage
```

---

## 17. 로그 작성 원칙

### 원칙 1. 관찰 가능한 문제만 적는다
막연한 느낌보다 실제 출력 문제를 적는다.

### 원칙 2. 수정 내용은 문장 단위로 남긴다
어떤 문구를 추가/삭제/이동했는지 추적 가능해야 한다.

### 원칙 3. 결과는 비교 기준과 함께 본다
수정 전/후의 차이를 같은 유형 입력으로 비교한다.

### 원칙 4. 테스트 수가 적으면 확정하지 않는다
한 번 좋아졌다고 바로 표준 프롬프트로 고정하지 않는다.

---

## 18. 프롬프트 버전 관리 권장 방식

프롬프트는 문구 변경이 잦기 때문에 버전 관리가 필요하다.

### 권장 방식
- `P03_draft_generation_v1`
- `P03_draft_generation_v1_1`
- `P03_draft_generation_v1_2`
- `P07_html_conversion_v1`

### 원칙
- 큰 구조 수정은 minor 버전 상승
- 작은 문구 수정은 patch 수준으로 기록 가능
- 운영 반영본은 별도로 표시한다

예:
- working draft
- test version
- production version

---

## 19. 운영 반영 기준

테스트 결과가 좋아 보여도 바로 운영 반영하지 않는다.

### 권장 반영 조건
- 최소 3개 이상 다른 기사 세트에서 테스트
- 주요 실패 유형이 줄어듦
- 새 부작용이 크지 않음
- 수동 검수 부담이 실제로 감소함

---

## 20. 자주 발생하는 튜닝 패턴

### 20.1 과장 결론 완화
- 결론에 “의미”를 쓰게 하면 과도한 해석이 생길 수 있음
- 해결:
  - 기사 근거 범위 내 해석 제한
  - 미래 예측 금지
  - 승패형 표현 금지

### 20.2 비교 축 흔들림 방지
- 비교형 글인데 축이 자주 바뀌는 문제
- 해결:
  - 비교 기준 2~3개를 먼저 명시
  - 각 섹션이 같은 축을 따라가게 고정

### 20.3 도입부 일반론 축소
- 도입부가 AI 산업 일반론으로 시작하는 문제
- 해결:
  - 첫 문단에서 기사 사건 자체를 먼저 언급
  - 배경 설명은 2순위로 배치

### 20.4 HTML 출력 안정화
- 모델 설명문이나 코드블록이 섞이는 문제
- 해결:
  - 출력 형식 규칙을 최상단에 배치
  - “설명 없이 HTML만 출력” 명시
  - 변환 단계 분리

---

## 21. 모델별 튜닝 로그를 분리할지 여부

프로젝트 운영 중 모델별 특성이 크게 다르면  
공통 로그와 별도 로그를 병행하는 것이 좋다.

### 공통 로그에 적는 것
- 전체 운영 공통 규칙
- 모델과 무관한 구조 변경
- 파이프라인 설계 변경

### 모델별 로그에 적는 것
- 특정 모델에서만 발생하는 과장
- 출력 형식 오류
- 길이 조절 특성
- 문체 편차

---

## 22. 수동 검수와의 연결

튜닝 로그는 검수 결과와 연결될 때 가장 유용하다.

### 연결 방식
- `12_manual_review_guide_v1.md`에서 반복 지적된 문제 확인
- `13_posting_ready_criteria_v1.md`에서 자주 Hold 되는 원인 확인
- 그 문제를 프롬프트 수정 대상으로 연결
- 수정 후 Hold 비율이 줄었는지 확인

### 예시
- 반복 문제: 결론 과장
- 조치: 결론 톤 제약 문구 추가
- 확인: 수정 후 Approved 비율 상승 여부 확인

---

## 23. 실행 로그와의 연결

프롬프트 튜닝은 실행 로그와 함께 봐야 한다.

### 함께 기록하면 좋은 항목
- 어떤 버전의 프롬프트를 사용했는지
- 어떤 모델에서 테스트했는지
- 결과 판정이 어땠는지
- 재생성 비율이 줄었는지
- 수동 수정 시간이 줄었는지

---

## 24. 권장 성과 지표

프롬프트 수정 효과를 아래 지표로 간단히 볼 수 있다.

- Approved 비율 증가
- Hold 비율 감소
- Rerun Required 비율 감소
- 수동 수정량 감소
- HTML 오류 감소
- 제목 수정 빈도 감소
- 결론 완화 수정 빈도 감소

---

## 25. 로그를 남기지 않을 때의 문제

- 같은 실수를 반복한다
- 왜 좋아졌는지 알 수 없다
- 팀원이 바뀌면 기준이 사라진다
- 실패 원인을 모델 탓으로만 돌리게 된다
- 프롬프트가 불필요하게 길고 복잡해진다

---

## 26. 로그가 너무 장황해질 때의 문제

- 실제로 다시 보지 않게 된다
- 핵심 원인과 결과가 흐려진다
- 운영 속도가 떨어진다

### 균형 원칙
짧게 쓰되,  
**문제 / 수정 / 결과 / 판단**은 반드시 남긴다.

---

## 27. 최소 실무 템플릿

시간이 부족할 때는 아래 형태만 써도 된다.

```md
## Prompt Change Quick Log

- Date:
- Prompt:
- Problem:
- Change:
- Result:
- Decision:
```

예시:

```md
## Prompt Change Quick Log

- Date: 2026-01-23
- Prompt: P03_draft_generation
- Problem: title too sensational
- Change: added "avoid dramatic or winner-loser framing"
- Result: titles became calmer in 2/3 tests
- Decision: keep and monitor
```

---

## 28. 팀 운영 시 권장 규칙

1. 프롬프트를 수정했으면 반드시 로그를 남긴다.
2. 운영 반영 전 테스트 결과를 최소 2~3건 확인한다.
3. 실패 로그도 성공 로그만큼 중요하게 취급한다.
4. 공통 프롬프트와 실험 프롬프트를 구
