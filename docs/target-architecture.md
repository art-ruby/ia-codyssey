# 목표 아키텍처

2026-09-03 · 근거 `integration-audit.md` · 계약 `data-contract.md`

---

## 1. 현재 구조 (실측)

```
┌─ Radar (Streamlit · CSV) ──────────────────────────┐
│  seeds.json → collector → videos.csv (777)         │
│               snapshot_collector → snapshots(1884) │
│               analysis.build()  ← 매번 재계산       │
│               channel_analyzer → channels.csv (30) │
│               channel_fit → channel_fit.csv (5)    │
│               comments · subtitles                 │
│               production_brief → briefs/ (2)       │
└───────────────────┬────────────────────────────────┘
                    │  ✋ 화면에서 복사
                    ▼
              [ Claude 웹 ]  ← 사람이 대화하며 대본을 받는다
                    │  ✋ 손으로 저장 → data/scripts/ (0건)
                    ▼
┌─ AutoMaker (Flask · 프로젝트 폴더) ────────────────┐
│  ✋ 소재 입력칸에 손으로 붙여넣기                    │
│  2 채널설정(genres.json — 현재 0개)                 │
│  3 소재분석 → 4 제목 → 5 화자 → 6 대본(64k)         │
│  7 TTS(VOICEVOX) → 8·9 이미지·영상(Flow/Grok)       │
│  11 렌더 → 12 썸네일 → 14 숏폼                      │
│  15·16 등록 «가이드»                                │
└───────────────────┬────────────────────────────────┘
                    │  ✋ 사람이 유튜브에 업로드
                    ▼
                 YouTube
                    │
                    ✗  아무 데이터도 돌아오지 않는다
```

**끊긴 곳 3군데:** 판단(기록 없음) · 대본 전달(수동 3회) · 성과(전무).

---

## 2. 목표 구조

