# 기능 Cross Matrix — KEEP / MOVE / MERGE / REMOVE / NEW

2026-09-03 · 근거는 `integration-audit.md`.

처리 구분:

- **KEEP** — 지금 자리에서 유지
- **MOVE** — 기능은 살리되 다른 시스템으로 옮김
- **MERGE** — 두 곳에 있는 것을 하나로
- **REMOVE** — 없애는 편이 나음
- **NEW** — 지금 없어서 새로 만들어야 함

«최적 위치» 는 R=Radar, S=AI Strategist(신규), M=AutoMaker, H=사람.

---

## 1. 발견 (Discovery)

| 기능 | Radar | AutoMaker | 중복 | 최적 | 처리 | 이유 |
|---|---|---|---|---|---|---|
| 검색어 기반 영상 수집 | ✅ `collector.py` | ✗ | 없음 | R | **KEEP** | AutoMaker 는 시장을 보지 않는다 |
| 검색어 관리·후보 제안 | ✅ `seeds.py` (15개 상한, 사람이 승인) | ✗ | 없음 | R | **KEEP** | 자동 추가 금지 원칙이 이미 옳다 |
| 일본어 판정 | ✅ `language.py` | ✗ | 없음 | R | **KEEP** | |
| 스냅샷 시계열 | ✅ 1,884행 | ✗ | 없음 | R | **KEEP** | 이 시스템의 유일한 축적 자산 |
| Watchlist / 졸업 규칙 | ✅ `snapshot_collector.build_watchlist` | ✗ | 없음 | R | **KEEP** | |
| API quota 계량 | ✅ `youtube.py` + `quota_log.csv` | ✗ (없어서 비용이 안 보인다) | 없음 | R→공용 | **MOVE(개념)** | 같은 개념을 AutoMaker LLM 비용에도 적용해야 한다 |

## 2. 분석 (Analysis)

| 기능 | Radar | AutoMaker | 중복 | 최적 | 처리 | 이유 |
|---|---|---|---|---|---|---|
| ADViews · Age Bucket 보정 | ✅ `analysis.py` | ✗ | 없음 | R | **KEEP** | 임의 변경 금지 |
| Video Score | ✅ | ✗ | 없음 | R | **KEEP** | |
| Channel Score (Baseline/Momentum) | ✅ `channel_analyzer.py` | ✗ | 없음 | R | **KEEP** | 합치지 않는다 |
| Outlier(구독 대비) | ✅ SVR + 분모 하한 1,000 | ✗ | 없음 | R | **KEEP** | |
| 매크 방어(참여율 1.5/1k) | ✅ | ✗ | 없음 | R | **KEEP** | |
| 검색어 성과 분석 | ✅ `seeds.performance` | ✗ | 없음 | R | **KEEP** | |
| `_seed_standing()` 중복 | ✅ ×2 (`export`·`production_brief`) | — | **내부 중복** | R | **MERGE** | 한 함수로. 지금은 결과가 같아 조용히 갈릴 위험만 있다 |
| 점수의 시점 스냅샷 | ✗ 매번 재계산 | ✗ | — | R→S | **NEW** | 결정 시점 점수를 동결해야 예측/실제 비교가 가능 |

## 3. 재료 수집 (Evidence)

| 기능 | Radar | AutoMaker | 중복 | 최적 | 처리 | 이유 |
|---|---|---|---|---|---|---|
| 자막 수집·요약 | ✅ `subtitles.py` yt-dlp, 1,500자 digest | ✗ | 없음 | R | **KEEP** | |
| 댓글 수집 (공식 API) | ✅ `comments.fetch` 50건, 상태 구분 | ✗ (위키만 비공식 스크래핑) | 없음 | R | **KEEP** | «없다»와 «못 받았다»를 가르는 설계가 옳다 |
| 댓글 → 시청자 목소리 분석 | ✅ `comments.analyze` (concerns/questions/fears/objections/phrases/gaps) | ✅ `analyze/source` 의 viewer_voice·viewer_emotions·viewer_phrases | **중복 · 높음** | R | **MERGE** | Radar 쪽이 입력(실제 댓글)과 스키마가 더 낫다. AutoMaker 는 값이 들어오면 **재분석하지 말고 받아쓰기** |
| 참고 이미지 스타일 분석 | ✗ | ✅ `/api/analyze/image` | 없음 | M | **KEEP** | 제작 영역 |
| 위키(패턴 학습) | ✗ | ✅ 코드만 존재, `wiki/` 없음 | 없음 | M | **KEEP(보류)** | 성과 데이터가 생기기 전에는 «어떤 패턴이 좋았나»를 판정할 근거가 없다. 지금 키우지 말 것 |

## 4. 채널 (Channel)

