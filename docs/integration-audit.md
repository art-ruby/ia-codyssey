# 통합 감사 — Radar / AutoMaker 현황

2026-09-03 · 실제 소스코드와 실제 데이터 기준. 코드는 한 줄도 고치지 않았다.

이 문서는 «무엇을 만들면 좋겠다» 가 아니라 **지금 무엇이 있는가** 만 적는다.
설계와 제안은 `target-architecture.md` · `integration-roadmap.md` 에 있다.

---

## 0. 한 줄 요약

두 프로그램은 **겹치지 않는다.** Radar 는 «무엇을 만들지» 를 찾고 AutoMaker 는
«그것을 어떻게 만들지» 를 실행한다. 문제는 중복이 아니라 **두 시스템 사이가
사람의 복사·붙여넣기로만 이어져 있고, 게시 이후가 통째로 비어 있다** 는 것이다.

---

## 1. 위치와 정체

| | Program A — Radar | Program B — AutoMaker |
|---|---|---|
| 경로 | `C:\ia-codyssey\assignments\M1-1\Japanese-Longform-Opportunity-Radar` | `C:\automaker` |
| git | ia-codyssey 저장소 안 (branch `m1-1-channel-profile-seeds`) | **git 미사용** — 폴더 복사본으로 백업 (`_원본백업_20260901_2126`) |
| 언어·프레임워크 | Python · Streamlit · pandas | Python · Flask · 정적 HTML/JS |
| entry point | `streamlit run app.py`, `python -m src.collector`, `python -m src.snapshot_collector` | `python App.py` → `http://localhost:5300` |
| 규모 | `app.py` 992줄 + `src/` 16모듈 (전체 5,553줄, 테스트 포함) | `App.py` **16,883줄** 단일 파일 + `pages/*.html` 17개(최대 304KB) |
| 저장 | CSV · JSON 파일 | 프로젝트 폴더 + `project.json` / `script.json` / `titles.json` / `description.json`, 전역 `genres.json` |
| 테스트 | `python -m pytest -q` → **61 passed** (1.59s) | `python -m pytest -q --import-mode=importlib` → **64 passed** (31s) |
| 문서 | README · REPORT · prd · tech · task · docs/specs | docs/ 5건 (API 연결지도, 일본배포전환 등) |

`C:\autotube` 는 2026-08-14 경 갈라져 나온 **옛 갈래**다. AutoMaker 의 자체 문서가
그렇게 기록하고 있고 (`docs/2026-09-01-일본배포전환.md` §0), 이후 수정이 없다.
**통합 대상에서 제외한다.** 그러나 `C:\automaker\AutoTube_Student.zip` 이
**2.08GB** 로 소스 폴더 안에 그대로 있어, 폴더 복사 백업 방식과 겹쳐 디스크와 백업
시간을 잡아먹고 있다.

---

## 2. Program A — Radar 가 실제로 하는 일

### 2.1 데이터 흐름 (검증됨)

```
seeds.json (검색어 15개 상한)
   ↓  src/collector.py            search.list → videos.list
videos.csv                        777행 · 변하지 않는 정보만
   ↓  src/snapshot_collector.py   매일 1회 videos.list (50개=1unit)
video_snapshots.csv               1,884행 · 시간에 따라 변하는 정보
   ↓  src/analysis.py             load → add_metrics → add_age_adjusted → add_scores
(메모리 DataFrame)                ADViews · SVR · Age Bucket · Video Score
   ↓  src/channel_analyzer.py     TOP30 채널만
data/processed/channels.csv       30행 · Channel Baseline / Momentum / Channel Score
```

`python -c "from src import analysis; analysis.build()"` 를 직접 돌려 확인했다 —
777행이 나오고 `gains()` 는 202행을 낸다.

### 2.2 Source of Truth

