# 최종 보고 — Radar × AI Strategist × AutoMaker 통합 검토

2026-09-03 · 실제 소스코드·실제 데이터 기준. **코드는 한 줄도 고치지 않았다.**

상세 근거는 다음 6개 문서에 있다. 이 문서는 그 요약이자 결론이다.

| 문서 | 내용 |
|---|---|
| [integration-audit.md](integration-audit.md) | 두 프로그램 현황·기술스택·데이터 흐름·중복·단절 |
| [feature-cross-matrix.md](feature-cross-matrix.md) | 기능별 KEEP / MOVE / MERGE / REMOVE / NEW |
| [ai-strategist-boundary.md](ai-strategist-boundary.md) | LLM / 규칙 / 코드 / 사람 경계, Hallucination 방지 |
| [data-contract.md](data-contract.md) | 공통 entity 와 JSON schema 초안 |
| [target-architecture.md](target-architecture.md) | 현재 구조 → 목표 구조 |
| [integration-roadmap.md](integration-roadmap.md) | Phase 0~5 |
| [productization-assessment.md](productization-assessment.md) | 제품화·Moat·타깃·KPI·수익모델 |

---

## 0. 검증 방법 — 문서만 읽지 않았다

| 대상 | 명령 | 결과 |
|---|---|---|
| Radar 테스트 | `python -m pytest -q` | **61 passed** (1.59s) |
| Radar 파이프라인 | `analysis.build()` / `gains()` | **777행 / 202행** |
| AutoMaker 테스트 | `python -m pytest -q --import-mode=importlib` | **64 passed** (31s) |
| AutoMaker 테스트(기본) | `python -m pytest -q` | **5개 모듈 전부 수집 실패** |
| 데이터 실측 | CSV 직접 계수 | videos 777 · snapshots 1,884 · channels 30 · channel_fit 5 · briefs 2 · **scripts 0** |

**외부 과금 API는 한 번도 부르지 않았다.** (YouTube Data API · OpenAI · Anthropic ·
Gemini · 이미지/영상 생성 전부 미호출)

---

## 1. 한 문장 결론

**결합은 타당하다. 단 «두 프로그램을 붙이는 일»이 아니라 «두 프로그램 사이에 빠져
있는 판단 층과 성과 층을 새로 만드는 일»이다.**

실제 중복은 2건뿐이다. 진짜 문제는 그 사이가 사람의 복사·붙여넣기 4회로만
이어져 있고, 게시 이후가 통째로 비어 있다는 것이다.

---

## 2. 현재 구조의 가장 큰 문제 5개

| # | 문제 | 근거 |
|---|---|---|
| 1 | **판단이 기록되지 않는다** | MAKE/WATCH/SKIP 을 저장하는 자리가 어느 시스템에도 없다. `app.py` 「오늘의 발견」은 근거를 나열할 뿐 결론을 남기지 않는다 |
| 2 | **점수가 시점 고정되지 않는다** | `analysis.build()` 는 호출 때마다 그 시점 모집단으로 재계산한다. 파일로 남는 것은 `channel_fit.csv` 뿐. 예측/실제 비교가 **원천적으로 불가능** |
| 3 | **성과 데이터가 0이다** | `App.py` 안에 `analytics`·`youtube_upload` 문자열 **0건**. 15·16단계는 «복사해서 올리세요» 가이드. Radar 는 남의 채널만 본다 |
| 4 | **채널 정체성이 두 곳에 있다** | `channels.json`(2개, 둘 다 `production_enabled:false`) vs `genres.json`(**파일 자체가 없음**). 서로 모른다 |
| 5 | **AutoMaker 는 16,883줄 단일 파일에 git 이 없다** | 폴더 복사 백업(`_원본백업_20260901_2126`) + 소스 폴더 안 2.08GB zip. 여기에 통합 코드를 넣는 것은 위험을 사는 일 |

---

## 3. 가장 큰 자동화 기회 5개

| # | 기회 | 이득 |
|---|---|---|
| 1 | Radar 브리프 → AutoMaker 소재입력 | **수동 복사 4회 → 파일 1개** |
| 2 | `skip_reanalysis` 플래그 | AutoMaker 3단계 LLM 호출 2~4개 생략 |
| 3 | 우리 영상 성과 스냅샷 | **기존 `snapshot_collector` 재사용, 비용 ~0** (videos.list 50개=1unit) |
| 4 | 규칙 엔진 1차 선별 | 777건 → 3~5건, **LLM 없이** |
| 5 | ChannelProfile 단일화 | 2곳 → 1곳 + `genres.json` 단방향 export |

