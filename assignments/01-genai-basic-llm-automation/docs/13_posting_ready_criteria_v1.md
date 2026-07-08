# 13_posting_ready_criteria_v1.md

## 1. 문서 목적

이 문서는 AI 테크 뉴스 블로그 자동화 프로젝트에서 생성된 결과물이  
**실제 게시 가능한 수준인지 최종 판정하는 기준**을 정의한다.

목적은 다음과 같다.

- 게시 승인 판단을 일관된 기준으로 수행한다.
- 초안, 수정본, 최종본의 상태를 명확히 구분한다.
- 품질이 애매한 결과물이 그대로 게시되는 일을 줄인다.
- 수동 검수 결과를 최종 의사결정으로 연결한다.

---

## 2. 적용 범위

이 문서는 아래 산출물에 적용한다.

- 블로그 본문 초안
- 수동 수정 완료본
- HTML 최종 출력물
- 비교형 AI 뉴스 요약/정리 글
- 게시 직전 후보 문서

---

## 3. 이 문서의 역할

이 문서는 “좋은 글 작성 가이드”가 아니라  
**최종 승인/보류/재작업 판단 문서**이다.

따라서 이 문서는 다음 질문에 답해야 한다.

- 이 글은 지금 게시해도 되는가?
- 수정 후 게시 가능한가?
- 재생성이 더 적절한가?
- 보류해야 하는가?

---

## 4. 기본 원칙

### 원칙 1. 게시 가능 여부는 감각이 아니라 기준으로 판단한다
“괜찮아 보인다”가 아니라  
“필수 조건을 충족했는가”로 판단한다.

### 원칙 2. 완벽함보다 안정성을 우선한다
조금 덜 화려해도  
사실성, 구조, 표현 안정성이 더 중요하다.

### 원칙 3. 애매하면 보수적으로 판단한다
기사 기반성과 해석 강도가 애매하면  
과감한 게시보다 보류 또는 완화를 선택한다.

### 원칙 4. 수동 수정 비용이 과도하면 재작업을 검토한다
최종 승인 단계에서 많은 수정을 요구한다면  
생성 단계나 프롬프트 단계 문제일 가능성이 높다.

---

## 5. 최종 판정 상태값

게시 직전 결과물은 아래 상태 중 하나로 판정한다.

- `Approved`
- `Approved with Minor Edits`
- `Hold`
- `Rerun Required`
- `Rejected`

---

## 6. 상태값 정의

### 6.1 Approved
즉시 게시 가능한 상태이다.

조건 예시:
- 구조가 안정적이다
- 기사 기반성이 충분하다
- 과장 표현이 관리되어 있다
- HTML이 바로 사용 가능하다
- 추가 수정이 사실상 필요 없다

### 6.2 Approved with Minor Edits
가벼운 수정 후 게시 가능한 상태이다.

조건 예시:
- 제목 표현 완화 필요
- 도입부 1~2문장 수정 필요
- 결론 톤 조정 필요
- HTML 경미한 정리 필요

### 6.3 Hold
즉시 게시하기에는 불안하지만  
재생성 전 최종 검토나 추가 수정이 가능한 상태이다.

조건 예시:
- 비교 균형이 조금 부족함
- 일부 단정 표현 수정 필요
- 표 문구가 다소 길고 불균형함
- 게시 전 재검토가 필요함

### 6.4 Rerun Required
수동 수정으로 해결하기보다  
재생성이 더 효율적인 상태이다.

조건 예시:
- 비교 구조가 무너짐
- 기사 기반성이 약함
- 특정 대상에 과도하게 치우침
- 사실성 리스크가 여러 곳에서 보임

### 6.5 Rejected
현재 기준상 게시 대상에서 제외한다.

조건 예시:
- 품질이 현저히 낮음
- 신뢰도 문제가 큼
- 구조/근거/출력 형태가 모두 불안정함
- 실험용 실패 사례로만 보관하는 것이 적절함

---

## 7. 게시 승인 판단의 핵심 축

최종 판정은 아래 6개 축을 중심으로 한다.

1. 주제 적합성
2. 기사 기반성
3. 비교 구조 품질
4. 표현 안정성
5. HTML 사용 가능성
6. 전체 완성도

---

## 8. 주제 적합성 기준

글이 프로젝트 목적에 맞는지 먼저 확인한다.

### 점검 항목
- [ ] 이 글이 AI 테크 뉴스/비교형 블로그 목적에 맞는가
- [ ] 제목과 본문 주제가 일치하는가
- [ ] 입력 기사 묶음과 관련성이 충분한가
- [ ] 독자 대상에 맞는 설명 수준인가