| 파일 | 성격 | 누가 쓰나 |
|---|---|---|
| `data/raw/videos.csv` | **원본.** 고정 정보. 같은 video_id 는 다시 쓰지 않는다 | collector |
| `data/raw/video_snapshots.csv` | **원본.** 시계열. 하루 한 줄씩 append | snapshot_collector |
| `data/raw/seeds.json` | **원본.** 검색 전략. git 대상 아님(로컬) | 사람(화면) |
| `data/config/channels.json` | **원본.** 채널 정체성 2개 | 사람(손) |
| `data/raw/subs/*.json3` · `data/raw/comments/*.json` | **원본 캐시.** 변하지 않으므로 재수집 안 함 | subtitles · comments |
| `data/processed/channels.csv` | 파생 | channel_analyzer |
| `data/processed/channel_fit.csv` | 파생(LLM 판정 캐시, append-only) | channel_fit |
| `data/processed/comments/*.json` | 파생(LLM 요약 캐시) | comments.analyze |
| `data/briefs/{channel}/{vid}.md` | 파생(조립) | production_brief |
| DataFrame 전체 | **매번 다시 계산. 디스크에 없다** | analysis.build() |

**계산 값이 파일로 남지 않는다는 점이 중요하다.** Video Score·ADViews·Age Bucket
백분위는 `analysis.build()` 가 호출될 때마다 그 시점의 모집단으로 다시 계산된다.
이것은 의도된 설계다(나이는 매일 바뀌므로). 대신 **«그때 그 점수가 몇이었나» 를
되짚을 방법이 없다.** 예측 대비 실제를 나중에 비교하려면 이 값을 **결정 시점에
동결(freeze)해서 남겨야 한다.** 현재 유일하게 시점이 동결되는 것은
`channel_fit.csv` 뿐이다 (append-only + `analyzed_at` + `profile_version`).

### 2.3 계산이 한 곳에 모여 있는가 — 그렇다

- `src/analysis.py` 만 점수를 계산한다. `app.py` · `export.py` · `production_brief.py`
  는 전부 `analysis.build()` 결과를 **읽기만** 한다. UI 재계산 없음.
- 루트 `analysis.py`(280줄)는 이름이 겹치지만 **과제 리포트용 그래프 생성기**다.
  `from src import analysis as A` 로 같은 모듈을 쓴다. 중복 계산 아님.
- 예외: `_seed_standing()` 이 `export.py` 와 `production_brief.py` 에 **거의 같은
  코드로 두 벌** 있다. 한쪽은 `RECENT_DAYS` 상수를, 다른 쪽은 하드코딩 30 을 쓴다.
  지금은 결과가 같지만 한쪽만 고치면 조용히 갈린다. — **작은 중복 1건.**

### 2.4 사람이 판단하는 마지막 지점

`app.py` 의 「☀️ 오늘의 발견」 탭에서 사람이 하는 일:

1. 채널을 고른다 (`channel_picker`)
2. 목록에서 영상 하나를 고른다 (Video Score 상위 40 + 급상승 10)
3. 「한 장 만들기」 → `export.one_pager()` 를 읽고 **만들지 말지 판단**
4. 「댓글 받고 브리프 만들기」 → `comments.fetch/analyze` + `channel_fit.judge` + `production_brief.build`
5. 「Claude 대본용 자료 만들기」 → `script_package()` 출력을 **손으로 복사**
6. Claude 웹에 붙여넣어 대본을 받고 → **손으로** `data/scripts/{channel}/{vid}_script.md` 에 저장

**3번과 6번이 완전한 수작업이다.** 특히 3번에는 판단 근거가 화면에 나열될 뿐
«MAKE / WATCH / SKIP» 이라는 결론도, 그 결론을 남긴 기록도 없다.

### 2.5 Claude 에게 실제로 넘어가는 것

`production_brief.script_package()` = `prompts/script_writer.md` 템플릿에
아래를 채워 만든 **한 덩어리 텍스트**(브리프 상한 8,000자):

