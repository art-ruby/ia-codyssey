# 통합 로드맵 — Phase 0 ~ 5

2026-09-03 · 근거 `integration-audit.md` · 계약 `data-contract.md` · 목표 `target-architecture.md`

**한 번에 다 만들지 않는다.** 각 Phase 는 앞 Phase 없이는 성립하지 않는다.
Phase 3 이전에 AI 기능부터 붙이면 근거가 없는 추천이 나온다.

---

## 우선순위 판정 기준

| 기능군 | Impact | 자동화 가치 | 난이도 | 위험 | 의존 | 우선 |
|---|---|---|---|---|---|---|
| AutoMaker git 편입 | 낮음(직접) | — | 낮음 | **없애는 위험이 큼** | 없음 | **P0** |
| ChannelProfile 합본 | 높음 | 중 | 낮음 | 낮음 (지금 `genres.json` 이 비어 있어 가장 쌈) | 없음 | **P0** |
| DecisionSnapshot 동결 | **최고** | 낮음(당장) | 낮음 | 낮음 | 없음 | **P0** |
| StrategyDecision 기록 | **최고** | 높음 | 중 | 낮음 | Snapshot | **P1** |
| brief.json + skip_reanalysis | 높음 | **최고** | 중 | 중(AutoMaker HTML) | ChannelProfile | **P1** |
| Publication 입력칸 | 높음 | 중 | 낮음 | 낮음 | 없음 | **P1** |
| 우리 영상 성과 스냅샷 | **최고** | 높음 | 낮음 (기존 모듈 재사용) | 낮음 | Publication | **P2** |
| AI 오늘의 브리핑 | 중 | 높음 | 중 | **중(환각)** | Snapshot | **P2** |
| 자연어 질의 | 중 | 중 | 중 | 중 | 기록 축적 | **P2** |
| Outcome (예측/실제) | 높음 | 높음 | 중 | 높음(표본 부족) | 성과 10건+ | **P3** |
| 패턴 통계·위키 반영 | 중 | 중 | 높음 | **높음** | Outcome 30건+ | **P3** |
| SNS 확장 | 낮음 | 낮음 | 높음 | 높음 | 전부 | **P3** |

**Quick Win:** ChannelProfile 합본 · Publication 입력칸 · 성과 스냅샷 재사용
**Core Architecture:** DecisionSnapshot · StrategyDecision · brief.json
**Nice to Have:** 자연어 질의 · 오늘의 브리핑
**Premature:** 위키 학습 · ML 랭킹 · SNS 어댑터 · 자동 업로드

---

## Phase 0 — 현재 상태 보호

**목표.** 통합을 시작해도 되는 상태로 만든다. 기능 추가 없음.

| 할 일 | 대상 | 이유 |
|---|---|---|
| AutoMaker 를 git 저장소로 만든다 (`.gitignore` 로 output·zip·키 제외) | `C:\automaker` | 폴더 복사 백업으로는 «무엇을 바꿨는지» 를 알 수 없다. 통합 작업의 전제 |
| `AutoTube_Student.zip`(2.08GB) 을 소스 밖으로 옮긴다 | 같음 | 백업·git 이 감당 못 한다 |
| `pytest.ini` 한 줄 추가 (`--import-mode=importlib`) | 같음 | 지금 기본 명령으로 테스트가 **수집조차 안 된다** |
| Radar `_seed_standing()` 중복 제거 | `export.py`·`production_brief.py` | 조용히 갈릴 자리 |
| 두 시스템 현 상태 스냅샷 커밋 | 양쪽 | 되돌아갈 지점 |

**수정 예상 파일:** `automaker/.gitignore`(신규), `automaker/pytest.ini`(신규),
`radar/src/export.py`, `radar/src/production_brief.py`
**의존:** 없음 **위험:** 낮음. 단 git init 시 `.api_keys.json`·`license.key`·`.session_secret`
가 커밋되지 않도록 **먼저** `.gitignore` 를 쓴다.
**테스트:** 양쪽 pytest 통과 (61 / 64)
**완료 조건:** `git status` 가 깨끗하고, `python -m pytest -q` 가 양쪽에서 인자 없이 통과.

---

## Phase 1 — Data Contract

**목표.** 코드를 붙이지 않고 **형식**을 세운다. 이 Phase 만 끝나도 수작업이 줄어든다.

| 할 일 | 산출 |
|---|---|
| ChannelProfile 합본 스키마 확정 + `channels.json` 확장 | `data/config/channels.json` (identity/judgment/production/youtube) |
| `genres.json` 내보내기 (단방향) | `tools/export_genres.py` |
| DecisionSnapshot 동결 함수 | `src/snapshot_decision.py` — `analysis.build()` 결과 + git commit + config 해시 |
| Opportunity 내보내기 | `data/processed/opportunities/{date}.jsonl` |
| ProductionBrief 의 JSON 출력 | `production_brief.build()` 가 `.md` 와 `.json` 을 함께 낸다 |
| 스키마 검증 테스트 | `tests/test_contract.py` — 필수 필드·결측 규칙(0으로 채우지 않았는가) |

