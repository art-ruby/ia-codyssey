# Decision Assistant v2 사전 시스템 감사

2026-09-11 · 읽기 전용 감사 · **코드·설정·데이터를 수정하지 않았다. 이 문서가 유일한 산출물이다.**

대상 저장소 (모두 실측):

| 시스템 | 경로 | 브랜치 / HEAD |
|---|---|---|
| RADAR | `C:\Lapisai` | `codex/selective-binding` f57779c |
| AutoMaker (운영 체크아웃) | `C:\automaker` | `codex/flow-receipts` 90ab15e |
| AutoMaker (RADAR 수신 상태가 있는 워크트리) | `C:\ai-worktrees\automaker-integration` | `codex/automaker-integration` fc52141 — `.automaker-runtime.json` 이 여기를 가리킨다 |
| Decision Assistant v1 | `C:\ia-codyssey\assignments\M1-2\m1-2-decision-assistant` | `automaker` |

표기: **[측정]** 파일·행수·DB 를 직접 확인 · **[코드]** 소스 확인 · **[문서]** 기존 감사·설계 문서 인용 · **[추정]** 근거는 있으나 미측정 · **확인 불가** 는 그대로 적었다.

---

# A. 한 문장 결론

**현재 Decision Assistant v1 은 실제 RADAR 와 연결된 적이 없는(168건 전부 표본) 「점수 상위 조회 챗봇」이며, 의사결정 계층이 되기 위해 필요한 네 입력(시장 신호·채널 DNA·제작 이력·성과) 가운데 시장 신호는 RADAR 에 이미 구조화되어 있고, 채널 정의는 세 곳에 흩어져 있고, 제작 이력은 AutoMaker 에 부분적으로 있고, 성과는 어디에도 없다 — 그러나 이 넷을 잇는 열쇠(`video_id` → `package_id` → `project.json.radar_intake`)는 이미 존재하므로 v1 을 버릴 필요 없이 «읽는 곳» 을 바꾸고 «결정 기록의 정본» 을 하나로 합치면 v2 로 갈 수 있다.**

---

# B. 현재 시스템 구조 (실측 기반)

```text
┌─────────────────────────── RADAR (C:\Lapisai) ────────────────────────────┐
│ collector.py ──▶ data/raw/videos.csv        1,628건 · 966채널  [측정]        │
│ snapshot_collector ─▶ data/raw/video_snapshots.csv 10,747행 · 1,398영상       │
│ signals.py ──▶ data/raw/signal_history.csv  4,305행 · 1,262영상 · 회차별 점수  │
│ analysis.build() ─ 읽을 때마다 재계산 ─▶ video_score · sub_tier · grade        │
│ channel_fit.py (LLM) ─▶ processed/channel_fit.csv        5행                  │
│ comments.analyze ─▶ processed/comments/*.json            4건                  │
│ production_brief ─▶ data/briefs/{ch}/{vid}.md            3건                  │
│ channel_dna.py ──▶ data/dna/{UC…}.json                   1건 (벤치마크 채널)   │
│ data/config/channels.json  ── loss_defense · solo_pride (production_enabled=false) │
│ decisions.py  ── MAKE/WATCH/SKIP freeze  ──▶ data/decisions.jsonl  **파일 없음** │
│ publications.py / own_performance.py / outcomes.py  ──▶ **파일 없음 (3종 모두)** │
│ automaker_intake.py ─ package(schema v2 + production_signals) ─▶ 루프백 HTTP   │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │ POST /api/radar/intake (127.0.0.1:5300)
                                    │ 실제 수신 1건 · schema_version **1** (v2 아님) [측정]
┌───────────────────────────────────▼───────────────────────────────────────┐
│ AutoMaker  radar_intake.py ─▶ .radar-intake/intake.sqlite3                  │
│    packages(1) · mappings(1: loss_defense→"radar-loss_defense", mode=new)     │
│ materialize ─▶ output/RADAR_<pkg>/project.json  (radar_intake{package_id,…})  │
│    progress {genre,source,channel,script,tts,images,videos,clips,titles,      │
│              description,last_step}  — 업로드·완료·youtube_video_id **없음**    │
│ genres.json ─ 채널 1개 (id=1 「일본 시니어 힐링 인문학」) — RADAR 채널과 미연결     │
│ selective_dna.py ─ data/dna/*.json 을 allowlist 필드로 «선택 적용»             │
│ 15/16 등록가이드 ─ 사람이 수동 업로드. 성과 수집 코드 0건 [코드]                  │
└───────────────────────────────────────────────────────────────────────────┘

┌──────────── Decision Assistant v1 (M1-2) ────────────┐
│ adapters/sources.py                                     │
│   SampleSource ─▶ sample_data/candidates.json 168건 ─── 화면의 168건 = 이것  │
│   RadarSource  ─▶ {RADAR_ROOT}/outbox/*.json  ← **RADAR 에 이 경로 없음**     │
│                   payload.demand / payload.discovery ← **RADAR v2 는 다른 위치**│
│ store (memory | firestore) ─▶ summary.build_summary ─▶ chat.select_candidates │
│ ─▶ OpenAI ─▶ conversations ─▶ PATCH decision ─▶ handoff/*.json (읽는 쪽 없음) │
└─────────────────────────────────────────────────────────┘
```

**세 시스템 사이에 Decision Assistant 가 실제로 꽂혀 있는 선은 0개다.** RADAR→AutoMaker 직결선은 1회 동작했다(package `radar-1fa02883…`, 2026-09-10).

---

# C. RADAR 감사 결과

## C-1. Source of Truth

| 정보 | 파일 | 규모 [측정] | 성격 |
|---|---|---|---|
| 영상 고정 정보 | `data/raw/videos.csv` | **1,628행** (unique video_id 1,628 · channel_id 966) · published 2026-06-03~09-10 · found_at 2026-09-01~09-10 | append-only, video_id 중복 차단 (`storage.append_videos`) |
| 시간 변화 정보 | `data/raw/video_snapshots.csv` | 10,747행 · 1,398영상 · 수집일 8일(09-01·02·03·06·07·08·09·10) · 영상당 1~16회 | append-only |
| 신호 이력 | `data/raw/signal_history.csv` | 4,305행 · 1,262영상 · observed_at 09-02~09-10 · rules_version 전부 1 | append-only, 회차별 `video_score`·`vph`·`rise_rank`·`signal_stage`·`velocity_trend` |
| 검색어 | `data/raw/seeds.json` | 상위 seed: 熟年離婚 195 · 年金暮らし 139 · 定年後 109 · 親の介護 101 … | 사람이 화면에서 관리 |

> ⚠️ 기존 감사(`docs/2026-09-10-radar-architecture-product-audit.md`)의 「videos.csv 26,882행」은 `wc -l` 값이다. description 이 여러 줄이라 **실제 레코드는 1,628건**이다. 이 문서에서 «후보 수» 는 1,628 을 기준으로 한다.

**점수는 파일에 없다.** `analysis.build()` 가 읽을 때마다 그 시점 모집단으로 백분위를 다시 낸다 (`src/analysis.py:253`). 점수의 «그때 값» 이 남는 곳은 두 군데뿐 — `signal_history.csv` 의 회차별 `video_score` 열, 그리고 `decisions.jsonl` 의 `metrics` (파일 없음).

## C-2. 조사 기준 항목 — 있는 것 / 없는 것