---

## 4. AI 비서가 반드시 맡아야 할 기능 5개

1. **근거 문장화** — 이미 계산된 숫자를 사람이 읽을 문장으로
2. **반대 근거 생성** — 필수 필드. 비면 저장 거부
3. **Channel Fit 판정** — 이미 있음(`channel_fit.py`). **새로 만들지 말고 이동만**
4. **Angle 설계** — 이미 부분 존재. 강화
5. **오늘의 브리핑 3~5줄** — «오늘 무엇을 보아야 하는가»

> 원 지시서의 후보 A~I 중 실제로 새로 만들 것은 **3개(A·B·C)** 뿐이고,
> 2개(D·E)는 이동이며, 3개(F·H·I 확장)는 데이터가 쌓이기 전에는 만들면 안 된다.

---

## 5. AI에게 맡기면 안 되는 것

| 절대 코드가 해야 하는 것 | 절대 사람이 해야 하는 것 |
|---|---|
| ADViews · Age Bucket 백분위 | **최종 MAKE 결정** |
| Video Score · Channel Score | **세무·연금·법률·상속 사실 확정** |
| Subscriber View Ratio · 분모 하한 | **업로드** (되돌릴 수 없다) |
| 매크 방어(참여율 1.5/1k) | **최종 대본 승인** |
| Daily View Gain · MIN_GAIN_HOURS | **채널 프로필 변경** (profile_version) |
| API quota 계산 | **검색어 추가/삭제** |
| 게시 후 성과 관측 | **API 비용 한도 변경** |

시청자가 50~69세이고 다루는 것이 자기 돈과 집이다. 틀린 제도 설명은 조회수 문제가
아니라 **사람에게 손해를 끼친다.**

---

## 6. 두 시스템에서 가장 심각한 중복

**① 채널 정체성** — 단, 두 파일은 *다른 층*이다.

| Radar `channels.json` | AutoMaker `genres.json` |
|---|---|
| «이 소재가 우리 채널 것인가» 를 **판단**하는 렌즈 | «이 채널은 어떻게 쓰는가» 라는 **집필 규격** |
| audience · promise · core_question · lenses | structureType · titlePatterns · speakingStyle · forbiddenPatterns 등 13항목 |

→ 하나로 합치되 `identity` / `judgment` / `production` 블록으로 나눈다. 소유자는 Radar.

**② 시청자 목소리 분석** — Radar `comments.analyze`(실제 댓글 API 50건)와
AutoMaker `03_콘텐츠소스_분석`의 `viewer_voice` / `viewer_phrases` / `viewer_emotions`.
같은 개념을 다른 스키마로, 각각 LLM 비용을 내며 만든다.
→ Radar 를 정본으로. AutoMaker 는 값이 들어오면 **재분석하지 말고 받아쓴다.**

나머지(제목 후보 2회·소재 요약·팩트체크·`_seed_standing`)는 «같은 이름, 다른 질문»
이거나 한쪽 내부 중복이다.

---

## 7. 가장 중요한 Data Contract

**DecisionSnapshot** — 판단 시점의 숫자를 동결한다.

```jsonc
{ "snapshot_id": "…", "opportunity_id": "…", "frozen_at": "…",
  "code_version": "radar@7ebecad3",
  "profile_version": 3,
  "config_digest": "sha256:…",       // 가중치·임계값 해시
  "metrics": { /* 그 시점 값 전부 */ },
  "population": { "n_videos": 777, "n_in_bucket": 63 } }
```

이것 없이는 Phase 4·5 가 전부 성립하지 않는다.
`config_digest` 가 있어야 «가중치를 바꾸기 전 점수»와 «바꾼 뒤 점수»를 섞어 비교하는
사고를 막는다.

그 다음이 **ChannelProfile**, 그 다음이 **ProductionBrief(json)** 이다.

---

## 8. 추천 목표 Architecture

```
Radar(발견) → AI Strategist(판단·기록) → AutoMaker(제작)
            → ✋사람 업로드 → Performance(Radar 모듈 재사용) → Strategist
                        ↑                                        │
                        └────────────── Outcome ─────────────────┘
```