```
CHANNEL_ID / CHANNEL_NAME / CHANNEL_AUDIENCE / CHANNEL_PROMISE /
CHANNEL_CORE_QUESTION / CHANNEL_LENSES        ← channels.json
PRODUCTION_BRIEF                               ← 조립된 브리프 전문
TRANSCRIPT_DIGEST                              ← 앞 3분 + 반복 낱말 + 마지막 1분 (1,500자)
COMMENT_ANALYSIS                               ← 댓글 LLM 요약 (2,500자)
```

raw 자막·raw 댓글 전문은 **넣지 않는다.** 이 설계는 옳다. 그대로 유지한다.

### 2.6 외부 의존

| 대상 | 용도 | 비용 |
|---|---|---|
| YouTube Data API v3 (urllib 직접) | search.list · videos.list · channels.list · playlistItems.list · commentThreads.list | quota. search=100units, 실질 하루 100회 |
| `copa.codyssey.kr/v1` (OpenAI 규격 프록시, `gemini-3-flash`) | 제목 번역 · Channel Fit · 댓글 분석 · 검색어 제안 | 과금 |
| `yt-dlp` (subprocess) | 자동생성 일본어 자막 json3 | 무료·비공식 |
| Windows 작업 스케줄러 | `run_daily.cmd` 매일 07:00 | — |

**quota 를 코드가 직접 센다** (`src/youtube.py`, `data/raw/quota_log.csv`).
이 설계는 AutoMaker 에 없는 미덕이다.

---

## 3. Program B — AutoMaker 가 실제로 하는 일

### 3.1 단계 (pages/ 파일명 = 실제 화면 순서)

```
0.메인 → 1.프로젝트관리 → 2.채널설정 → 3.콘텐츠소스 → 4.제목선택 → 5.화자설정
      → 6.대본생성 → 7.TTS설정 → 8.이미지생성 → 9.영상생성 → 10.배경음악생성
      → 11.영상조합 / 11.PIP영상조합 → 12.제목썸네일 → 13.영상설명태그
      → 14.숏폼생성 → 15.롱폼등록가이드 → 16.숏폼등록가이드
                                            (+ wiki.html)
```

### 3.2 단계별 입·출력 (확인된 것)

| 단계 | 입력 | 처리 | 출력·저장 | 외부 |
|---|---|---|---|---|
| 1 프로젝트 | 이름·저장위치·언어(기본 `ja`) | 폴더 생성 | `project.json`(version/name/created/path/lang/genre/channel/source/progress) + `script.json` + `titles.json` + `description.json` + `audio,images,videos,clips,reference` | — |
| 2 채널설정 | Q1~Q7 문답 | 페르소나 6항목 + chips 생성 | **`genres.json`** (전역, 프로젝트 밖) | Anthropic→Gemini |
| 3 콘텐츠소스 | **자유 텍스트 `contentText`** + 참고 이미지 | 팩트체크→소재분석→이미지분석→현지화, 4연속 | `project.source` / `source_analysis` | Perplexity, Gemini→Anthropic ×3 |
| 4 제목선택 | 소재분석 | 제목 후보 생성·번역 | `titles.json` | Anthropic→OpenAI→Gemini |
| 5 화자설정 | 장르·소재 | 등장인물 제안 · 설계도 · 보이스 추천 | `project.blueprint` | Anthropic→Gemini, VOICEVOX 목록 |
| 6 대본생성 | 장르+소재분석+설계도 | 대본 생성(**출력 상한 64,000** — 전 라우트 최대) | `script.json`, `script_jp.txt` | Anthropic→Gemini→OpenAI |
| 7 TTS | 씬별 대사 | 음성 합성 | `audio/` | **VOICEVOX(로컬, 일본어 기본)**, Gemini, ElevenLabs |
| 8·9 이미지·영상 | 씬 | 프롬프트 배치 생성 → 브라우저 자동화로 생성 | `images/`, `videos/` | Gemini→Anthropic + **Google Flow / Grok(브라우저 조작)** |
| 10 BGM | — | 페이지를 열어 주는 것까지 | — | Suno(수동) |
| 11 조합 | 클립·오디오 | ffmpeg 렌더 | `clips/`, 최종 mp4 | 로컬 ffmpeg |
| 12·13 | 대본 | 제목 9종 + 썸네일 문구, 설명·태그 | `titles.json`, `description.json` | Gemini→Anthropic |
| 14 숏폼 | 롱폼 | 숏폼 5종 대본·렌더 | `videos/` | Anthropic→Gemini→OpenAI |
| **15·16 등록** | 최종물 | **복사 버튼이 달린 «가이드»** | — | **없음 — 업로드는 사람이 손으로 한다** |
| wiki | 외부 자료·YouTube 댓글 스크래핑 | 패턴 학습·원칙 축적 | `wiki/` (**아직 존재하지 않음**) | Anthropic→Gemini |

