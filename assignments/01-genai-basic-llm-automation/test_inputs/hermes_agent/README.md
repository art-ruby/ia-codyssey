# Hermes Agent 공통 평가 입력

이 폴더는 ChatGPT, Gemini, Claude에 동일하게 제공할 Hermes Agent 평가 입력과 판정 기준을 보관한다.

## 파일

| 파일 | 용도 |
|---|---|
| `article_source.md` | 세 모델에 입력한 분석 기사 원문 |
| `source_manifest.md` | 기사와 원출처 URL, 출처 계층 |
| `expected_facts.md` | 사실 검증 기준과 확인 필요 주장 |
| `test_case.md` | 공통·최적화 비교 실행 절차와 합격 기준 |

## 사용 순서

1. `article_source.md` 내용을 모델에 입력한다.
2. 공정 비교에서는 공통 v6 프롬프트를 사용한다.
3. 실무 비교에서는 모델별 v3·v4·v5 프롬프트를 사용한다.
4. 결과를 `evaluation/model_outputs/`에 저장한다.
5. `expected_facts.md`와 `test_case.md` 기준으로 평가한다.
6. 점수와 근거를 `evaluation/scores/hermes_agent/`에 기록한다.

## 중요 원칙

`article_source.md`는 평가 입력의 고정본이다. 사실이 의심되는 문장이 있어도 모델 비교 중에는 원문을 임의로 수정하지 않는다. 대신 `expected_facts.md`에서 확인 필요 여부를 표시하고, 모델이 불확실성을 어떻게 처리하는지 평가한다.