| 항목 | 존재 | 위치 (필드명 실제) |
|---|---|---|
| 후보 ID | ✅ | `video_id` (YouTube 11자). 패키지 단위는 `package_id = 'radar-'+sha([channel_id, video_id, input_type])[:32]` (`automaker_intake.py:92`) |
| 수집 시각 | ✅ | `found_at` (videos.csv) · `collected_at` (snapshots) · `observed_at` (signal_history) |
| 영상 ID / 채널 ID / 채널명 / 제목 | ✅ | `video_id`·`channel_id`(UC…)·`channel_name`·`title`·`title_ko` |
| 주제 | 🔶 | `seed`(검색어) 만 저장. 주제 분류는 `patterns.find()` 가 제목 낱말로 **실행 시 계산**, 파일 없음. `config.PILLARS` 4개는 seed 에 붙는 구획 |
| 키워드 | 🔶 | `similar.tokens()`/`seeds._chunks` 로 실행 시 추출. 저장 안 함 |
| 조회수·좋아요·댓글·구독자 | ✅ | snapshots: `views`·`likes`·`comments`·`channel_subscribers`·`channel_video_count`·`hidden_subscriber_count` |
| 게시일 / 영상 나이 | ✅ | `published_at` 저장, `age_days`·`age_bucket` 계산 |
| 상승 속도 | ✅ | signal_history: `view_gain`·`elapsed_hours`·`vph`·`prev_vph`·`velocity_change`·`velocity_trend`(가속/둔화/유지) |
| 조회수 대비 구독자 | ✅ | `subscriber_view_ratio` (구독 1,000 미만·비공개·매크 의심은 결측, `ratio_missing_why` 에 사유) |
| score | ✅(계산) | `video_score = age_adjusted_percentile×0.6 + svr_percentile×0.4` (`analysis.add_scores`) |
| score 구성요소 | ✅ | `age_adjusted_percentile`·`percentile_method`·`svr_percentile`·가중치(`config.W_*`). v2 payload 의 `production_signals.demand.components/weights` 에 실린다 |
| trend | ✅ | `signal_stage`(초기 상승/상승 관찰/지속 상승/장기 지속) + `velocity_trend`. 실측 분포: 상승 관찰 1,863 · 초기 상승 1,586 · 지속 상승 856 · 장기 지속 **0** |
| gap | 🔶 | `gaps.collect()` — `processed/comments/*.json`(4건) 의 `unresolved_gaps`·`next_video_questions` 를 모음. 댓글 받은 영상에만 존재 |
| pattern | 🔶 | `patterns.find(df)` — 실행 시 계산 (MIN_VIDEOS 3 · MIN_CHANNELS 3 · RECENT_DAYS 30). 파일 없음 |
| evidence | 🔶 | `evidence.have()` — 파일 존재 여부 5종(gain/channel/subtitle/comments/fit). «사실 검증» 이 아니라 «자료 보유 여부» |
| language / country | ✅ | `default_audio_language`·`detected_language`·`kana_ratio`; region 은 검색조건(JP) 이라 행에 없음 |
| source | ✅ | 전부 YouTube Data API v3 |
| target channel | ✅ | `data/config/channels.json` 의 `id` (loss_defense · solo_pride) — 후보 행이 아니라 **브리프·결정·패키지 단위**에 붙는다 |
| MAKE/WATCH/SKIP | ✅(코드) ❌(데이터) | `decisions.freeze(decision=…)` + `app.py:881` selectbox. **`data/decisions.jsonl` 없음** [측정] |

## C-3. 반드시 답할 질문

1. **Source of Truth** — `data/raw/videos.csv` + `video_snapshots.csv` 두 CSV. 점수·등급·패턴은 파생값이며 저장되지 않는다(신호 이력·결정 동결 제외).
2. **안정적 ID** — `video_id`. 채널 맥락까지 포함한 식별자는 `(channel_id, video_id)` 쌍이고, 그것을 해시한 `package_id` 가 AutoMaker 까지 그대로 간다. `decision_id = 'dec_'+sha([channel_id, video_id, revision])` (`decisions.py:184`).
3. **score 계산 위치** — `src/analysis.py` `add_metrics → add_age_adjusted → add_scores → add_opportunity`. 다른 곳에서 재계산하지 않는다 (`production_signals.py:1` "No new score").
4. **재현 가능성** — **부분.** 구성요소·가중치·`config_digest`·`code_version` 은 남지만, 백분위는 «그때의 모집단» 에 의존한다. `decisions.population_of()` 는 `n_videos`·`n_scored` 두 숫자만 남긴다. 완전 재현은 불가, 근사 재현은 가능.
5. **시점별 score** — ✅ `signal_history.csv` 에 회차별 `video_score` 가 남는다 (2026-09-02 이후). 단 «gain 이 계산된 회차» 만 적히므로 스냅샷 1회짜리 영상(124건)은 이력이 없다.
6. **후보 history** — ✅ snapshots(원값) + signal_history(파생). 영상당 중앙값 5~8회 관측.
7. **trend 계산 가능 데이터** — ✅ 있다. 다만 관측 간격 중앙값 ≈ 8~10시간이라 `FULL_DAY_HOURS` 미만 관측은 `is_early` 로 «초기 신호» 취급 (`config.py:105-117` 실측 주석).
8. **evidence/gap/pattern 구조화** — 실행 시 dict 로 구조화된다 (`production_signals.snapshot()` schema_version 1: discovery·demand·patterns·similar·gaps·evidence·channel_fit). **파일로는 없고 v2 payload 에만 실린다.**
9. **RADAR 가 이미 MAKE/WATCH/SKIP 을 하는가** — **코드와 화면은 있다.** 브리프 화면에서 결정을 고르고 `decisions.freeze` 로 얼린다. 그러나 실제 파일이 생성된 적이 없다 → 운영에서 쓰인 적 없음.
10. **DA v1 이 중복하는 부분** — §G-4 참조. 요약: 후보 목록·점수 정렬·요약 통계·결정 기록·handoff 5가지.

---

# D. Channel DNA 감사 결과

## D-1. 채널 관련 정의가 있는 곳 — 전수 [측정]