### 3.3 확인된 사실 몇 가지

- **업로드 자동화는 없다.** `App.py` 안에 `youtube.com/upload`·`youtube_upload`·
  `analytics` 문자열이 **0건**이다. 15·16단계는 «복사해서 유튜브에 올리세요» 안내다.
- **성과 수집이 없다.** YouTube Data API 를 아예 쓰지 않는다. 조회수·CTR·시청유지
  어느 것도 프로그램에 들어오지 않는다.
- **`genres.json` 이 지금 디스크에 없다.** 즉 이 작업본에는 **설정된 채널이 하나도
  없다.** 대본 생성은 `_channel_required_missing()` 이 11~13개 필수항목을 요구하며
  막는다: `structureType, titlePatterns, scriptStructure, speakingStyle,
  forbiddenPatterns, thumbnailPatterns, viewerPersona, commentEmotion, ctrHooking,
  retentionBridge, emotionTemperature` (+HYBRID/INFO 면 `channelPersona`,
  +일본어면 `localization`).
- **`wiki/` 디렉터리도 없다.** 위키 기능은 코드로만 존재하고 축적된 것이 없다.
- 2026-09-01 에 **일본어 직접 생성으로 전환**했다(프롬프트 9개·36곳). 한국어로 쓰고
  번역하던 왕복을 없앴다. → Radar 의 대상 시장과 이제 완전히 같다.
- 2026-09-02 에 Supertone·Typecast TTS 를 제거하고 일본어는 VOICEVOX(로컬·무료)로
  고정했다.
- **테스트가 기본 설정으로는 수집조차 안 된다.** `python -m pytest` 는 5개 모듈 전부
  `ModuleNotFoundError` 로 실패하고 `--import-mode=importlib` 를 줘야 64개가 통과한다.
  `pytest.ini`/`pyproject.toml` 이 없어서다. — 사소하지만 «테스트가 있다» 를
  «테스트가 돈다» 로 착각하기 쉬운 자리다.

### 3.4 외부 의존과 비용

`docs/2026-09-02-API연결지도.md` 기준(자체 문서, 라우트 목록으로 교차 확인):
외부 API 8종 · 서버 호출부 95개 · 키 슬롯 5개 · API 사용 라우트 54개 ·
**부르는 곳이 없는 라우트 4개**.

- 모든 외부 호출은 `App.py` 에서만 나간다 (키가 브라우저로 새지 않는 구조). **좋다.**
- 그러나 호출부가 **95곳에 흩어져 있다.** Radar 의 `src/translate.py` 는 이 점을
  명시적으로 반면교사로 삼아 «함수 1개 + PROVIDERS 한 줄» 로 제공자를 교체하도록
  만들어졌다(모듈 docstring에 그렇게 적혀 있다).
- 키는 `.api_keys.json` 에 **평문** 저장. 개인 PC 전용이라는 전제.
- 토큰이 몰리는 곳: 6단계 대본생성(출력 64,000) · 대본 업그레이드(32,000, 누를
  때마다 반복) · 3단계 소재현지화(16,000, 잘리면 24,000 재시도).