- Strategist 는 **FastAPI 별도 프로세스**. AutoMaker 안에도, Radar 안에도 넣지 않는다.
- **AutoMaker `App.py` 는 한 줄도 고치지 않아도 연결 7개 중 5개가 성립한다** —
  `/api/project/save` 가 «화면이 모르는 키를 지우지 않고 병합»하기 때문이다(2026-07-30 주석).
- 화면 역할: Radar=분석 콘솔 / Strategist=오늘의 결정 / AutoMaker=제작 워크플로.
  Radar 「오늘의 발견」의 **판단 블록 2개만** Strategist 로 옮긴다. 새 대시보드는 만들지 않는다.

---

## 9. MVP 범위

```
오늘의 기회 3~5
   → MAKE/WATCH/SKIP + 근거 + 반대 근거 + confidence + Channel Fit + Angle
   → ✋사람 승인
   → 프로젝트 자동 생성 + brief.json
   → 제작 (기존)
   → ✋게시 + URL 한 칸 입력
   → 24h/72h/7d 자동 스냅샷
   → 예상 vs 실제 (표본 10건 전에는 «판단 불가»)
```

**MVP 에서 뺀다:** 자연어 채팅 · 중복 소재 방지 · 위키 · 패턴 통계 · CTR 자동 수집 ·
숏폼 성과 · 예측값 자체(초기엔 «등급»만).

---

## 10. 구현 순서

| Phase | 목표 | 완료 조건 |
|---|---|---|
| **0** 현재 상태 보호 | AutoMaker git 편입 · `pytest.ini` · 2GB zip 이동 · `_seed_standing` 중복 제거 | 인자 없이 양쪽 pytest 통과 |
| **1** Data Contract | ChannelProfile 합본 · DecisionSnapshot · Opportunity JSONL · brief.json | `json` 만으로 «왜 골랐는지» 재구성 가능 |
| **2** Radar → Strategist | 규칙 엔진 → 기록 → 승인 화면 → LLM 근거 | 결정 5건이 근거·반대근거와 함께 남는다 |
| **3** Strategist → AutoMaker | brief.json 배치 · `skip_reanalysis` · Fact Check 게이트 | **손으로 옮긴 문자 0자** |
| **4** Performance | 게시 URL 입력 · 우리 영상 스냅샷 · 버킷 집계 | 게시 1건의 24h/72h/7d 가 자동으로 쌓인다 |
| **5** 학습·확장 | Outcome(게시 10건) → 통계(30건) → 규칙 보정(50건) | — |

---

## 11. 예상 위험

| 위험 | 확률 | 영향 | 완화 |
|---|---|---|---|
| **AI Hallucination** | 높음 | 높음 | 숫자 통로 단일화 · 스키마 강제 · «모른다»를 값으로 |
| **인과관계 착각** | 높음 | 높음 | 「점수 높은 걸 만들었더니 잘됐다」는 상관. `verdict` 기본값 `unknown` |
| **온보딩 13항목** | 높음 | 높음 | 남에게 팔려면 이것부터 줄여야 한다 |
| **1인 유지보수 부담** | 높음 | 높음 | 26,000줄+ 를 혼자. **가장 현실적인 위험** |
| AutoMaker HTML 수정 | 중 | 중 | 3단계·16단계 파일만, 함수 추가로 제한 |
| LLM 비용 계량 부재 | 높음 | 중 | 대본 64k·업그레이드 32k 반복. quota 개념 이식 |
| 추천이 틀렸을 때 신뢰 하락 | 높음 | 높음 | 반대 근거를 항상 함께. **LOW confidence 를 숨기지 않는다** |

---

## 12. 지금 바로 개발해도 되는 것

- AutoMaker git 편입 (`.gitignore` 먼저 — `.api_keys.json`·`license.key`·`.session_secret`)
- `pytest.ini` 한 줄 (`--import-mode=importlib`)
- Radar `_seed_standing()` 중복 제거
- **ChannelProfile 합본** — `genres.json` 이 비어 있는 **지금이 가장 싸다**
- DecisionSnapshot 동결 함수
- `production_brief` 의 JSON 출력 추가

## 13. 아직 개발하면 안 되는 것

자동 업로드 · 완전 자율 에이전트 · ML/Fine-tuning · 위키 학습 확장 ·
**AutoMaker LLM 호출부 95곳 리팩터링** · 자유형 채팅 UI · 결제/계정 관리 ·
모바일 앱 · SNS 멀티플랫폼 게시 · **Radar 를 Firestore 로 이관** · 새 대시보드

## 14. 사용자가 결정해야 하는 사항