```
                    ┌──────────────────────────────────────┐
                    │  ChannelProfile (단일 파일)           │
                    │  identity / judgment / production     │
                    └───────┬───────────────┬──────────────┘
                            │ 판단 렌즈       │ 집필 규격
                            ▼               ▼
┌─ ① RADAR ────────────────────┐   ┌─ ③ AUTOMAKER ─────────────┐
│ 무엇을 만들 가치가 있는가?      │   │ 실제로 만든다              │
│                              │   │                           │
│ collector · snapshot         │   │ 3 소재(brief.json 수용)    │
│ analysis (점수 · 유일 계산처)  │   │ 4 제목 · 5 화자           │
│ channel_analyzer             │   │ 6 대본 · 7 TTS            │
│ comments · subtitles         │   │ 8·9 이미지·영상            │
│                              │   │ 11 렌더 · 12 썸네일        │
│ → Opportunity + Evidence     │   │ 14 숏폼                   │
└──────────┬───────────────────┘   └────────┬──────────────────┘
           │ opportunity.json               │ project.json
           │ evidence                       │ (+opportunity_id/decision_id/brief_id)
           ▼                                ▲
┌─ ② AI STRATEGIST ─────────────────────────┴──────────────────┐
│ 왜 · 어떻게 · 지금 만들 것인가                                  │
│                                                              │
│  [규칙 엔진]  1차 선별 · Fact Check 플래그 · 데이터 부족 판정    │
│       ↓                                                      │
│  [DecisionSnapshot]  판단 시점의 숫자를 동결 (불변)             │
│       ↓                                                      │
│  [LLM]  근거 · 반대 근거 · confidence · angle · 오늘의 브리핑    │
│       ↓                                                      │
│  [사람]  승인 ─────────────────────────────────────────────┐  │
│       ↓                                                   │  │
│  StrategyDecision (append-only) → ProductionBrief(json+md)┘  │
│                                                              │
│  Content Memory: decisions · briefs · publications · outcomes │
└──────────┬───────────────────────────────────▲───────────────┘
           │ brief.json                        │ Outcome
           ▼                                   │
      (③ AUTOMAKER 로)                         │
           │                                   │
           ▼  ✋ 사람이 업로드 (자동화하지 않는다)  │
       YouTube / SNS                           │
           │                                   │
           ▼  Publication (URL 한 칸 입력)       │
┌─ ④ PERFORMANCE ───────────────────────────────┘
│ snapshot_collector 를 «우리 영상» 에도 돌린다 (videos.list, 50개=1unit)
│ 24h / 72h / 7d / 30d
│ CTR · 유지율 · 구독전환 → 초기에는 Studio 수기 입력
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 무엇이 어디에 사는가

| 층 | 실행 형태 | 언어·기술 | 저장 |
|---|---|---|---|
| ① Radar | Streamlit + CLI (현행) | Python·pandas | CSV/JSON |
| ② Strategist | **FastAPI + 정적 프런트** (신규) | Python·Pydantic | 파일(Phase1) → Firestore(M1-2) |
| ③ AutoMaker | Flask + HTML (현행, **거의 안 건드림**) | Python | 프로젝트 폴더 |
| ④ Performance | Radar 안의 모듈 하나 | Python | CSV |

**Strategist 를 별도 프로세스로 두는 이유**

1. AutoMaker 는 16,883줄 단일 파일에 git 이 없다. **여기에 판단 로직을 넣으면 안 된다.**
2. Radar 안에 넣으면 Streamlit 이 «분석 화면» 과 «판단 화면» 을 겸하게 되어
   목적이 흐려진다. Radar 화면의 미덕은 **숫자와 경고문이 같이 있는 것**인데,
   판단 UI 는 결론이 앞에 와야 한다. 두 화면은 성격이 다르다.
3. M1-2 과제 요구사항(FastAPI·Firestore·OpenAI·CORS·Render/Vercel)과 정확히 겹친다.
   과제를 위한 별도 toy app 을 만들 필요가 없다.

---

## 4. 세 시스템의 화면 역할

중복 화면을 만들지 않는다.

| | Radar (Streamlit) | Strategist (신규) | AutoMaker (기존) |
|---|---|---|---|
| 성격 | **분석·운영 콘솔** | **오늘의 결정 화면** | **제작 워크플로** |
| 주 사용자 행동 | 데이터를 의심하고 확인한다 | 결정하고 승인한다 | 단계를 밟는다 |
| 화면 | 오늘의 발견 · 떡상 · 시계열 · Outlier 분포 · 검색어 관리 · 채널 검증 · Watchlist · quota · 스케줄러 | 오늘의 추천 3~5 · MAKE/WATCH/SKIP + 근거/반대근거 · 승인 · 과거 결정 · 성과 리뷰 · 질의 | 1~16단계 + wiki |
| 겹치는 것 | 「오늘의 발견」의 **판단 부분**만 Strategist 로 이동 | | 3단계 소재입력이 brief.json 수용으로 **줄어듦** |

**Radar 의 「오늘의 발견」 탭은 없애지 않는다.** 다만 그 안의
「📋 Claude 웹으로 넘기기」·「🎬 제작 후보로 확정하기」 두 블록이 Strategist 로 옮겨
간다. Radar 에는 «무엇이 눈에 띄는가» 만 남는다.

---

## 5. 연결 지점 — 실제로 손대는 코드

| # | 연결 | 방식 | Radar | Strategist | AutoMaker |
|---|---|---|---|---|---|
| 1 | ChannelProfile 합본 | 파일 | `channels.py` 읽기 확장 | 읽기 | **변경 없음** (export 로 `genres.json` 생성) |
| 2 | Opportunity 내보내기 | JSONL | 신규 모듈 1개 | 읽기 | — |
| 3 | 결정 → 브리프 | JSON+MD | `production_brief` 에 json 출력 추가 | 쓰기 | — |
| 4 | 브리프 → 프로젝트 | 파일 | — | 프로젝트 폴더에 `brief.json` 배치 | 3단계 화면이 있으면 읽는다 (**HTML 소폭 수정**) |
| 5 | 프로젝트 → 결정 역참조 | project.json 3필드 | — | 읽기 | **변경 없음** (병합 저장이 지켜 준다) |
| 6 | 게시 URL 입력 | 한 칸 | — | 쓰기 | 16단계에 입력칸 1개 (**HTML 소폭 수정**) |
| 7 | 성과 수집 | CSV | `snapshot_collector` 재사용 | 읽기 | — |

**AutoMaker 의 `App.py` 는 한 줄도 고치지 않아도 1·2·3·5·7 이 성립한다.**
4·6 만 HTML 소폭 수정이 필요하고, 그것마저 «수동 붙여넣기» 로 대체 가능하다.

---

## 6. 플랫폼 확장 — Core / Adapter

지금 통합하지 않는다. **구조만 비워 둔다.**

```
ContentCore                       (brief · script · assets · angle)
   ├─ YouTubeLongformAdapter      ← 지금 유일하게 실제로 쓰는 것
   ├─ YouTubeShortsAdapter        ← AutoMaker 14단계가 이미 만든다. 게시만 수동
   ├─ InstagramAdapter            ← 없음
   └─ ThreadsAdapter              ← 없음