---

## 4. 두 시스템이 지금 어떻게 이어져 있는가

Radar 자체 문서 `docs/automaker-contract.md` 가 이미 계약을 적어 두었다.
**파일로만 주고받는다** 는 원칙은 옳다. 문제는 그 파일이 **사람 손을 세 번 거친다**는 것이다.

```
Radar  script_package() 출력          ← 프로그램
   ✋  화면에서 복사
   ✋  Claude 웹에 붙여넣기 · 대화
   ✋  결과를 data/scripts/…_script.md 로 저장
AutoMaker 3단계 contentText 입력칸     ← 또 손으로 옮긴다
```

**실측:** `data/briefs/loss_defense/` 에 브리프 2건이 있고
`data/scripts/loss_defense/` · `solo_pride/` 는 **둘 다 비어 있다.**
즉 **이 경로로 실제 대본이 한 번도 만들어진 적이 없다.**
계약은 문서로 존재하고 코드로는 절반만 존재하며 운영 실적은 0이다.

---

## 5. 중복 — 실제로 겹치는 것

겹치는 것은 «기능 이름» 이 아니라 **«같은 질문에 두 시스템이 각자 답하고 있는» 자리**다.

| # | 중복 | Radar | AutoMaker | 심각도 |
|---|---|---|---|---|
| 1 | **채널 정체성** | `channels.json` — audience·promise·core_question·tone·lenses·profile_version | `genres.json` — channelPersona·viewerPersona·speakingStyle·titlePatterns·thumbnailPatterns·forbiddenPatterns·ctrHooking·retentionBridge·emotionTemperature·localization | **높음.** 같은 채널을 두 곳에 따로 정의하고 서로 모른다 |
| 2 | **시청자 목소리 분석** | `comments.analyze()` — 실제 YouTube 댓글 50건 → top_concerns·questions·fears·objections·viewer_phrases·unresolved_gaps | `03_콘텐츠소스_분석.txt` — 입력 텍스트에 섞인 댓글에서 viewer_voice·viewer_emotions·viewer_phrases | **높음.** 같은 개념을 두 번, 다른 스키마로, 각각 LLM 비용을 내며 만든다 |
| 3 | **사실 확인** | 사람이 한다. 대본의 `[FACT CHECK]` 표시를 사람이 확인 (계약서에 명시) | Perplexity 웹검색 → `fact_check_result` → 틀린 수치를 대본에서 배제하도록 프롬프트 주입 | **중간.** 정책이 서로 다르다. 연금·세금·상속을 다루는 채널에서는 이 차이가 위험 |
| 4 | **소재 요약** | `subtitles.digest()`(1,500자) + 브리프의 「원 영상은 어떻게 풀었나」 | `/api/analyze/source` 의 summary·key_points·script_map | **중간.** 입력이 다르므로(원 영상 vs 우리 소재) 완전 중복은 아니나, Radar 브리프를 그대로 넣으면 AutoMaker 가 **이미 분석된 것을 다시 분석한다** |
| 5 | **제목 후보** | 없음 (script_writer.md 가 Claude 웹에서 만들게 함) | 4단계 + 12단계, 두 번 만든다 | **중간.** AutoMaker 내부 중복 |
| 6 | `_seed_standing()` | `export.py` · `production_brief.py` 에 두 벌 | — | 낮음 |
| 7 | LLM 호출부 | `translate.py` 한 곳 | **95곳** | 낮음(중복이 아니라 산개) |

**진짜 중복은 1번과 2번뿐이다.** 나머지는 «같은 이름, 다른 질문» 이다.

---

## 6. 단절 — 이어져 있지 않은 것