**수정 예상 파일:** `radar/src/channels.py`, `radar/src/production_brief.py`,
`radar/src/config.py`(해시), 신규 3개, `radar/tests/test_contract.py`
**의존:** Phase 0
**위험:** `profile_version` 을 올리면 `channel_fit.csv` 캐시 5건이 전부 무효가 된다.
→ **의도된 동작이다.** 다만 재판정 비용(LLM 5회)을 알고 올린다.
**테스트:** 계약 스키마 테스트 + 기존 61개 유지
**완료 조건:** 브리프 하나를 만들면 `.md` 와 `.json` 이 같이 생기고,
`json` 만으로 «어떤 영상을 왜 골랐는지» 를 재구성할 수 있다.

---

## Phase 2 — Radar → AI Strategist

**목표.** 판단을 기록하기 시작한다. **여기가 이 프로젝트의 핵심이다.**

| 할 일 | 비고 |
|---|---|
| FastAPI 앱 골격 (`strategist/`) | 라우터/서비스 분리, Pydantic 검증, CORS, `/docs` |
| 규칙 엔진 (1차 MAKE/WATCH/SKIP) | **LLM 없이 먼저.** 임계값은 config 한 곳 |
| `POST /api/decisions` · `GET /api/decisions` | append-only JSONL |
| Fact Check 플래그 (정규식) | 연금·세금·상속·보험·부동산·금액 |
| 화면: 오늘의 추천 3~5 + 근거/반대근거 + 승인 버튼 | 정적 HTML/JS |
| LLM 근거 문장 생성 | **Snapshot 만 입력으로 받는 조립 함수** — 다른 인자 금지 |
| Evidence 링크 · `unsupported_claims` 배지 | |
| Radar 「오늘의 발견」에서 판단 블록 제거 | 화면 중복 방지 |

**수정 예상 파일:** 신규 `strategist/` 일체, `radar/app.py`(블록 이동)
**의존:** Phase 1
**위험:**
- LLM 환각 → `ai-strategist-boundary.md` §3 의 3중 방어를 **먼저** 구현.
- 자유 채팅창을 만들고 싶은 유혹 → **금지.** 정해진 질문 6~8개부터.
- Radar 화면을 건드리다 기존 61개 테스트를 깨는 것 → 이동만 하고 로직은 손대지 않는다.

**테스트:** 규칙 엔진 단위 테스트(임계 경계값), 스키마 검증, `reasons_against` 가 비면 저장 거부
**완료 조건:** 실제 후보 5건에 대해 MAKE/WATCH/SKIP 을 내리고
`decisions.jsonl` 에 근거·반대근거·confidence 가 남는다. **일주일 뒤 다시 읽어도
왜 그렇게 정했는지 알 수 있다.**

---

## Phase 3 — AI Strategist → AutoMaker

**목표.** 복사·붙여넣기 3회를 파일 1개로 바꾼다.

| 할 일 | 비고 |
|---|---|
| 승인된 결정 → AutoMaker 프로젝트 폴더 생성 + `brief.json` 배치 | `POST /api/new_project` 를 그대로 호출해도 되고, 폴더만 만들어도 된다 |
| `project.json` 에 `opportunity_id`·`decision_id`·`brief_id` 주입 | **병합 저장 덕분에 AutoMaker 코드 변경 불필요** |
| AutoMaker 3단계 화면: `brief.json` 이 있으면 읽어 채우고 재분석 생략 | `pages/3.콘텐츠소스.html` 소폭 수정 |
| 댓글 분석 매핑 (Radar → viewer_voice/phrases/emotions) | 원문 보존 규칙 유지 |
| Fact Check 미완료면 대본 생성 차단 | `_channel_required_missing` 과 같은 패턴 |

**수정 예상 파일:** `strategist/services/handoff.py`(신규),
`automaker/pages/3.콘텐츠소스.html`
**의존:** Phase 2
**위험:**
- **AutoMaker HTML 을 처음 건드리는 Phase다.** 304KB 짜리 파일도 있다.
  → 3단계 파일 하나만, 함수 하나 추가로 제한. `_원본백업` 대신 git 브랜치로.
- `skip_reanalysis` 가 잘못 켜지면 소재 분석 없이 대본이 나간다.
  → 브리프에 `script_map`/`emotion_map` 상당 정보가 없으면 **건너뛰지 않는다**.
    부분 생략이 아니라 «전부 있으면 생략, 아니면 그대로 분석» 로 한다.

**테스트:** `brief.json` 있는 프로젝트 / 없는 프로젝트 두 경우의 프런트 계약 테스트
(AutoMaker 에 이미 `test_japanese_frontend_contract.py` 가 있다 — 같은 방식)
**완료 조건:** 결정 승인 → AutoMaker 를 열면 3단계가 채워져 있고,
사람이 손으로 옮긴 문자가 **0자**다.

---

## Phase 4 — Performance Feedback

**목표.** 게시 후 데이터를 돌려받는다. **Flywheel 의 유일한 입구를 만든다.**