### 승인 불가 신호
- 글이 지나치게 일반론 위주
- 기사 입력과 무관한 설명이 많음
- 비교형 글인데 비교 축이 거의 없음

---

## 9. 기사 기반성 기준

이 프로젝트의 최우선 승인 조건 중 하나다.

### 필수 조건
- 주요 내용이 기사 맥락 안에 있어야 한다
- 과도한 외삽이나 추정이 적어야 한다
- 비교 해석이 기사에서 자연스럽게 도출되어야 한다

### 점검 항목
- [ ] 핵심 문장이 기사 기반으로 설명 가능한가
- [ ] 없는 내용을 사실처럼 쓰지 않았는가
- [ ] 해석이 기사 범위를 심하게 벗어나지 않는가

### 즉시 보류 신호
- 출처 기사에 없는 기능/수치/전략이 등장
- 기사보다 해석이 훨씬 강함
- 추정이 누적되어 글 중심을 이룸

---

## 10. 비교 구조 품질 기준

비교형 글은 단순 요약보다 구조적 비교가 중요하다.

### 필수 조건
- 비교 대상이 분명해야 한다
- 비교 축이 일관적이어야 한다
- 한쪽에 과도하게 기울지 않아야 한다

### 점검 항목
- [ ] 비교 대상이 초반에 명확히 드러나는가
- [ ] 본문 전체에서 비교 기준이 유지되는가
- [ ] 특정 대상만 과도하게 길거나 자세하지 않은가
- [ ] 표/정리 블록이 비교 구조를 강화하는가

### 보류 또는 재생성 신호
- A는 제품, B는 전략, C는 시장 반응처럼 축이 흔들림
- 병렬 나열만 있고 비교가 없음
- 한쪽 설명이 다른 쪽의 2배 이상으로 치우침

---

## 11. 표현 안정성 기준

게시 가능한 글은 문체가 과장되지 않고 안정적이어야 한다.

### 필수 조건
- 자극적 표현이 적어야 한다
- 단정이 과하지 않아야 한다
- 투자 권유/시장 예측처럼 읽히지 않아야 한다

### 점검 항목
- [ ] “승자”, “압도”, “끝났다”, “충격” 같은 표현이 없는가
- [ ] 확정적 미래 예측이 없는가
- [ ] 기업 의도를 지나치게 단정하지 않는가
- [ ] 독자가 오해할 정도로 과격한 해석이 없는가

### 수정 우선 신호
- 결론 문단만 유독 강함
- 제목이 본문보다 자극적임
- 표현만 완화하면 게시 가능한 수준임

---

## 12. 문장 및 가독성 기준

내용이 맞아도 읽기 어려우면 게시 효율이 떨어진다.

### 필수 조건
- 문장이 과도하게 길지 않아야 한다
- 중복 표현이 많지 않아야 한다
- 문단 흐름이 자연스러워야 한다

### 점검 항목
- [ ] 문장 길이가 과도하지 않은가
- [ ] 번역투/기계적 반복이 심하지 않은가
- [ ] 문단 간 연결이 자연스러운가
- [ ] 소제목이 글 흐름을 도와주는가

### 보완 필요 신호
- 같은 표현이 반복됨
- 도입부가 너무 길고 일반적임
- 결론이 본문 반복 수준에 머무름

---

## 13. HTML 사용 가능성 기준

최종 출력물은 실제 운영에 바로 투입 가능한 수준이어야 한다.

### 필수 조건
- HTML이 구조적으로 안정적이어야 한다
- 마크다운 잔재가 없어야 한다
- 붙여넣기 시 형태가 심하게 무너지지 않아야 한다

### 점검 항목
- [ ] HTML 외 설명 문장이 섞여 있지 않은가
- [ ] 제목, 문단, 리스트, 표가 정상적으로 구분되는가
- [ ] 불필요한 코드 블록 표시가 없는가
- [ ] 태그 중첩 오류가 심하지 않은가

### 즉시 보류 신호
- HTML이 전반적으로 깨짐
- 표가 구조를 잃음
- 콘텐츠 앞뒤에 모델 설명문이 붙음
- 마크다운과 HTML이 심하게 혼합됨

---

## 14. 완성도 기준

최종본은 부분 점수보다 전체 완성도가 중요하다.

### 확인 질문
- 이 글은 한 편의 게시물로 자연스럽게 읽히는가
- 제목, 도입, 본문, 결론이 한 방향으로 연결되는가
- 지금 바로 게시해도 운영자가 불안하지 않은가

### 점검 항목
- [ ] 글 전체의 방향이 일관적인가
- [ ] 부분 수정 후 자연스럽게 연결되는가
- [ ] 독자가 읽었을 때 핵심 비교 포인트가 남는가

---