1. `channels.json` 의 `production_enabled` 를 **언제 `true` 로 바꿀지**
   — 이게 안 되면 Phase 4 는 시작 자체가 불가능하다
2. 대본을 **Claude 웹으로 계속 쓸지, AutoMaker 6단계로 옮길지**
   (현재 경로가 3개인데 실제로 쓰이는 것은 수동 경로다)
3. **팩트체크 정책 통일안** — Perplexity 는 보조 자료, 게이트는 사람 (권고)
4. **AutoMaker HTML 수정 허용 범위** (3단계·16단계 두 파일이면 충분)
5. **Strategist 를 M1-2 과제로 낼지**

---

# 제품 관점 결론

## 15. 이 시스템이 해결하는 핵심 문제

**제작이 느린 것이 아니다. 제작은 이미 자동이다.**
**«무엇을 만들지 정한 근거가 매번 사라지는 것»** 이 문제다. 주 2~3편이면 연 100~150회 반복된다.

## 16. 가장 적합한 첫 사용자

**1차:** 「해외(한국 등) 소재를 조사해 일본 시장용 롱폼을 만드는, 얼굴 없는 1인 운영자」
— AutoMaker 의 현지화 프롬프트가 이미 이것을 전제로 만들어져 있다. 본인이 그 사람이다.
**2차:** 다채널 운영자 · 자동화 채널 운영자.
**부적합:** 소상공인·기업 마케팅팀 — Video Score·Age Bucket 은 **YouTube 롱폼 전용 설계**다.

## 17. 현재 가장 강한 제품 차별점

발견·생성·게시는 시장에 이미 많다(vidIQ / 1of10 / OpusClip / Predis / Metricool 계열).
**그 사이의 «판단과 검증» 은 비어 있다.** 우리 자리는 그 사이다.
— 이것은 강점이자 약점이다. 사이에 있는 제품은 양쪽이 다 있어야 가치가 생긴다.

## 18. 경쟁자가 쉽게 복제할 수 있는 부분

코드 전부 · 분석 알고리즘(문서에 다 공개돼 있다) · 남의 영상 데이터 ·
제작 자동화(VOICEVOX·ffmpeg·Flow 모두 공개 도구) · **«LLM 을 붙였다»는 사실 자체**

## 19. 복제하기 어려운 부분

1. **Prediction → Actual 이력** — 자기 채널을 실제로 운영해야만 생긴다
2. **채널별 판단 렌즈의 누적 보정** — «이 각도는 안 먹혔다»는 기록
3. **시간** — 스냅샷은 소급 수집이 불가능하다

**셋 다 «게시»를 해야 생기는데 지금 게시 실적이 0건이다.**

## 20. 시간이 쌓일수록 가치가 커지는 데이터

| 자산 | 현재 | 필요 조치 |
|---|---|---|
| Video Snapshot | ✅ 1,884행 | 유지 |
| Prediction vs Actual | ❌ | **저장 구조 필요** |
| 제목/Angle/Hook ↔ 성과 | ❌ | **저장 구조 필요** |
| MAKE/WATCH/SKIP 이력 | ❌ | **저장 구조 필요** |
| 게시 후 성과 | ❌ | **게시 개시 필요** |
| Outlier·Opportunity 발생 시점 | ❌ 매번 재계산 | 이력화 |

## 21. Data Flywheel 가능성

```
기회 발견 ✅ → AI 판단 ❌ → 제작 ✅ → 게시 ❌ → 성과 ❌
        → 예상 비교 ❌ → 규칙 개선 ❌ → 선택 개선 ❌
```

**8칸 중 2칸.** 지금은 Flywheel 이 아니라 반쪽 파이프다.

「데이터가 쌓이면 AI 가 학습한다」는 표현은 쓰지 않는다. 실제로 가능한 것은
① 과거 사례 검색 + Context Injection ② 성공/실패 통계화(30건) ③ 규칙 임계값 보정(50건)
④ (아주 나중에) 별도 랭킹 모델. **①만으로 대부분의 체감 가치가 나온다.**

## 22. 가장 유력한 Positioning 3개

1. 「**내 판단이 맞았는지 나중에 확인할 수 있는** 콘텐츠 기획 도구」 ← 가장 방어 가능
2. 「해외에서 잘 된 소재를 **내 채널 각도로** 바꿔 주는 도구」
3. 「무엇을 만들지 **감으로 정하지 않게** 해 주는 시스템」