| # | 파일 | 무엇을 정의하나 | 작성 주체 | 소비 주체 | 사용 중 | SoT 여부 |
|---|---|---|---|---|---|---|
| 1 | RADAR `data/config/channels.json` | **제작 채널 2개** (`loss_defense`·`solo_pride`): `name_ko/ja`·`emoji`·`audience`(50-69)·`promise_ko`·`core_question_ko`·`tone_ko`·`discovery_enabled`·`production_enabled`(**둘 다 false**)·`profile_version`(2)·`lenses[]` | 사람 (RADAR 설계자) | `channels.py`·`channel_fit.judge`·`production_brief`·`automaker_intake.build_payload`(→`payload.target_channel` 통째로) | ✅ | RADAR 안에서는 SoT. AutoMaker 는 `name_ko` 만 씀 (`radar_intake.py:264`) |
| 2 | RADAR `data/dna/UCjlh_Ko4lEpJIqftz5mxNXQ.json` | **벤치마크 채널** 人生の果実【漫画】 의 패턴 13개(1_TITLE…11_EMOTION + 6_THUMBNAIL_COPY/LAYOUT/COLOR)·`channel_persona`·`videos_used`(2건)·`prompt_version` v3·`repeat_confirmed` true | RADAR LLM (`channel_dna.run`) | AutoMaker `selective_dna.py` — 제작 채널 확정 후 allowlist 필드에만 사람이 체크해 적용 | ✅ (1건) | 벤치마크 근거의 SoT. **제작 DNA 아님** |
| 3 | RADAR `data/processed/channel_fit.csv` | 영상×채널×profile_version 별 HIGH/MED/LOW 7항목 + `reason`·`angle_ko` | RADAR LLM | `production_brief`·`production_signals.channel_fit` | 🔶 5행 | 판정 캐시. SoT 아님 |
| 4 | RADAR `data/briefs/{ch}/{vid}.md` 머리말 | Channel Profile 블록을 산문으로 복사 | `production_brief.build` | AutoMaker `source.contentText`, NotebookLM | ✅ 3건 | 사본. #1 의 복제 |
| 5 | AutoMaker `genres.json` | **AutoMaker 제작 채널 1개** (`id: 1`, 「🇯🇵 일본 시니어 힐링 인문학」): `channelPersona`(+Raw)·`viewerPersona`·`titlePatterns`·`scriptStructure`·`speakingStyle`·`forbiddenPatterns`·`thumbnailPatterns`·`commentEmotion`·`ctrHooking`·`retentionBridge`·`emotionTemperature`·`localization`(##4_LOCAL## 원문)·`speakerConfig`(VOICEVOX 화자 2명)·`benchmarkLinks`(→ `0YuPs8cbmMo`)·`notebookLmUrl`·`status: ready` | 사람 + NotebookLM 12단계 | `App.py` 대본·TTS·썸네일 생성, `radar_intake.choices()` | ✅ | AutoMaker 전역 채널의 SoT (legacy) |
| 6 | AutoMaker `output/*/project.json.genre` | 프로젝트별 채널 스냅샷 (승인 Persona `persona_approval`·`radar_draft`) | intake materialize / 사용자 승인 | guarded 생성 API (`production_identity.py`) | ✅ | **승인 Persona 의 SoT** — e2e 감사 §C [문서] |
| 7 | AutoMaker `.radar-intake/intake.sqlite3` `mappings` | RADAR 채널 id → AutoMaker 채널 매핑 (`loss_defense` → `radar-loss_defense`, mode `new`) | 사용자 (바인딩 화면) | `project_channel_binding.py` | ✅ 1행 | 매핑의 SoT |
| 8 | AutoMaker `radar_senior_healing_config.json` · `AUTOMAKER_일본_시니어_힐링_채널_페르소나.md` 등 | 시니어 힐링 채널 설계 산문 | 사람 | 확인 불가 (코드 소비처 grep 0) | ❓ | 문서 |
| 9 | DA `sample_data/generate.py` `CHANNELS` | `loss_defense`·`solo_pride` 의 라벨·주제 8+7개 하드코딩 | DA 개발자 | 표본 생성 전용 | 표본 | SoT 아님 (복제) |

## D-2. 항목별 존재 여부 (제작 채널 기준)

| 항목 | RADAR channels.json | AutoMaker genres.json | project.json.genre |
|---|---|---|---|
| 채널 목적 | `promise_ko` ✅ | `desc`·`channelPersonaRaw.extras.identity` ✅ | 승인 후 ✅ |
| 타깃 시청자 | `audience: "50-69"` ✅ | `viewerPersona` ✅ | ✅ |
| 핵심 문제 | `core_question_ko` ✅ | — (identity 에 산문) | — |
| 핵심 감정 | — | `emotionTemperature`·`extras.emotion` ✅ | ✅ |
| 콘텐츠 pillar | `lenses[]` ✅ (7/6개) | — | — |
| 금지/제외 주제 | — (브리프의 ■금지 블록은 공통 문구) | `forbiddenPatterns` ✅ | ✅ |
| 톤 | `tone_ko` ✅ | `speakingStyle`·`extras.tone` ✅ | ✅ |
| 표현 방식 / 스토리 구조 | — | `scriptStructure`·`structureType: STORY` ✅ | ✅ |
| 영상 길이 | — | — | 확인 불가 |
| 제목 스타일 / 썸네일 방향 | — | `titlePatterns`·`thumbnailPatterns` ✅ | ✅ |
| 주제 비율 / 최근 전략 | — | — | — |
| 벤치마크 | (dna/*.json 별도) | `benchmarkLinks` ✅ | `benchmark_dna`(선택 적용 시) |
| Persona / DNA | — | `channelPersona` ✅ | `channelPersona`+`persona_approval` ✅ |

## D-3. 반드시 답할 질문

1. **공식 SoT 가 있는가** — **없다. 두 벌이다.** RADAR 는 «발굴 관점의 채널 약속»(channels.json), AutoMaker 는 «제작 관점의 스타일 사양»(genres.json / project.genre). 항목이 거의 겹치지 않아 «중복» 이라기보다 **«반쪽씩»** 이다.
2. **같은 채널 정의를 쓰는가** — **아니다.** AutoMaker 가 RADAR 에서 받는 것은 `target_channel.name_ko` 한 줄뿐 (`radar_intake.py:264,287`). `promise_ko`·`tone_ko`·`lenses` 는 project.json 어디에도 저장되지 않는다. 브리프 산문(`source.contentText`) 안에만 있다 — e2e 감사 §B «NotebookLM에 실제 전달되는 RADAR 필드» [문서] 와 일치.
3. **중복 존재** — 시청자(50-69 ↔ viewerPersona), 톤(tone_ko ↔ speakingStyle) 정도. 나머지는 상호 배타.
4. **다른 값 가능성** — **이미 다르다.** RADAR 두 채널은 `production_enabled=false`(업로드 전) 인데 AutoMaker 유일 채널 `id=1` 은 `status: ready` 이고 RADAR 어느 채널과도 매핑되어 있지 않다(`mappings` 에 `loss_defense→radar-loss_defense(new)` 만 있음). 즉 **RADAR 의 2채널과 AutoMaker 의 1채널은 서로 다른 실체**다.
5. **DA 가 Channel DNA 를 읽는가** — **못 읽는다.** DA Candidate 에는 `channel: str` 문자열만 있다 (`schemas.py:49`). 프로필을 읽는 코드가 없다.
6. **내부 채널 ID ↔ 제작 채널 연결** — `loss_defense` → AutoMaker `radar-loss_defense` (Persona 미승인, `radar_draft: true`) 1건. `solo_pride` → 매핑 없음. `genres.json id=1` → RADAR 채널 없음. **연결 완성도 1/3.**
7. **벤치마크 DNA ↔ 제작 DNA 혼동 가능성** — **실제로 혼동된 흔적이 있다.** `C:\automaker\output\20260903 人生の果実【漫画】` 는 **벤치마크 채널명**을 프로젝트 이름으로 쓰고 있고 `genre.id=1` 에 묶여 있다. `genres.json.benchmarkLinks` 도 같은 영상(`0YuPs8cbmMo`)이다. 2026-09-11 selective-binding 작업이 «DNA 는 제작 채널 확정 후 선택 적용» 으로 막았지만(`selective_dna.py:1` "never determines the production channel"), 기존 프로젝트는 그 전에 만들어졌다.

---

# E. AutoMaker 제작 이력 감사

## E-1. 제작 단계 (실제 필드명)

`project.json.progress` [측정]:
```json
{"genre":false,"source":false,"channel":false,"script":false,"tts":false,
 "images":false,"videos":false,"clips":false,"titles":false,"description":false,"last_step":2}
```
화면 번호(pages/): 0메인·1프로젝트관리·2채널설정·3콘텐츠소스·4제목선택·5화자설정·6대본생성·7TTS·8이미지·9영상·10BGM·11영상조합·12제목썸네일·13설명태그·14숏폼·**15/16 등록가이드(수동 안내)**.
새 경로(e2e 감사 §A [문서]): `.research/`(NotebookLM)·`.visual/zero-style/`·`.visual/generation/`·`.python/`(Master)·Hook 검수 기록.

**«업로드」·「완료」 단계는 데이터 모델에 없다.** `youtube_video_id`·`upload_status`·`published_at`·`completed_at` 필드는 `*.py` 전체에서 0건 [grep 측정]. `App.py` 의 youtube 관련 61건은 전부 **소스 영상**(yt_dlp 메타·자막·댓글·썸네일) 용도다.

## E-2. 추적 가능 항목

| 항목 | 존재 | 위치 |
|---|---|---|
| radar_id(video_id) | 🔶 | `project.json` 최상위에는 없음. `radar_intake.package_id` 로 `.radar-intake/<rev>.json` 의 `payload.opportunity_id` 를 열어야 나온다 |
| project_id | 🔶 | 디렉터리 경로가 곧 ID. 연구/ZeroStyle/VisualPlan 은 각자 다른 id(경로 digest·UUID) — e2e 감사 §C «project identity 세 형태» [문서] |
| channel | ✅ | `channel_id`·`genre.id`·`channel_binding{state, radar_channel_id, selection_kind}` |
| topic / title | ✅ | `name`(=RADAR topic)·`titles`·`selected_title` |
| 선택일 | 🔶 | `created`(YYYY-MM-DD)·intake `audit.at`·`channel_binding.bound_at` |
| 제작 시작일 / 현재 단계 | ✅ | `created`·`progress.last_step`·`last_accessed` |
| 완료일 · 영상 파일 · 업로드 상태 · YouTube video id · 실패/중단 | ❌ | 없음. `.python/` masters 존재 여부로 렌더 완료만 추정 가능 |
| 스크립트 | ✅ | `script`·`script.json`·`script_edit.txt` |

## E-3. 실제 프로젝트 인벤토리 [측정]

| 위치 | 프로젝트 | last_step | channel_id | radar_intake |
|---|---|---|---|---|
| `C:\automaker\output` | 20260903 人生の果実【漫画】 | 6 | (빈값) · genre.id=1 | 없음 |
| 〃 | 20260910 シニアの整え知恵 ×2 (공백 유무 중복 디렉터리) | 2 | (빈값) | 없음 |
| 〃 | LOCAL_TEST_* ×7 | — | — | 테스트 |
| `automaker-integration\output` | RADAR_1fa02883… (0YuPs8cbmMo → loss_defense) | 3 | `radar-loss_defense` (Persona 미승인) | ✅ rev 1 |
| 〃 | 20260911 P0 채널연결 검증 · 20260910 シニアの整え知恵 | — | — | 검증용 |

## E-4. 반드시 답할 질문

1. **어떤 RADAR 후보가 제작됐는지 연결** — 🔶 **구조는 있다 (`intake.sqlite3.packages.project` + `project.json.radar_intake`). 실적은 1건, 그것도 Persona 미승인·조사 0·Visual 0 이라 «제작됨» 이 아니다.** 나머지 3개 실프로젝트는 RADAR 연결 없이 수동 생성.
2. **유사 소재 과거 제작 여부** — ❌ **불가.** AutoMaker 에 프로젝트 간 주제 색인이 없다. `wiki/_wiki_vid_ids.json` 은 «학습한 소스 영상» 목록이지 제작물 목록이 아니다 (`App.py:5148`). RADAR `similar.py`/`patterns.py` 는 **남의 영상** 모집단 위에서만 돈다.
3. **최근 N개 제작물 주제 구성** — ❌ 제작물 자체가 0~1건. 계산할 데이터 없음.
4. **채널별 제작 빈도** — ❌ 위와 동일. `created` 로 셀 수는 있으나 «완료» 정의가 없다.
5. **제작 중 vs 미제작 구분** — 🔶 `progress.last_step` 과 `.python/` 존재로 근사. 명시적 상태 머신 없음.
6. **중복 제작 방지 데이터** — ❌ 없음. `ai-strategist-boundary.md §4 F` 도 «제작 이력 0건이라 지금 만들면 항상 없음만 답한다» 고 보류 [문서].
7. **DA 가 읽을 수 있는 안정적 인터페이스** — 🔶 HTTP: `project_channel_binding.py` 의 Blueprint(`create_project_channel_binding_api`), `radar_intake_api.py`(inbox/choices/mappings). 파일: `intake.sqlite3`(3 테이블) + `project.json`. **읽기 전용 «프로젝트 목록+상태» API 는 없다** — 확인 범위 내(`App.py` 17,477줄 전수는 아님).
8. **Handoff ↔ AutoMaker 연결 키** — RADAR 경로: ✅ `package_id`·`payload_hash`·`revision`·`opportunity_id`. **DA 경로: ❌** — DA `handoff/*.json` 은 `radar_id`·`candidate_id`(DA 내부 UUID) 만 있고 `package_id` 가 없으며, AutoMaker 에 이 파일을 읽는 코드가 없다.

---

# F. YouTube 실제 성과 감사

## F-1. 수집 코드와 데이터

| 시스템 | 코드 | 데이터 파일 | 상태 [측정] |
|---|---|---|---|
| RADAR | `publications.py` (게시 기록, `publication_id=pub_<vid>`·`youtube_video_id`·`channel_id`·`format`·`published_at`·`source_video_id`) | `data/publications.jsonl` | **없음** |
| RADAR | `own_performance.py` (videos.list → `views`·`likes`·`comments`·`hours_since_publish`·`bucket` 24h/72h/7d/30d) | `data/raw/own_snapshots.csv` | **없음** |
| RADAR | `outcomes.py` (decisions+publications+own_snapshots 조인, `MIN_SAMPLES=10`, HIT_X 1.5 / MISS_X 0.5) | 파생 | 입력 3개 중 3개 없음 |
| RADAR | `tracked.py` (추적 채널 업로드) | `data/config/tracked_channels.json` · `processed/tracked_uploads.csv` | **없음** |
| AutoMaker | — | — | 성과 수집 코드 없음 (grep 0) |
| DA | — | — | 없음 |

## F-2. 지표별

| 지표 | 상태 |
|---|---|
| video_id · channel_id · published_at | 코드 있음(publications) · 데이터 없음 |
| views · likes · comments | 코드 있음(own_performance, Data API videos.list) · 데이터 없음 |
| impressions · CTR · AVD · APV · watch time · subscriber gain · retention | **코드도 없음.** `own_performance.py:13` 이 명시: «YouTube Analytics API(OAuth) 는 지금 단계에서 붙이지 않는다» |
| 조회수 변화 / 시간별 snapshot | 코드 있음(bucket 4단) · 데이터 없음 |

## F-3. 반드시 답할 질문

1. **수집되고 있는가** — **아니다.** 근본 원인: 아직 업로드된 영상이 없다. `channels.json` 두 채널 모두 `production_enabled: false`, 브리프 머리말에 «이 채널은 아직 실제 업로드 전» [측정].
2. **어느 수준까지 가능한가** — 게시 기록 한 줄만 적으면 Data API 로 조회수·좋아요·댓글은 하루 1 unit 으로 즉시 쌓인다. CTR·시청유지는 OAuth 작업 필요.
3. **영상 ↔ RADAR 후보 연결** — 설계됨: `publications.source_video_id`(원 소재 video_id). 데이터 없음.
4. **제작 전 판단 ↔ 제작 후 결과 비교** — 설계됨(`outcomes.build`). `decisions.jsonl` 도 없어 양쪽 다 비어 있다.
5. **시계열 성과 저장** — 설계됨(bucket). 데이터 없음.
6. **학습/평가 가능 수준인가** — **아니다.** `outcomes.MIN_SAMPLES=10` 전에는 `verdict=unknown` 으로 설계돼 있고, 현재 0건.
7. **가장 큰 공백** — **게시 기록(publications.jsonl) 한 줄이 없다.** 이것이 없으면 뒤의 모든 것이 0 이다. 두 번째는 AutoMaker 가 «업로드 완료» 를 어디에도 적지 않는 것.

---

# G. Decision Assistant v1 감사

## G-1. 실제 흐름 (파일 · 함수 · 입출력)

| 단계 | 파일 / 함수 | 입력 | 출력 | 데이터 source |
|---|---|---|---|---|
| import | `routers/data.py:import_candidates` → `adapters/sources.build_source(name)` | `?source=sample\|radar&replace=` | store 에 Candidate dict 저장 | `SampleSource`: `sample_data/candidates.json` · `RadarSource`: `{RADAR_ROOT}/outbox/*.json` → `data/decisions.jsonl` |
| 저장 | `repositories/store.py` `InMemoryStore` / `FirestoreStore` | Candidate(`id`·`date`·`value`·`memo`·`radar_id`·`channel`·`topic`·`title`·`radar_score`·`decision`·`decision_reason`·`source`) | — | 현재 실행: **memory** (`/api/health store: memory` [측정]) |
| summary | `services/summary.build_summary` | 전 후보 | `Summary{period,count,metrics,trend,decisions,top_topics,channels,source_mix}` | `date` 1개/후보 |
| retrieval | `services/chat.select_candidates` | 질문 + 전 후보 | ≤25건 + basis(`decision`/`keyword`/`top_score`) | 질문 낱말 ↔ `channel`·`topic`·`title` 문자열 일치 |
| context | `services/chat.build_context_block` | Summary + 25건 | 번호 목록 + `[표본]/[실측]/[수동]` 태그 | — |
| GPT | `services/chat.generate_reply` | SYSTEM_RULES + context + history(≤8턴) | reply · model · `answer_source`(openai/rule_based/error_fallback) | Codyssey 게이트웨이 `gpt-5-mini` |
| conversation | `routers/chat.py` → `store.create/replace_conversation` | messages | conversation_id | memory/firestore |
| MAKE/WATCH/SKIP | `routers/data.py:set_decision` (PATCH `/api/data/{id}/decision`) | decision + reason | Candidate 갱신 | store |
| handoff | `services/handoff.build_record/write_record` | MAKE 후보 | `handoff/<stamp>_<radar_id>.json` (`HandoffRecord`) | 자기 디렉터리에만 씀 |

## G-2. 데이터 구성 [측정]

| 구분 | 건수 | 근거 |
|---|---|---|
| 실제 RADAR 원본 | **0** | `RADAR_ROOT` 미설정(`.env`) + 설정해도 §G-3 불일치로 0 |
| 표본 | **168** | `SAMPLE_0000`~`0167`, `generate.py` seed 20260911, 75일 분산, 점수 `betavariate` |
| 테스트 | 2 (smoke) | `handoff/20260910T162015_0b24…json` 등 `source: manual`·`radar_id: null` |
| 사용자 입력 | 0 (표본 위 decision 변경은 있음) | — |

## G-3. RadarSource 는 실제 RADAR 와 맞지 않는다 [코드]

| 항목 | DA `adapters/sources.py` 가 기대 | RADAR 실제 (`Lapisai`) |
|---|---|---|
| 패키지 위치 | `{root}/outbox/*.json` (`:151`) | `data/automaker-outbox/outbox.sqlite3` (`automaker_intake.py:96`) — 현재 로컬에 없음. AutoMaker 쪽 수신본은 `automaker-integration/.radar-intake/intake.sqlite3` |
| 점수 경로 | `payload.demand.video_score` (`:181,186`) | `payload.production_signals.demand.video_score` (`production_signals.py:77`) |
| 시점 경로 | `payload.discovery.observed_at` (`:193`) | `payload.production_signals.discovery.observed_at` (`:74`) |
| 결정 경로 | `payload.decision.{decision,note,metrics}` | ✅ 일치 (`automaker_intake.py:61-65`) — 단 항상 `None` |
| 스키마 | v2 필수 (`:176`) | 실제 송신·수신된 유일한 패키지는 **v1** [측정] |

`tests/test_units.py:136` 의 v2 픽스처가 DA 의 기대 모양이고, RADAR 의 실제 v2(`production_signals` 안에 중첩)와 다르다. **어댑터·테스트·문서(`README §14`)가 서로 일치하지만 셋 다 RADAR 실물과 다르다.**

## G-4. 반드시 답할 질문

1. **168 중 RADAR 원본** — 0.
2. **표본** — 168.
3. **섞이는가** — 같은 store·같은 summary 에 들어간다. 다만 `source` 열이 강제되고 `Summary.source_mix` 와 prompt 태그로 구분된다. 현재는 표본만 있어 «섞임» 자체가 발생하지 않았다.
4. **GPT 가 구분 가능한가** — 가능. 행마다 `[표본]/[실측]/[수동]` 태그 + SYSTEM_RULES 4항. 표본이 실측인 척하지 못하게 한 설계는 옳다.
5. **추천 = score 상위 정렬인가** — **사실상 그렇다.** `select_candidates` 는 (a) 질문에 MAKE/WATCH/SKIP 낱말 → 상태 필터, (b) 낱말 일치 → 관련도·점수순, (c) 아니면 점수 상위. 채널 적합성·이력·포화도 입력 없음.
6. **25건 기준** — `MAX_CANDIDATES_IN_PROMPT=25`, 위 (a)(b)(c) 순. `basis` 를 답변에 함께 돌려주는 점은 좋다(`selection_basis`).
7. **AI 가 보는 범위** — Summary + ≤25건. 168건 전체를 보지 않는다.
8. **«최근 상승»·«상위 주제» 가 시계열인가** — **아니다.** `summary._trend_label` 은 «최근 7일에 `date` 가 찍힌 후보들의 점수 평균» vs «그 전 7일 후보들의 평균» — 후보 집단 간 횡단 비교이지 어느 후보의 시간 변화도 아니다. 후보당 `date` 가 하나뿐이라 시계열이 성립하지 않는다. «상위 주제» 는 `topic` 빈도 상위 5. RADAR 의 `velocity_trend`·`signal_stage`·`patterns.recent` 같은 진짜 시간축 값은 DA 에 들어오지 않는다.
9. **RADAR 와 중복** — 후보 목록/필터 · 점수 정렬 · 요약 통계(RADAR `health`·`patterns`) · MAKE/WATCH/SKIP 기록(RADAR `decisions.freeze` 가 더 풍부: 동결 metrics·config_digest·revision·decision_id) · handoff(RADAR `automaker_intake` 가 hash·provenance·revision 계약 보유, DA 는 읽는 쪽 없는 JSON).
10. **DA 에만 있는 것** — 자연어 질의 + 대화 저장/불러오기 · Firestore 영속 옵션 · 웹 배포(Render/Vercel) · 결정 사유 자유 텍스트 · 프롬프트 주입 preview(`/api/chat/preview`, DEBUG). **의사결정 계층 고유 입력(채널 DNA·제작 이력·성과)은 아무것도 없다.**

## G-5. 강점 (지킬 것)

- 표본/실측 분리 원칙이 코드·API·프롬프트 세 층에서 일관됨 (`source` 강제, `is_real_data`, `[표본]` 태그).
- 키 없을 때 «조용한 가짜 답» 대신 규칙 기반으로 떨어지고 그 사실을 첫 줄에 밝힘 (`_rule_based_reply`).
- 후보 선별 근거(`selection_basis`)를 응답에 노출 → 환각 방어의 좋은 기초.
- 어댑터 경계(`CandidateSource`) 덕에 소스 교체 지점이 한 곳.

---

# H. ID / Data Lineage

```text
RADAR 후보        video_id (videos.csv)                                   ✅
   ↓              + channel_id ─▶ package_id = radar-sha(channel_id, video_id, input_type)
Decision          RADAR: decision_id = dec_sha(channel_id, video_id, revision) → decisions.jsonl  ❌ 파일 없음
                  DA:    candidate.id (UUID) + radar_id → handoff/*.json  (package_id 없음)        🔶
   ↓
AutoMaker Project project.json.radar_intake.{package_id, revision, payload_hash, radar_channel_id} ✅ (1건)
                  opportunity_id 는 .radar-intake/<rev>.json 안에만                              🔶
   ↓
YouTube Video     youtube_video_id — AutoMaker 어디에도 없음. RADAR publications.jsonl 설계만       ❌
   ↓
Performance       own_snapshots.csv — 없음                                                        ❌
```

실제 필드명 대응표:

| 개념 | RADAR | AutoMaker | DA |
|---|---|---|---|
| radar_candidate_id | `video_id` | `payload.opportunity_id` (archive 내부) | `radar_id` |
| channel_id (제작) | `channels.json.id` | `project.channel_id` = `radar-<id>` 또는 `genre.id`(1) · `radar_intake.radar_channel_id` | `channel` |
| project_id | — | 디렉터리 경로 · `radar_intake.package_id` | — |
| automaker_project_id | — | `intake.sqlite3.packages.project` (경로) | — |
| youtube_video_id | `publications.youtube_video_id` (설계) | — | — |
| decision_id | `decisions.decision_id` (설계) | — | `candidate.id` |
| conversation_id | — | — | `conversation.id` |

### 판정: **PARTIAL**

RADAR→AutoMaker 구간은 결정적 ID 와 hash 검증까지 갖춘 **PASS 수준의 설계**가 1건 실증됐다. Decision 구간은 두 시스템이 각자 기록하려 하고 둘 다 비어 있다. AutoMaker→YouTube→Performance 는 **FAIL** (키 자체가 없다). 한 소재를 끝까지 역추적하는 것은 현재 불가능하고, 성과가 생겨도 `youtube_video_id` 를 project.json 에 적는 자리가 없어 여전히 끊긴다.

---

# I. Source of Truth 표

| 정보 | 현재 위치 | 실제 소비처 | 문제 | 권장 SoT |
|---|---|---|---|---|
| RADAR 후보 | `Lapisai/data/raw/videos.csv` + `video_snapshots.csv` | analysis·signals·brief·intake | 점수는 파생·비저장 (의도된 설계) | **그대로.** DA 는 복제하지 말고 읽는다 |
| 채널 정의 (제작) | RADAR `channels.json`(2) ↔ AutoMaker `genres.json`(1) ↔ `project.json.genre` | 각자 | 서로 다른 실체·반쪽 정보·1/3 만 매핑 | **AutoMaker `project.json.genre`(승인 Persona) 를 «스타일·사양» SoT, RADAR `channels.json` 을 «약속·lens» SoT 로 역할 분리 + `mappings` 로 잇는다.** 하나로 합치지 않는다 (변경 주기가 다름) |
| 채널 DNA (벤치마크) | RADAR `data/dna/{UC}.json` | AutoMaker selective_dna | 제작 DNA 와 이름이 같아 혼동 | **RADAR.** 이름을 «benchmark DNA» 로 고정 표기 |
| 벤치마크 DNA | (위와 동일) | | | RADAR |
| Decision | RADAR `decisions.jsonl`(없음) · DA store+`handoff/*.json` | 아무도 안 읽음 | **이중 기록 예정지** | **RADAR `decisions.jsonl` 형식 하나.** DA 는 이 형식으로 쓰거나 이 파일에 append 한다. `decision_id`·`config_digest`·동결 metrics 가 있는 쪽이 정본 |
| 제작 프로젝트 | AutoMaker `output/*/project.json` | App.py | 경로가 ID · 여러 루트 | **AutoMaker.** 단 `radar_intake` 블록에 `opportunity_id` 승격 필요 |
| 제작 상태 | `project.json.progress` + `.python/` 존재 | App.py | 완료·업로드 상태 없음 | AutoMaker `progress` 확장 (`uploaded`, `youtube_video_id`) — **미래 구현, 지금은 없음** |
| 업로드된 영상 | 없음 | — | 게시 기록 부재 | RADAR `publications.jsonl` (이미 설계됨) — AutoMaker 가 업로드 시 한 줄 append 하거나 사람이 RADAR 화면에서 등록 |
| YouTube 성과 | 없음 | — | — | RADAR `own_snapshots.csv` (이미 설계됨) |
| AI 판단 기록 | DA `conversations` (memory) | DA 화면 | 재시작 시 소실 · decision 과 미연결 | DA Firestore `conversations` + 각 MAKE 에 `conversation_id`·`decision_id` 상호 참조 |

---

# J. 기능 책임 분리표

| 기능 | RADAR | Decision Assistant | AutoMaker | 중복 여부 | 권장 책임 주체 · 이유 |
|---|---|---|---|---|---|
| 후보 탐색 | ✅ collector·seeds·tracked | 🔶 목록 조회·필터 | ❌ | **중복(조회)** | **RADAR.** DA 는 RADAR 결과를 읽기만. 자체 목록 화면은 «결정 대기 큐» 로 좁힌다 |
| 점수 계산 | ✅ analysis | ❌ (value 복사) | ❌ | 없음 | **RADAR.** `ai-strategist-boundary §2.1` «숫자는 코드가» |
| 트렌드 | ✅ signals(vph·stage) | 🔶 횡단 평균(가짜 시계열) | ❌ | **중복(이름만)** | **RADAR.** DA 의 `_trend_label` 은 RADAR `signal_history` 로 대체 |
| 주제 분류 | 🔶 patterns(실행시) | 🔶 topic 문자열 빈도 | 🔶 wiki 구조유형 | 중복 | **RADAR** (시장 주제) + **AutoMaker** (제작 구조 유형). DA 는 둘을 조인만 |
| 채널 매칭 | ✅ channel_fit(LLM, 5건) | ❌ | ✅ binding(사람 확정) | 경계 모호 | **판정 재료는 RADAR, 확정은 AutoMaker binding.** DA 는 «이 채널에 맞나» 를 channel_fit + binding 상태로 **읽어서** 설명 |
| MAKE/WATCH/SKIP | ✅ decisions(코드만) | ✅ PATCH+handoff | ❌ | **정면 중복** | **DA 가 UI, RADAR decisions.jsonl 이 저장 형식.** 두 저장소를 두지 않는다 |
| 제작 이력 확인 | ❌ | ❌ | 🔶 project.json | 없음 | **AutoMaker** 가 «프로젝트 목록+상태» 읽기 API 를 내고 DA 가 소비 |
| 중복 소재 판정 | 🔶 similar(시장 내) | ❌ | ❌ | 없음 | **DA.** RADAR `similar.Index` 를 «후보 vs 제작이력» 에 적용하는 것이 DA 고유 가치. 제작이력 0건이라 지금은 «구조만» |
| 포트폴리오 판단 | ❌ | ❌ | ❌ | 없음 | **DA.** v2 의 존재 이유 |
| 성과 분석 | ✅ outcomes(코드만) | ❌ | ❌ | 없음 | **RADAR** 수집·판정, **DA** 해석·질의 |
| 제작 실행 | ❌ | ❌ | ✅ | 없음 | **AutoMaker** |

---

# K. v2 필수 데이터 (Must / Should / Later)

## Must — 없으면 v2 가 v1 과 다르지 않다

| 블록 | 필요 필드 | 현재 존재 | 현재 source | 추가 구축 |
|---|---|---|---|---|
| **Candidate Signal** | `video_id`·`found_at`·`video_score`·`components`·`sub_tier`·`opportunity_grade`·`signal_stage`·`velocity_trend`·`vph`·`patterns[]`·`similar.n`·`evidence.available`·`channel_fit` | ✅ 전부 | RADAR `production_signals.snapshot()` (v2 payload) 또는 `analysis.build()`+`signals.summarize()` | **어댑터만.** DA `RadarSource` 를 실제 경로·스키마로 |
| **Channel Fit** | RADAR `channels.json` 전체(`promise_ko`·`lenses`·`tone_ko`) + AutoMaker `mappings`(radar_ch→am_ch) + `project.genre.persona_status` | ✅ 흩어져 존재 | RADAR JSON + AutoMaker sqlite | **읽기 어댑터 2개.** 새 정의 만들지 않음 |
| **Decision (정본)** | `decision_id`·`decided_at`·`decision`·`note`·동결 `metrics`·`config_digest`·`revision` | ✅ 형식 · ❌ 데이터 | RADAR `decisions.py` | DA 가 이 형식으로 기록하도록 연결 |

## Should — 제작 의사결정이 «지금» 을 반영하려면

| 블록 | 필요 필드 | 현재 존재 | source | 추가 구축 |
|---|---|---|---|---|
| **Production History** | 프로젝트별 `package_id`·`opportunity_id`·`channel_id`·`name`·`created`·`progress.last_step`·`persona_status`·렌더 완료 여부 | 🔶 project.json + sqlite | AutoMaker | AutoMaker 에 «프로젝트 인덱스» 읽기 API (또는 DA 가 output 루트 스캔 — 방식 A 의 위험) |
| **Content Saturation** | 후보 제목 vs 제작·MAKE 이력 제목의 tf-idf 유사도 · 채널별 최근 N편 lens 분포 | ❌ | RADAR `similar.Index`(재사용) + 위 History | DA 안에서 계산 (숫자는 코드) |
| **Production Cost/State** | 채널별 «진행 중 편수»·단계 정체 일수 | 🔶 | project.json `last_accessed`·`progress` | 위 History 에 포함 |

## Later — 성과가 쌓인 뒤

| 블록 | 필요 필드 | 현재 존재 | source | 추가 구축 |
|---|---|---|---|---|
| **Performance Feedback** | `youtube_video_id`·`source_video_id`·bucket별 views/likes/comments·`verdict` | ❌ 코드만 | RADAR publications/own_performance/outcomes | (1) 업로드 시 `publications.jsonl` 한 줄 (2) `run_daily` 에 own_performance 추가 (3) AutoMaker `project.json` 에 `youtube_video_id` 자리 |

---

# L. 현재 답할 수 있는 질문 / 없는 질문

| Q | 판정 | 이유 · 빠진 데이터 |
|---|---|---|
| Q1 오늘 하나만 만든다면 | **부분 가능** | RADAR 데이터로 «시장 신호 1위» 는 답할 수 있다(`video_score`+`signal_stage`+`channel_fit`). «우리 채널 사정» 을 반영한 하나는 불가 — 제작 이력·포화도 0. **DA 현재 상태로는 표본 위 점수 1위일 뿐** |
| Q2 점수는 높지만 만들지 말아야 할 후보 | **부분 가능** | RADAR `low_engagement`(매크)·`ratio_missing_why`·`channel_fit LOW`·`news_risk` 로 일부 답 가능. «이미 만들었다/포화» 이유는 불가 |
| Q3 최근 제작 콘텐츠와 겹치는 후보 | **불가능** | 제작 콘텐츠 0~1건. 비교 대상 없음 |
| Q4 과다 제작 중인 주제 | **불가능** | 동일 |
| Q5 부족하게 다룬 영역 | **부분 가능** | `channels.json.lenses` × 제작이력 lens 태깅으로 설계 가능하나 제작이력 0. RADAR `gaps.py`(시청자 빈칸)는 «시장이 못 채운 것» 이지 «우리가 안 다룬 것» 이 아니다 |
| Q6 두 채널 중 오늘 기회 | **부분 가능** | 채널별 후보 수·평균 점수·`channel_fit` 분포는 계산 가능. 두 채널 모두 `production_enabled=false`·Persona 미승인이라 «기회» 가 «제작 가능» 으로 이어지지 않음 |
| Q7 지난 MAKE 중 성과 나빴던 것 | **불가능** | decisions·publications·own_snapshots 3개 다 없음 |
| Q8 지난 SKIP 중 기회였던 것 | **불가능** | SKIP 기록 없음. 단 RADAR `signal_history` 로 «SKIP 시점 이후 시장 조회수가 계속 올랐나» 는 나중에 답할 수 있는 구조는 있다 |
| Q9 이번 주 5편 포트폴리오 | **불가능** | Q3·Q4·Q6 의 합. 제작 capacity 데이터도 없음 |
| Q10 비용/시간 대비 효율 | **불가능** | 제작 시간·단계별 소요·API 비용이 프로젝트에 기록되지 않음 (`usage_log.csv` 는 전역) |

---

# M. v2 권장 아키텍처 (데이터 흐름)

```text
                 ┌──────────────── 읽기 전용 어댑터 (DA 안) ────────────────┐
                 │                                                          │
RADAR  ──files──▶│ RadarSignalAdapter                                      │
  videos.csv     │   analysis.build() 를 부르지 않는다*                     │
  snapshots      │   ① data/automaker-outbox/outbox.sqlite3 (v2 payload)   │
  signal_history │   ② 없으면 signal_history 최신행 + channels.json         │
  channels.json  │   → CandidateSignal{video_id, score, components, stage, │
  decisions.jsonl│                      trend, patterns, fit, target_ch}    │
                 │                                                          │
AutoMaker ─files▶│ ProductionAdapter                                       │
  intake.sqlite3 │   packages.project + project.json.{radar_intake,        │
  output/*/      │   channel_id, genre.persona_status, progress}            │
   project.json  │   → ProductionRecord{package_id, opportunity_id, ch,    │
                 │                      stage, persona_ok, started}        │
                 └──────────────────────┬───────────────────────────────────┘
                                        ▼
                      DecisionContext (계산, 숫자는 코드)
                        · saturation  = similar(후보, 제작이력∪MAKE이력)
                        · channel_load= 채널별 진행중 편수
                        · lens_cover  = lenses × 제작이력
                        · fit         = channel_fit + mapping 상태
                                        ▼
                      GPT (해석·반대근거·confidence + why_low)  ── 기존 chat.py 골격 유지
                                        ▼
                      사람 MAKE/WATCH/SKIP
                                        ▼
                      decisions.freeze 형식으로 기록  ──▶ RADAR data/decisions.jsonl  (단일 정본)
                                        │
                      MAKE 이면 RADAR automaker_intake.package/send 를 **호출**
                      (DA 자체 handoff/*.json 은 폐기 후보)
```
`*` DA 가 pandas 로 RADAR 점수를 다시 계산하면 두 벌이 된다. RADAR 가 이미 낸 값(payload·signal_history)만 옮긴다 — 현재 `sources.py` 의 원칙과 같다.

---

# N. 구현 우선순위

```text
P0 — 반드시 먼저 (v1 을 «실데이터 위에» 올린다)
  P0-1  DA RadarSource 를 RADAR 실물에 맞춘다: 경로(outbox.sqlite3 / .radar-intake/intake.sqlite3)
        + 스키마(payload.production_signals.demand/discovery). v1 envelope 는 signal_history 로 보강.
  P0-2  결정 정본 단일화: DA 의 MAKE/WATCH/SKIP 을 RADAR decisions.jsonl 형식으로 기록.
        (RADAR 측 P0-1 «decisions.jsonl 이 실제로 생기게» 와 같은 문제)
  P0-3  DA Candidate 에 package_id·channel 프로필 참조를 싣는다 (읽기만).

P1 — v2 핵심 (의사결정 계층 고유 입력)
  P1-1  ChannelAdapter: channels.json + intake mappings + project.genre.persona_status.
  P1-2  ProductionAdapter: AutoMaker 프로젝트 인덱스 (읽기 API 신설 또는 sqlite+project.json 스캔).
  P1-3  Saturation: RADAR similar.Index 재사용해 «후보 vs 제작·MAKE 이력».
  P1-4  DA summary.trend 를 RADAR signal_history 기반으로 교체 (가짜 시계열 제거).
  P1-5  select_candidates 에 fit·saturation·channel_load 를 정렬 키로 추가 (숫자는 코드).

P2 — 성과 피드백
  P2-1  publications.jsonl 기록 경로 확보 (AutoMaker 업로드 완료 시 또는 RADAR 화면).
  P2-2  run_daily 에 own_performance 편입.
  P2-3  outcomes.build 결과를 DA 가 읽어 Q7/Q8 답변.
  P2-4  AutoMaker project.json 에 youtube_video_id 자리.

P3 — Agentic 확장 (§14 참조)
```

---

# O. 수정해야 할 파일 후보 (향후 · 지금 수정하지 않음)

| 경로 | 현재 역할 | 향후 예상 역할 | 수정 필요 이유 |
|---|---|---|---|
| DA `backend/app/adapters/sources.py` | sample/radar 어댑터 | RadarSignalAdapter (sqlite·v2 중첩 스키마·signal_history 보강) | 실물과 경로·필드 불일치 (§G-3) |
| DA `tests/test_units.py:136-160` | v2 픽스처 | RADAR 실제 v2 형태로 교체 | 픽스처가 실물과 다름 |
| DA `backend/app/config.py` | `RADAR_ROOT` | + `AUTOMAKER_INTAKE_STATE`·`AUTOMAKER_OUTPUT_ROOTS` (`.automaker-runtime.json` 과 동일 키) | ProductionAdapter 입력 |
| DA `backend/app/models/schemas.py` | Candidate 12필드 | + `package_id`·`signal{stage,trend,vph}`·`fit`·`saturation`·`channel_profile_ref` | v2 입력 |
| DA `backend/app/services/summary.py` | 횡단 평균 trend | RADAR signal 기반 trend + 채널별 load | 가짜 시계열 제거 |
| DA `backend/app/services/chat.py` | 25건 선별·프롬프트 | 선별 키 확장 · «반대 근거»·`confidence/why_low` 출력 스키마 강제 | `ai-strategist-boundary §3` 원칙 |
| DA `backend/app/services/handoff.py` | 자체 JSON 기록 | RADAR `decisions.freeze` 형식 기록 + `automaker_intake.send` 위임 (또는 폐기) | 이중 기록·읽는 쪽 없음 |
| DA `backend/app/routers/data.py` | import/CRUD | import 소스에 `radar-sqlite`·`automaker` 추가 | 어댑터 노출 |
| RADAR `src/automaker_intake.py` | v2 package | `found_at`·`video_score` 최상위 승격은 이미 `production_signals` 로 해결. `content/brief` 중복 제거(기존 P0-2) | 페이로드 70% 중복 [문서] |
| RADAR `app.py:881-914` | 결정 selectbox | 실제로 `decisions.jsonl` 이 생기는지 확인 | 파일 부재 원인 미확인 (**확인 불가** — 이번 감사에서 UI 를 실행하지 않음) |
| AutoMaker `radar_intake.py:262-269` | project.json 생성 | `radar_intake` 블록에 `opportunity_id`·`target_channel.promise_ko/lenses` 승격 | lineage 최상위 노출 |
| AutoMaker `App.py` (프로젝트 목록 API) | 화면용 | 읽기 전용 «프로젝트 인덱스+상태» 엔드포인트 | ProductionAdapter 가 output 루트를 직접 긁지 않게 |
| AutoMaker `project.json` 스키마 (`docs/automaker-data-model.md`) | progress 10 플래그 | + `uploaded`·`youtube_video_id`·`published_at` | Performance 연결 키 |
| RADAR `run_daily.cmd` | collect·snapshot·signals | + `own_performance` | P2 |

---

# P. 위험 요소

| 위험 | 실측 근거 | 현재 상태 |
|---|---|---|
| **RADAR·DA 이중 scoring** | DA `value`=RADAR `video_score` 복사, 재계산 없음 (`sources.py:184`). 표본은 `betavariate` 로 «지어낸 점수» | 지금은 없음. **P1-5 에서 DA 가 자체 종합점수를 만들면 발생** — 정렬 키를 나란히 두고 합산하지 말 것 (RADAR `patterns.py` 원칙과 동일) |
| **채널 설정 중복** | channels.json(2) ↔ genres.json(1) ↔ project.genre — 서로 다른 실체 | **현존.** 합치지 말고 역할 분리+매핑 (§I) |
| **벤치마크 DNA ↔ 제작 DNA 혼동** | `output/20260903 人生の果実【漫画】` 가 벤치마크 채널명 · `genres.json.benchmarkLinks` 동일 영상 | **현존 (과거 프로젝트).** selective_dna 가 신규는 막음 |
| **표본·실제 혼합** | DA 168 표본 + smoke `manual` 2건이 같은 handoff 폴더 | 표본은 `SAMPLE_` 접두어·`source` 로 구분됨. **실데이터 붙일 때 `replace=true` 로 표본을 지우지 않으면 요약이 섞인다** |
| **최신 값 ↔ historical snapshot 혼동** | RADAR `analysis.build()` 는 항상 «지금» 값. DA 는 import 시점 값을 store 에 굳힌다 | DA store 의 `value` 는 사실상 «import 시점 동결값» 인데 `date` 는 «관측 시점» 이라 **두 시각이 다르다.** Candidate 에 `imported_at`/`score_as_of` 가 없다 |
| **프로젝트 ↔ YouTube 영상 연결 실패** | `youtube_video_id` 필드 부재 (grep 0) | **확정된 공백.** 업로드 전에 자리를 만들지 않으면 첫 영상부터 끊긴다 |
| **동일 주제 중복 제작** | 제작 간 주제 색인 없음 · `similar` 는 시장 전용 | 제작 0건이라 미발생. **첫 3편부터 위험** |
| **AI hallucination** | DA 는 25건+태그로 방어. 그러나 `confidence`·`why_low`·«반대 근거» 없음 (`ai-strategist-boundary §3.2 ③`) | LOW 를 값으로 만드는 스키마 강제 필요 |
| **판단 기록 미보존** | RADAR decisions.jsonl 없음 · DA memory store (재시작 시 소실, `/api/health store_is_persistent: false` [측정]) | **현존.** 오늘 내린 결정이 내일 없다 |
| (추가) **어댑터·문서·테스트 셋이 실물과 다른 채 서로 일치** | §G-3 | 통과하는 테스트가 «연결됨» 을 증명하지 않는다 |

---

# Q. 최종 추천

> 현재 v1 을 유지하면서 무엇만 추가하면, RADAR 의 단순 조회 챗봇이 아니라 실제 AutoMaker 의 제작 의사결정 비서가 되는가?

**세 가지를 «추가» 하고 한 가지를 «빼면» 된다. 새 시스템·새 점수·새 채널 정의는 만들지 않는다.**

1. **읽는 곳을 바꾼다 (P0-1, P1-1, P1-2).** 표본 대신 RADAR 실물(`signal_history`·v2 payload·`channels.json`)과 AutoMaker 실물(`intake.sqlite3`·`project.json`)을 읽는 어댑터 세 개. DA 의 `CandidateSource` 경계는 이미 그 자리를 비워 두고 있다.
2. **결정을 한 곳에 쓴다 (P0-2).** DA 의 MAKE/WATCH/SKIP 을 RADAR `decisions.freeze` 형식(`decision_id`·동결 metrics·`config_digest`)으로 남긴다. 이 한 줄이 RADAR 감사의 P0-1, `outcomes.py` 의 첫 입력, Q7/Q8 의 전제를 동시에 푼다.
3. **DA 고유 계산 두 개만 넣는다 (P1-3, P1-5).** «후보 vs 제작·MAKE 이력 유사도(saturation)» 와 «채널별 진행 중 편수(load)». 둘 다 RADAR `similar.Index` 와 AutoMaker `progress` 를 재사용하는 산수이지 새 엔진이 아니다. 이 두 숫자가 프롬프트에 들어가는 순간 «점수 1위» 와 «지금 우리가 만들 것» 이 갈라진다 — 그것이 v1 과 v2 의 차이다.
4. **뺀다:** DA 자체 `handoff/*.json` 과 `summary._trend_label`. 전자는 읽는 쪽이 없고 RADAR `automaker_intake` 가 더 좋은 계약을 이미 갖고 있으며, 후자는 시계열이 아닌 것에 «최근 상승» 이라는 이름을 붙인다.

성과(Performance) 는 지금 만들지 않는다. 게시 기록 한 줄이 생기면 RADAR 의 `own_performance`·`outcomes` 가 그대로 살아난다 — 그때 DA 는 읽기 어댑터 하나만 더 붙이면 된다.

---

## 부록 1. 세 시스템 비교 (§13 방식 A/B/C)

| | A. DA 가 파일/DB 직접 읽기 | B. 각 시스템이 Adapter/API 제공 | C. 공통 Decision Context 계층 |
|---|---|---|---|
| 장점 | 지금 당장 가능. RADAR·AutoMaker 수정 0 | 스키마 변경이 제공 측 책임. 테스트 가능 | 한 곳에서 lineage 완성. Agent 확장 자연스러움 |
| 단점 | RADAR/AutoMaker 내부 구조 변경에 DA 가 깨진다 (§G-3 가 이미 그 사례) | RADAR 는 파일 계약 문화(`automaker-contract.md`) — HTTP 서버가 없다(Streamlit) | 네 번째 저장소. 정본이 하나 더 생겨 SoT 논쟁 재발 |
| 결합도 | 높음 (경로·스키마) | 중간 | 낮음(런타임) / 높음(스키마 소유) |
| 구현 난이도 | 낮음 | 중간 (AutoMaker 읽기 API 1개 신설) | 높음 |
| 운영 안정성 | 낮음 | 중간~높음 | 높음 (데이터가 쌓인 뒤) |
| Agentic 확장성 | 낮음 | 중간 | 높음 |

**추천: B 를 «파일 계약 버전» 으로.** RADAR 는 이미 `production_signals.snapshot()` + `automaker_intake.package()` 라는 사실상의 어댑터를 갖고 있고 SQLite 로 낸다. AutoMaker 는 `intake.sqlite3` + `project_channel_binding` API 가 있다. DA 가 **그 두 산출물의 스키마를 계약으로 삼아** 읽으면, 새 서버 없이 B 의 이점을 얻는다. C 는 성과 데이터가 생기고 세 시스템의 lineage 가 실제로 조인될 때(P2 이후) 「`decisions.jsonl` + `publications.jsonl` + 프로젝트 인덱스」 세 파일을 한 폴더로 모으는 정도로 시작하면 충분하다.

## 부록 2. Agentic 구조 평가 (§14)

| 역할 | 지금 필요한 형태 | 근거 |
|---|---|---|
| Signal Analyst | **RADAR 코드 그 자체.** Agent 불필요 | 숫자는 코드가 (`ai-strategist-boundary §5`) |
| Channel Editor | DA 내부 **function 1개** (fit + persona 상태 읽기) | 입력이 파일 2개뿐 |
| Portfolio Strategist | DA 내부 **function 1개** (saturation·load·lens_cover) → GPT 해석 | v2 의 핵심이지만 데이터가 작아 tool 로 충분 |
| Production Planner | **보류.** AutoMaker binding 화면이 이미 사람 확정 단계 | 자동 계획은 Persona 승인 채널이 0개인 지금 의미 없음 |
| AutoMaker | 그대로 | — |
| Performance Evaluator | **보류.** RADAR `outcomes.py` 가 규칙 기반으로 먼저 | MIN_SAMPLES 10 전에는 판정 자체를 안 하는 설계 |

**결론: 지금은 하나의 Assistant + tool 3개(signal·channel·portfolio) 로 둔다.** 별도 Agent 로 쪼갤 시점은 (1) Persona 승인 채널이 2개 이상이고 (2) `outcomes` 가 `verdict` 를 내기 시작할 때다. 그 전에 나누면 각 Agent 가 «데이터 없음» 만 주고받는다.

---

## 이 감사가 하지 않은 것

- 코드·설정·데이터를 수정하지 않았다. 테스트를 돌리지 않았다. 외부 API 를 부르지 않았다.
- RADAR Streamlit 화면과 AutoMaker Flask 화면을 실행하지 않았다 — `decisions.jsonl` 이 «왜» 생기지 않는지는 **확인 불가**로 남긴다.
- AutoMaker `App.py` 17,477줄 전수 검토는 하지 않았다. «프로젝트 목록 읽기 API 부재» 는 grep 기반 판단이다.
- `C:\ai-worktrees` 의 다른 워크트리(antigravity·claude·codex)와 `_autotube_backup_*` 는 열지 않았다.