## 15. 필수 통과 조건

아래 항목은 기본적으로 충족되어야 한다.

- [ ] 기사 기반성에 중대한 문제가 없다
- [ ] 비교 구조가 존재한다
- [ ] 과장/단정 표현이 통제 가능 수준이다
- [ ] HTML이 사용 가능하다
- [ ] 제목과 본문이 일치한다
- [ ] 결론이 본문보다 과도하게 나가지 않는다

하나라도 크게 어긋나면  
`Approved` 판정은 내리지 않는다.

---

## 16. 권장 점수화 방식

필요하면 아래처럼 간단 점수화할 수 있다.

### 평가 축별 3점 척도
- `2점`: 안정적
- `1점`: 수정 필요
- `0점`: 승인 곤란

### 평가 항목
- 주제 적합성
- 기사 기반성
- 비교 구조
- 표현 안정성
- 가독성
- HTML 안정성

### 총점 예시 해석
- `10~12점`: Approved 가능
- `7~9점`: Minor Edit 또는 Hold
- `4~6점`: Hold 또는 Rerun Required
- `0~3점`: Rejected 검토

점수는 참고용이며  
최종 판단은 필수 통과 조건을 우선한다.

---

## 17. 승인 판정 예시

```md
### Posting Decision Example A
- Topic Fit: pass
- Source Grounding: pass
- Comparison Quality: pass
- Tone Safety: pass
- HTML Readiness: pass
- Final Decision: Approved
- Note:
  - ready for posting without additional revision
```

---

## 18. 소폭 수정 후 승인 예시

```md
### Posting Decision Example B
- Topic Fit: pass
- Source Grounding: pass
- Comparison Quality: acceptable
- Tone Safety: minor revision needed
- HTML Readiness: pass
- Final Decision: Approved with Minor Edits
- Note:
  - soften title
  - shorten conclusion
```

---

## 19. 보류 판정 예시

```md
### Posting Decision Example C
- Topic Fit: pass
- Source Grounding: mostly pass
- Comparison Quality: weak
- Tone Safety: acceptable
- HTML Readiness: pass
- Final Decision: Hold
- Note:
  - comparison balance needs another review
```

---

## 20. 재생성 필요 예시

```md
### Posting Decision Example D
- Topic Fit: weak
- Source Grounding: unstable
- Comparison Quality: inconsistent
- Tone Safety: uneven
- HTML Readiness: pass
- Final Decision: Rerun Required
- Note:
  - current draft requires structural regeneration
```

---

## 21. 반려 예시

```md
### Posting Decision Example E
- Topic Fit: fail
- Source Grounding: fail
- Comparison Quality: fail
- Tone Safety: fail
- HTML Readiness: unstable
- Final Decision: Rejected
- Note:
  - keep as failure sample only
```

---

## 22. 승인 전 마지막 확인 질문

게시 버튼을 누르기 전에 아래 질문을 확인한다.

1. 이 글은 기사 기반 자동화 프로젝트 결과물답게 읽히는가?
2. 독자가 읽었을 때 비교 포인트가 분명한가?
3. 과장되거나 오해를 부를 표현이 없는가?
4. HTML을 바로 붙여넣어도 되는가?
5. 지금 게시해도 나중에 크게 수정할 가능성이 낮은가?

---

## 23. 게시 보류가 더 나은 상황

아래 상황에서는 억지 승인보다 보류가 낫다.

- 기사 맥락은 맞지만 비교 중심이 약함
- 사실관계는 큰 문제 없지만 결론이 불안함
- 제목과 본문 방향이 조금 어긋남
- 검수자끼리 품질 판단이 갈림
- HTML 사소한 문제들이 반복됨

---

## 24. 수동 수정과의 연결 원칙

최종 승인 문서는 수동 검수 문서와 연결되어야 한다.

### 연결 방식
- 수동 검수에서 `Light`면 승인 가능성 높음
- `Moderate`면 보류 또는 소폭 수정 후 승인 검토
- `Heavy`면 재생성 여부 우선 검토
- `Rerun Preferred`면 승인 판정 보류

### 실무 원칙
최종 승인 단계에서 구조 수준 수정이 필요하면  
이미 승인 시점을 지난 것으로 본다.

---

## 25. 실행 로그 기록 권장 형식

최종 판정은 실행 로그에 아래처럼 남길 수 있다.

```md
## Posting Ready Decision

- Draft ID: 2026-01-15-run-03
- Review Status: Approved with Minor Edits
- Required Edits:
  - soften title
  - revise final paragraph
- Final Posting Decision:
  - Approved
```

또는 보류 사례:

```md
## Posting Ready Decision

- Draft ID: 2026-01-15-run-04
- Review Status: Hold
- Main Reason:
  - comparison axis weak
- Next Action:
  - manual revision or rerun review
```