```

**판단 근거:** 플랫폼마다 성공 지표가 다르다(롱폼=시청유지, 숏폼=시청완료율,
Threads=댓글). Radar 의 Video Score 는 **롱폼 전용 설계**다(`LONGFORM_MIN_SECONDS=600`).
숏폼에 그대로 쓰면 틀린다. 지금 필요한 것은 어댑터가 아니라
**`Publication.format` 필드 하나**다. 그것만 있으면 나중에 나눌 수 있다.

---

## 7. 사람이 개입하는 지점 (확정)

| 자동으로 넘어감 | AI 보조 + 사람 승인 | 강한 사람 승인 |
|---|---|---|
| 수집 · 스냅샷 | MAKE/WATCH/SKIP | **최종 대본** |
| 점수 계산 | 채널 선택 | **Fact Check 통과** |
| 규칙 1차 선별 | Angle | **업로드** |
| Evidence 수집(고른 것만) | 제목 방향 | **채널 프로필 변경** |
| 성과 스냅샷 | Production Brief | **검색어 추가/삭제** |
| Opportunity 생성 | 오늘의 브리핑 | **API 비용 한도 변경** |

**자동 업로드는 만들지 않는다.** 되돌릴 수 없고, 잘못 올라간 연금·세금 설명은
조회수가 아니라 사람에게 손해를 끼친다.

---

## 8. 이 구조가 실제로 좋아지게 하는 것

기술적으로 «연결됐다» 가 아니라 **사용자의 무엇이 줄어드는가**로 적는다.

| 지금 | 이후 | 근거 |
|---|---|---|
| 표를 읽고 머릿속으로 판단 · 기록 없음 | 결정과 근거가 파일로 남는다 | StrategyDecision |
| 화면→Claude→파일→AutoMaker 4회 복사 | 파일 1개 전달 | brief.json |
| AutoMaker 가 소재를 다시 분석 (LLM 2~4회) | `skip_reanalysis` 로 생략 | 3단계 라우트 |
| 채널 정체성 2곳 관리 | 1곳 | ChannelProfile |
| 게시 후 아무것도 모름 | 24h/72h/7d 자동 관측 | snapshot_collector 재사용 |
| «전에 이거 만들었나?» 를 기억에 의존 | 조회 가능 | decisions + publications |

**반대로 새로 생기는 복잡성도 적는다.**

- 프로세스가 2개에서 3개로 는다 (Radar·Strategist·AutoMaker).
- 파일 종류가 는다 (opportunities · decisions · snapshots · publications · outcomes).
- 계약을 어기면 조용히 실패한다 — Radar 의 «이 프로그램의 실패는 조용하다»(prd §10-④)
  가 계약 층에도 그대로 적용된다. **각 계약 파일에 스키마 검증 테스트가 필요하다.**