| 할 일 | 비고 |
|---|---|
| `ChannelProfile.youtube.channel_id` 채우기 | **사람이 해야 한다. 지금 null 이다** |
| AutoMaker 16단계에 «게시 URL» 입력칸 1개 | 또는 Strategist 화면에 수기 입력 |
| `POST /api/publications` | |
| `snapshot_collector` 를 우리 영상에도 적용 | `data/raw/own_snapshots.csv`. videos.list 50개=1unit — 비용 거의 0 |
| 24h/72h/7d/30d 버킷 집계 | 결정적 코드 |
| CTR·유지율 수기 입력 폼 | **YouTube Analytics OAuth 는 아직 붙이지 않는다** |
| 성과 화면 (게시물별 · 채널 평균 대비) | 표본 10건 미만이면 «판단 불가» 를 표시 |

**수정 예상 파일:** `radar/src/own_performance.py`(신규),
`radar/run_daily.cmd`(한 줄 추가), `strategist/`, `automaker/pages/15·16`
**의존:** Phase 3 + **실제 게시 1건 이상**
**위험:**
- 채널이 아직 `production_enabled: false` 다. **게시 실적이 0이면 이 Phase 는 시작할 수 없다.**
- 표본 부족 상태에서 «성과가 좋다/나쁘다» 를 말하는 것 → `n<10` 이면 등급을 내지 않는다.

**테스트:** 버킷 경계 계산, 결측 처리(Analytics 미입력 시 `null` 유지)
**완료 조건:** 게시한 영상 1건에 대해 24h·72h·7d 조회수가 자동으로 쌓인다.

---

## Phase 5 — 학습과 확장

**목표.** 사례가 쌓인 뒤에만 시작한다.

| 할 일 | 착수 조건 |
|---|---|
| Outcome (예측 vs 실제) | 게시 **10건** |
| 과거 사례 검색 + Context Injection | 결정 **20건** |
| 성공/실패 패턴 통계화 | 게시 **30건** |
| Recommendation Rule 보정 | 위 통계가 유의미할 때 |
| 위키에 검증된 패턴 반영 | 같음 |
| 숏폼/SNS 어댑터 | 롱폼 루프가 한 바퀴 돈 뒤 |
| 별도 랭킹 모델 | **당분간 없음.** Fine-tuning·ML 도입 금지 |

**위험:** 이 Phase 를 앞당기고 싶은 유혹이 가장 크다.
**«데이터가 쌓이면 AI 가 알아서 학습한다» 는 말은 사실이 아니다.**
실제로 일어나는 것은 «과거 사례를 프롬프트에 넣는 것»(Phase 5-1)과
«통계를 규칙 임계값에 반영하는 것»(Phase 5-3)뿐이다. 그 둘을 구분해서 부른다.

---

## M1-2 과제와의 연결

과제 요구사항이 Phase 2 와 **거의 그대로 겹친다.** 별도 toy app 을 만들지 않는다.

| 과제 요구 | 이 시스템에서 |
|---|---|
| 시계열 데이터 100개+ | `video_snapshots.csv` **1,884행** (또는 own_snapshots) |
| 분석 요약(기간·개수·평균/최대/최소·최근 추세) | `analysis.build()` + `gains()` 가 이미 낸다 |
| FastAPI + 라우터/서비스 분리 + Pydantic | Strategist 골격 |
| Firestore `data` / `conversations` | PerformanceSnapshot/VideoSnapshot / Conversation |
| CRUD 5개 + summary | 결정·데이터 CRUD + `/api/data/summary` = 오늘의 요약 |
| 대화 기록 저장/불러오기 | Conversation entity |
| Context Injection | **DecisionSnapshot 을 시스템 프롬프트에 주입** — 과제의 핵심 개념 그 자체 |
| CORS·환경변수·Swagger·Render/Vercel | 그대로 |

**단, 과제 때문에 구조를 나쁘게 만들지 않는다.**

- Firestore 를 **Radar 의 원본 저장소로 만들지 않는다.** 원본은 CSV 로 둔다.
  Firestore 는 Strategist 의 결정·대화·성과 요약만 담는다.
- 과제 제출용으로 «아무 시계열» 을 쓰지 않는다. **우리 스냅샷을 쓴다** —
  그래야 과제물이 버려지지 않고 Phase 2 의 실물이 된다.
- OpenAI 키를 과제 요구로 쓰되, Radar 는 계속 프록시(`copa.codyssey.kr`)를 쓴다.
  **제공자를 한 곳에서만 바꾸는 `translate.py` 패턴을 Strategist 에도 그대로 적용한다.**

---

## 절대 하지 않을 것 (이번 단계)

- 대규모 리팩터링 — 특히 AutoMaker `App.py` 의 LLM 호출부 95곳 정리
- 기존 scoring 공식 변경
- 두 프로그램을 한 저장소로 강제 병합
- 자동 업로드 · 완전 자율 에이전트
- ML 추천 모델 · Fine-tuning
- 결제·사용자 관리·모바일 앱
- Production Brief 제거 (지금 것이 자산이다)