---

## 26. 팀 운영 시 권장 규칙

### 권장 규칙
1. 승인 기준은 검수자 취향보다 문서 기준을 우선한다.
2. 초반에는 승인/보류 사례를 함께 축적한다.
3. 자주 보류되는 이유는 프롬프트 수정으로 연결한다.
4. 승인 기준이 너무 느슨해지지 않도록 정기 점검한다.

### 운영 팁
- “애매하지만 올릴 수는 있음” 같은 상태를 줄이는 것이 중요하다.
- `Hold`와 `Approved with Minor Edits`의 차이를 팀 내에서 명확히 맞춘다.

---

## 27. 게시 승인 기준이 너무 느슨할 때의 문제

- 품질 편차가 커진다
- 독자가 글 톤의 일관성을 느끼기 어렵다
- 수동 수정 부담이 사후적으로 커진다
- 프로젝트 자동화 신뢰도가 낮아진다

---

## 28. 게시 승인 기준이 너무 엄격할 때의 문제

- 너무 많은 결과물이 보류된다
- 운영 속도가 지나치게 느려진다
- 경미한 수정으로 해결 가능한 글까지 버리게 된다
- 재생성 비용이 커진다

### 균형 원칙
“중대한 문제는 엄격하게,  
경미한 표현 문제는 유연하게” 판단한다.

---

## 29. 권장 다음 작업

이 문서 작성 후 아래 작업을 수행하는 것을 권장한다.

1. 실제 초안 3개에 이 기준을 적용해본다.
2. `Approved`, `Hold`, `Rerun Required` 사례를 각각 1개 이상 모은다.
3. 자주 보류되는 이유를 프롬프트 수정 포인트로 연결한다.
4. `10_execution_log_v1.md`와 함께 판정 기록 방식을 통일한다.
5. 팀 기준 차이가 큰 항목은 별도 메모로 정리한다.

---

## 30. 다른 문서와의 연결

이 문서는 아래 문서들과 함께 사용할 때 가장 효과적이다.

- `docs/04_generation_pipeline_v1.md`
- `docs/05_prompt_design_v1.md`
- `docs/09_risk_and_limitations_v1.md`
- `docs/10_execution_log_v1.md`
- `docs/11_workflow_checklist_v1.md`
- `docs/12_manual_review_guide_v1.md`

### 역할 구분
- `04`: 생성 흐름
- `05`: 프롬프트 설계
- `09_risk_and_limitations_v1.md`: 실패 유형 관리
- `10`: 실행/판정 기록
- `11`: 절차 점검
- `12`: 수동 검수 기준
- `13`: 최종 게시 승인 판단

---

## 31. 현재 버전의 한계

이 문서는 v1 기준 문서이므로 운영 후 보완이 필요하다.

### 보완 필요 항목
- 승인/보류 실제 사례 추가
- 점수화 기준의 실전 보정
- 글 유형별 승인 기준 분리 여부 검토
- HTML 오류 심각도 분류 보완
- 팀 검수자 간 판정 차이 축소 기준 정리

---

## 32. 최소 승인 기준 요약

시간이 부족할 때는 아래 5가지만 우선 확인한다.

- [ ] 기사 기반성이 무너지지 않았는가
- [ ] 비교형 글로서 구조가 살아 있는가
- [ ] 과장/단정 표현이 통제되고 있는가
- [ ] 결론이 본문보다 더 과감하지 않은가
- [ ] HTML이 바로 게시 가능한 수준인가

이 5개 중 하나라도 크게 어긋나면  
즉시 `Approved` 판정은 내리지 않는다.

---

## 33. 실무용 최종 판정 템플릿

아래 템플릿을 사용하면 판정 기록을 빠르게 남길 수 있다.

```md
## Final Posting Review

- Draft ID:
- Topic Fit:
- Source Grounding:
- Comparison Quality:
- Tone Safety:
- Readability:
- HTML Readiness:
- Final Decision:
- Required Edits:
- Reviewer Note:
```

### 간단 예시

```md
## Final Posting Review

- Draft ID: 2026-01-20-run-02
- Topic Fit: pass
- Source Grounding: pass
- Comparison Quality: pass
- Tone Safety: minor fix
- Readability: pass
- HTML Readiness: pass
- Final Decision: Approved with Minor Edits
- Required Edits:
  - soften headline
  - shorten ending
- Reviewer Note:
  - overall stable and post-ready after light revision
```

---

## 34. 문서 수정 이력

- v1: 게시 가능 판정 기준, 상태값 정의, 필수 통과 조건, 예시 판정, 로그 템플릿 초안 작성