| 기능 | Radar | AutoMaker | 중복 | 최적 | 처리 | 이유 |
|---|---|---|---|---|---|---|
| 채널 정체성 정의 | ✅ `channels.json` (audience·promise·core_question·tone·lenses·profile_version) | ✅ `genres.json` (13개 필수 필드, **현재 0개**) | **중복 · 최고** | **단일 ChannelProfile** | **MERGE** | 둘은 **다른 층**이다 — Radar=판단 렌즈, AutoMaker=집필 규격. 한 파일 안 두 블록(`judgment` / `production`)으로 합치고 **소유자는 Radar**, AutoMaker 는 읽기만 |
| Channel Fit 판정 | ✅ `channel_fit.py` HIGH/MED/LOW 7항목 + 근거 + angle | ✗ | 없음 | R→S | **MOVE** | 판단 계층으로 옮긴다. 계산이 아니라 판단이다 |
| Crossover 후보(두 채널 모두 HIGH) | ✅ `is_crossover` | ✗ | 없음 | S | **MOVE** | 같은 이유 |
| 채널 페르소나 LLM 생성 | ✗ | ✅ `/api/persona/generate` | 없음 | M | **KEEP** | 집필 규격을 만드는 도구. 유지 |

## 5. 판단 (Decision) — **거의 전부 NEW**

| 기능 | Radar | AutoMaker | 중복 | 최적 | 처리 | 이유 |
|---|---|---|---|---|---|---|
| MAKE / WATCH / SKIP | ✗ | ✗ | — | S | **NEW** | 지금은 사람 머릿속에만 있다. 이것이 가장 큰 공백 |
| Confidence + 반대 근거 | ✗ | ✗ | — | S | **NEW** | LOW 를 허용해야 신뢰가 생긴다 |
| 결정 근거 저장 (Evidence 링크) | ✗ | ✗ | — | S | **NEW** | 근거 없는 판단은 나중에 검증 불가 |
| 중복 소재 방지 (과거에 만들었나) | ✗ | ✗ | — | S | **NEW** | 제작 이력이 아직 0건이라 지금은 빈 기능이지만 **구조는 먼저 있어야** 한다 |
| 오늘의 추천 3~5건 | 부분 (표만 있고 결론 없음) | ✗ | — | S | **NEW** | |
| 사람 최종 승인 | ✅ 화면 조작으로 암묵적 | ✅ 단계마다 버튼 | — | H | **KEEP** | 명시적 «승인» 기록만 추가 |

## 6. 제작 기획 (Production Planning)

| 기능 | Radar | AutoMaker | 중복 | 최적 | 처리 | 이유 |
|---|---|---|---|---|---|---|
| Opportunity Card (고를지 판단) | ✅ `export.one_pager` | ✗ | 없음 | R | **KEEP** | |
| Production Brief (어떻게 만들지) | ✅ `production_brief.build` → md 파일 | 부분: `source_analysis`(summary·emotion_map·script_map) | **개념 중복 · 중간** | R 생성 → M 소비 | **MERGE** | 브리프를 **JSON + md 두 형태**로 내고, AutoMaker 3단계는 그 JSON 을 받으면 `analyze/source` 를 **건너뛴다** |
| Angle 설계 | ✅ `channel_fit.angle_ko` + 댓글 채널별 각도 | ✗ | 없음 | S | **MOVE** | 판단 계층 |
| 제목 후보 | ✗ (Claude 웹) | ✅ 4단계 + 12단계 **두 번** | **내부 중복** | M | **MERGE** | 4단계 하나로. 12단계는 최종 확정만 |
| 썸네일 문구 | ✗ | ✅ 12단계 | 없음 | M | **KEEP** | |
| 화자·설계도 | ✗ | ✅ 5단계 | 없음 | M | **KEEP** | |

## 7. 집필 (Script)

| 기능 | Radar | AutoMaker | 중복 | 최적 | 처리 | 이유 |
|---|---|---|---|---|---|---|
| 대본 생성 | 간접 (`script_package` → Claude 웹, 수동) | ✅ `/api/generate/script` (출력 64,000) | **경로 3개** | M | **MERGE** | **AutoMaker 를 정본으로.** Radar 는 «재료»만 넘기고 집필하지 않는다 |
| 외부 대본 수용 | ✗ | ✅ `/api/generate/split_script` | 없음 | M | **KEEP** | Claude 웹 대본을 계속 쓰고 싶을 때의 유일한 정식 입구. 이미 있다 |
| FACT CHECK 표시 | ✅ 프롬프트 규약 + 사람 확인 | ✅ Perplexity + 프롬프트 주입 | **정책 충돌** | R+M | **MERGE** | 한 정책으로: 자동 검색은 **보조 자료**, 게시 차단 권한은 **사람**에게만 |
| 대본 업그레이드/점수/재작성 | ✗ | ✅ 3개 라우트, 기본 꺼짐 | 없음 | M | **KEEP** | 다만 토큰이 크므로 기본 꺼짐 유지 |