## 23. Brand Architecture 추천

**B. 1개 제품 + 3 모듈.** (A 독립 3제품은 지금 문제를 그대로 재생산, C 완전통합은 시기상조)
**이름은 지금 정하지 않는다.** 제품 정의가 실제 운영 10편으로 확인된 뒤에 정한다.

## 24. 최초 Monetization 가설

| 지금 검증 가능 | 나중 | 부적절 |
|---|---|---|
| **자체 채널 수익화** · 제작 대행 · 컨설팅+SW | 리포트 판매 · Subscription · 채널당 요금 · Agency · Usage-based | White Label · Creator Pro 티어 |

**첫 수익은 소프트웨어 판매가 아니라 자체 채널과 대행에서 나온다.**
그 과정에서 쌓이는 Prediction→Actual 이 나중에 SaaS 의 근거가 된다.

## 25. 30편 운영 시 반드시 측정할 지표

| 지금부터 재도 되는 것 | 아직 재면 안 되는 것 |
|---|---|
| 발견 → 제작 승인 소요시간 | MAKE 판단 콘텐츠의 성과 우위(**채널 평균이 없다**) |
| 추천 대비 실제 제작 전환율 | Prediction 적중률(예측을 저장하지 않는다) |
| 편당 제작 시간 · LLM/이미지 비용 | CTR·유지율(게시 후에만 존재) |
| 도구 간 수동 복사 횟수 | 「같은 실수 반복률」(이력 0건) |

**표본 10건 미만에서는 성과를 «등급»으로 표시하지 않는다.**

## 26. 사업화 가능성이 있는 이유

판단 층이 시장에서 비어 있다 · 자산이 시간에 비례해 쌓인다 · 본인이 진짜 첫 사용자다 ·
제작 자동화가 이미 완성도 높아 «판단만» 얹으면 된다.

## 27. 사업화 가능성이 낮을 수 있는 이유

사용자 1명 · 게시 0건 · 온보딩 필수 13항목 · 「사이에 있는 제품」의 구조적 약점 ·
**1인이 26,000줄+ 를 유지해야 한다**(AutoMaker 16,883 + Radar 5,553 + Strategist 신규).

## 28. 지금 가장 먼저 증명해야 할 가설 3개

1. **「근거가 기록되면 판단이 실제로 나아지는가」**
   → 결정 20건을 기록하고 3개월 뒤 다시 읽어, 같은 결론이 나오는지 본다
2. **「Radar 가 고른 소재가 우리 채널에서 통하는가」**
   → **10편을 실제로 게시한다.** 이것 없이는 어떤 기술적 개선도 검증되지 않는다
3. **「복사·붙여넣기 제거가 실제로 시간을 줄이는가」**
   → **지금 1편 기획에 걸리는 시간을 먼저 잰다**

## 29. 기술 개발보다 먼저 실사용으로 검증할 것

**① 현재 소요시간 측정 ② 실제 게시 개시.** 둘 다 코드가 필요 없다.
지금 재지 않으면 나중에 비교할 기준이 영원히 없다.

## 30. 결론 — 이 시스템은 무엇이 되어야 하는가

| 후보 | 판정 |
|---|---|
| A. 개인 생산성 도구 | **지금은 이것이다. 당분간 이것으로 충분하다** |
| B. Creator 전문 Tool | **가능성 있음** — 조건: 게시 30건 + 온보딩 단순화 |
| C. SaaS | **아직 아니다** — 사용자 1명, 게시 0건, 온보딩 13항목 |
| D. Agency/Consulting 내부 OS | **현실적인 중간 경로** |

**A 로 시작해 D 를 거쳐 B 를 노린다. C 는 지금 목표로 삼지 않는다.**

- 유일한 진짜 자산(Prediction→Actual)은 **직접 운영해야만 생긴다.** A 가 자산 축적 단계 그 자체다.
- D 는 사용자를 1명에서 3~5명으로 늘리며 **온보딩의 실제 난이도를 체감**하게 한다.
  SaaS 로 가려면 반드시 거쳐야 한다.
- B/C 로 바로 가면 «기능은 많은데 아무도 온보딩을 못 끝내는 제품»이 된다.
  채널 DNA 13항목 필수 입력이 그 증거다.

---

> **가장 정직한 한 줄**
> 지금 이 프로젝트에 부족한 것은 기능이 아니라 **실제로 게시된 콘텐츠 10편**이다.