```
Market → Discovery → Opportunity → Validation → Decision → Channel → Angle
   ✅        ✅           ✅          부분         ❌        부분      부분
→ Production Planning → Script → Video → Thumbnail → Shorts → Publish
        부분(2계통)      ❌(수동)   ✅       ✅         ✅       ❌(수동)
→ Performance → Post-analysis → Learning
      ❌             ❌             ❌
```

- **Decision(❌)** — MAKE/WATCH/SKIP 이라는 결론을 남기는 곳이 없다. 사람 머릿속에만 있다.
- **Script(❌)** — Radar 도 AutoMaker 도 대본을 «자기 안에서» 만들 수 있는데,
  실제 운영은 Claude 웹을 거친다. **경로가 세 개인데 실제로 쓰이는 것은 수동 경로다.**
- **Publish(❌)** — 가이드만 있다.
- **Performance / Post-analysis / Learning(❌❌❌)** — 아예 없다.
  게시한 영상의 조회수·CTR·유지율이 어느 프로그램에도 들어오지 않는다.
  **Radar 는 남의 채널만 보고 있고, 우리 채널은 아무도 보고 있지 않다.**

---

## 7. 문제점 정리

1. **판단이 기록되지 않는다.** Radar 는 근거를 훌륭하게 모아 주지만 «그래서 만들기로
   했는가» 를 저장하지 않는다. 기록이 없으면 나중에 검증도 학습도 불가능하다.
2. **점수가 시점 고정되지 않는다.** `analysis.build()` 는 매번 다시 계산한다.
   결정 순간의 Video Score 를 남기지 않으면 «예측 대비 실제» 를 만들 수 없다.
3. **채널 정체성이 두 곳에 있다.** `channels.json`(2개, 둘 다 `production_enabled:false`)
   과 `genres.json`(**현재 0개**). 두 채널은 아직 실제로 운영되지 않는다.
4. **성과 데이터가 0이다.** Flywheel 의 반환 경로가 존재하지 않는다.
5. **AutoMaker 는 16,883줄 단일 파일이고 git 이 없다.** 여기에 통합 코드를 더 넣는
   것은 위험을 사는 일이다.
6. **Radar 브리프 → AutoMaker 소재입력 사이에 형식 계약이 없다.** 지금은 자유 텍스트
   `contentText` 한 칸이다. 그대로 넣으면 AutoMaker 가 이미 분석된 것을 다시 분석한다.
7. **팩트체크 정책이 두 시스템에서 다르다.** 50~69세 시청자에게 연금·세금·상속을
   말하는 채널에서 이것은 편의 문제가 아니다.
8. **AutoMaker 테스트가 기본 설정으로 안 돈다** (`--import-mode=importlib` 필요).
9. **2.08GB 짜리 zip 이 소스 폴더 안에 있다** (`AutoTube_Student.zip`).
   git 없이 폴더 복사로 백업하는 방식과 정면으로 충돌한다.

---

## 8. 잘 되어 있는 것 — 건드리지 말 것

- Radar 의 **계산 단일화**(`src/analysis.py` 한 곳)와 **«결측»과 «0» 의 구분.**
  `subscriber_view_ratio` 는 분모가 1,000 미만이면 계산하지 않고 비운다.
  참여율 1.5/1k 미만은 «매크 의심» 으로 비율만 무효화하되 **행은 지우지 않는다.**
- **Video Score 와 Channel Score 를 합치지 않는 원칙.** 이것이 이 시스템의 핵심 정보다.
- Radar 의 **quota 자체 계량**.
- AutoMaker 의 **키를 서버에서만 쓰는 구조**, **VOICEVOX 로컬 TTS**(무료·무제한),
  `project.json` **병합 저장**(화면이 모르는 키를 지우지 않음), `genres.json`
  **축소 저장 거부**(2026-08-19 사고 방지).
- AutoMaker 의 **`/api/generate/split_script`** — 외부 대본을 씬 형식으로 변환하는
  라우트가 이미 있다. **Radar 대본을 받아들이는 문이 이미 뚫려 있다.**