## 8. 제작 실행 (Production)

| 기능 | Radar | AutoMaker | 중복 | 최적 | 처리 |
|---|---|---|---|---|---|
| TTS (VOICEVOX 로컬) | ✗ | ✅ | 없음 | M | **KEEP** |
| 이미지·영상 프롬프트 | ✗ | ✅ | 없음 | M | **KEEP** |
| Flow / Grok 브라우저 자동화 | ✗ | ✅ | 없음 | M | **KEEP** |
| ffmpeg 렌더·PIP·숏폼 | ✗ | ✅ | 없음 | M | **KEEP** |
| 배경음악(Suno 페이지 열기) | ✗ | ✅ | 없음 | M | **KEEP** |
| 호출부 없는 라우트 4개 | — | ✅ 죽은 코드 | — | M | **REMOVE** | |
| OpenAI 키 슬롯 | — | ✅ 3순위 폴백만 | — | M | **REMOVE(후보)** | 자체 문서도 «사실상 불필요» 로 결론 |
| Supertone·Typecast 구현부 | — | ✅ 잔존 | — | M | **REMOVE(후보)** | 화면에서 이미 뺐다 |
| `AutoTube_Student.zip` 2.08GB | — | ✅ 소스 폴더 안 | — | M | **REMOVE** | 폴더 복사 백업을 무겁게 만든다. 다른 디스크로 옮길 것 |

## 9. 게시·성과 (Publish / Measure) — **전부 NEW**

| 기능 | Radar | AutoMaker | 최적 | 처리 | 이유 |
|---|---|---|---|---|---|
| 업로드 | ✗ | 가이드만 | H | **KEEP(수동)** | 자동 업로드는 만들지 않는다. 되돌릴 수 없다 |
| 게시 기록(Publication) | ✗ | ✗ | S | **NEW** | video_id·게시시각·제목·썸네일·angle 을 남겨야 성과와 이어진다 |
| 자기 채널 성과 수집 (24h/72h/7d) | ✗ | ✗ | R | **NEW** | **이미 있는 `snapshot_collector` 를 우리 영상에도 돌리면 된다** — videos.list 는 50개 1unit |
| CTR·시청유지·구독전환 | ✗ | ✗ | H→S | **NEW(2차)** | YouTube Analytics API 는 OAuth 필요. 초기에는 **사람이 수기 입력** |
| 예측 vs 실제 | ✗ | ✗ | S | **NEW** | Data Contract 가 먼저 |
| 학습(패턴 축적) | ✗ | 위키(빈 상태) | S | **NEW(4차)** | 사례 30건 전에는 통계로 만들지 말 것 |

## 10. 운영·인프라

| 기능 | Radar | AutoMaker | 최적 | 처리 | 이유 |
|---|---|---|---|---|---|
| 스케줄 실행 | ✅ Windows 작업 스케줄러 07:00 | ✗ | R | **KEEP** | |
| LLM 호출 단일 창구 | ✅ `translate.py` | ✗ 95곳 산개 | — | **KEEP(R) / 개선 보류(M)** | AutoMaker 95곳 리팩터링은 **지금 하지 말 것** — 이익보다 위험이 크다 |
| 버전 관리 | ✅ git | ✗ 폴더 복사 | M | **NEW** | 통합 작업 전 **AutoMaker 를 git 에 넣는 것이 선행 조건** |
| 테스트 실행 설정 | ✅ `conftest.py` | ✗ 기본 모드로 수집 실패 | M | **NEW** | `pytest.ini` 한 줄 |
| 키 저장 | `.env` | `.api_keys.json` 평문 | — | **KEEP** | 개인 PC 전제. 다만 제품화 시 재검토 |

---

## 11. 요약 — 개수

| 처리 | 건수 | 대표 |
|---|---:|---|
| KEEP | 30 | Radar 분석·AutoMaker 제작 실행 전부 |
| MERGE | 7 | **ChannelProfile**, **시청자 목소리**, Production Brief, 제목 후보, FACT CHECK 정책, `_seed_standing`, 대본 생성 경로 |
| MOVE | 4 | Channel Fit · Crossover · Angle → AI Strategist / quota 개념 → 공용 |
| REMOVE | 5 | 죽은 라우트 4개, OpenAI 슬롯, 제거된 TTS 구현부, 2GB zip |
| NEW | 12 | **Decision 계층 전부**, 점수 동결, Publication, 성과 수집, 예측/실제, AutoMaker git·pytest 설정 |

**NEW 12개 중 8개가 «판단»과 «성과»에 몰려 있다.** 기능을 더 만드는 문제가 아니라
**빠진 두 층을 만드는 문제다.**
