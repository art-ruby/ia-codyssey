# Data Contract — 세 시스템이 주고받는 것

2026-09-03 · Radar 의 실제 CSV/JSON 열과 AutoMaker 의 실제 `project.json`·
`genres.json` 필드를 보고 설계했다. 예시 schema 를 그대로 쓰지 않았다.

---

## 0. 설계 원칙

1. **Radar 와 AutoMaker 를 코드로 붙이지 않는다.** 이미 `docs/automaker-contract.md`
   가 정한 «파일로만 주고받는다» 를 유지한다. 붙일 것은 코드가 아니라 **형식**이다.
2. **파생 값은 계약에 넣지 않는다.** 단 하나 예외가 **DecisionSnapshot** 이다 —
   판단한 시점의 숫자는 그때 얼려야 나중에 검증할 수 있다.
3. **결측은 `null`. `0` 으로 채우지 않는다.** Radar 가 CSV 단에서 지키는 원칙을
   계약 단에서도 지킨다.
4. **한 entity 는 소유자가 하나다.** 두 시스템이 같은 필드를 각자 쓰면 반드시 갈린다.
5. **모든 판단 기록은 append-only.** `channel_fit.csv` 가 이미 그렇게 하고 있다 —
   옛 판정을 지우면 «왜 그때는 그렇게 봤나» 를 잃는다.

---

## 1. Entity 목록과 소유권

| Entity | 목적 | 생성 | 수정 | 소비 | 수명 |
|---|---|---|---|---|---|
| **ChannelProfile** | 채널의 정체성과 집필 규격 | 사람 | 사람 | R·S·M | 영구 (version 증가) |
| **SourceVideo** | 남의 영상 관측 원본 | Radar collector | 없음(불변) | R·S | 영구 |
| **VideoSnapshot** | 시계열 관측 | Radar snapshot_collector | 없음(append) | R·S | 영구 |
| **Evidence** | 판단 근거 한 조각 | Radar (분석·자막·댓글) | 없음 | S | 영구 |
| **Opportunity** | «이 소재를 볼 만하다» | Radar | 상태만 | S·사람 | 열림→닫힘 |
| **DecisionSnapshot** | 판단 시점의 숫자 동결 | S | 없음(불변) | S | 영구 |
| **StrategyDecision** | MAKE/WATCH/SKIP + 근거 | S(제안) → 사람(확정) | append-only | M·S | 영구 |
| **ProductionBrief** | 무엇을 어떤 각도로 만들지 | Radar 조립 | 사람 | M | 영구 |
| **ProductionProject** | AutoMaker 작업 실체 | AutoMaker | AutoMaker | S | 프로젝트 수명 |
| **Publication** | 실제 게시 기록 | 사람 입력 | 사람 | R·S | 영구 |
| **PerformanceSnapshot** | 우리 영상의 성과 관측 | Radar(공개지표) + 사람(Analytics) | append | S | 영구 |
| **Outcome** | 예측 vs 실제 | S | S | S | 영구 |
| **AIRecommendation** | AI 가 한 말과 근거 | S | 없음 | 사람 | 영구 |
| **Conversation** | 질의 이력 | S | append | S | 영구 |

**Radar 가 소유:** SourceVideo · VideoSnapshot · Evidence · Opportunity · ProductionBrief · PerformanceSnapshot(공개지표)
**Strategist 가 소유:** DecisionSnapshot · StrategyDecision · Outcome · AIRecommendation · Conversation
**AutoMaker 가 소유:** ProductionProject
**사람이 소유:** ChannelProfile · Publication

---

## 2. ChannelProfile — 가장 중요한 MERGE

지금 두 곳에 있다. 그러나 **두 파일은 서로 다른 질문에 답한다.**

| Radar `channels.json` | AutoMaker `genres.json` |
|---|---|
| «이 소재가 우리 채널 것인가» 를 **판단**하는 렌즈 | «이 채널은 어떻게 쓰는가» 라는 **집필 규격** |
| audience, promise_ko, core_question_ko, lenses[], tone_ko | structureType, channelPersona, viewerPersona, speakingStyle, titlePatterns, thumbnailPatterns, forbiddenPatterns, ctrHooking, retentionBridge, emotionTemperature, localization |

**하나로 합치되 층을 나눈다. 소유자는 Radar 쪽 파일.**

```jsonc
{
  "id": "loss_defense",
  "profile_version": 3,               // 바뀌면 과거 판정이 무효가 된다
  "updated_at": "2026-09-03T00:00:00Z",

  "identity": {
    "name_ko": "제도와 현실의 덫",
    "name_ja": "知らないと損する、定年前後のお金と現実",
    "emoji": "🛡️",
    "audience": "50-69",
    "promise_ko": "…",
    "core_question_ko": "…",
    "tone_ko": "…"
  },

  "judgment": {                        // Radar / Strategist 가 읽는다
    "lenses": ["pension_trap", "tax_shock", "…"],
    "discovery_enabled": true,
    "production_enabled": false,
    "high_risk_topics": ["연금", "세금", "상속", "보험", "부동산"]
  },

  "production": {                      // AutoMaker 가 읽는다 (genres.json 의 필수 13항목)
    "structure_type": "INFO",
    "channel_persona": "…",
    "viewer_persona": "…",
    "speaking_style": "…",
    "title_patterns": [],
    "thumbnail_patterns": [],
    "forbidden_patterns": [],
    "ctr_hooking": "…",
    "retention_bridge": "…",
    "emotion_temperature": "…",
    "comment_emotion": "…",
    "localization": "…",
    "video_length": "15~20분",
    "lang": "ja"
  },

  "youtube": {                         // 성과 수집을 위해 필요. 지금은 null
    "channel_id": null,
    "channel_url": null
  }
}
```

**이행 방법:** AutoMaker 는 지금 `genres.json` 이 **비어 있다.** 즉 지금이
합치기 가장 싼 시점이다. `production` 블록을 `genres.json` 형식으로 내보내는
**단방향 export 한 개**만 만들면 되고, AutoMaker 코드는 손대지 않아도 된다.

> **주의:** `youtube.channel_id` 가 `null` 인 한 성과 수집은 시작할 수 없다.
> 이것이 Phase 4 의 실제 선행 조건이다.

---

## 3. Opportunity — Radar → Strategist

Radar 가 이미 가진 값만으로 만든다. 새 계산을 넣지 않는다.

```jsonc
{
  "opportunity_id": "opp_2026-09-03_DD3gDj8cKGo",
  "created_at": "2026-09-03T07:05:00Z",
  "status": "open",                    // open | decided | expired

  "source": {                          // videos.csv 그대로
    "video_id": "DD3gDj8cKGo",
    "url": "https://www.youtube.com/watch?v=DD3gDj8cKGo",
    "title": "…", "title_ko": "…",
    "channel_id": "UC…", "channel_name": "…",
    "published_at": "2026-08-20T09:00:00Z",
    "duration_seconds": 1380,
    "seed": "老後",
    "found_at": "2026-09-01T07:03:00Z"
  },

  "metrics": {                         // analysis.build() 의 그 시점 값
    "as_of": "2026-09-03T07:05:00Z",
    "views": 184203,
    "likes": 1620,
    "comments": 210,
    "channel_subscribers": 8400,
    "channel_video_count": 122,
    "age_days": 14.2,
    "age_bucket": "8-14",
    "age_bucket_n": 63,
    "adviews": 12971.0,
    "subscriber_view_ratio": 21.9,     // null 가능 — 구독 비공개 / 1,000 미만 / 매크 의심
    "engagement_per_1k": 8.8,
    "low_engagement": false,
    "age_adjusted_percentile": 94.2,
    "percentile_method": "bucket",     // bucket | median_ratio
    "svr_percentile": 97.1,
    "video_score": 95.4,
    "daily_view_gain": 8100.0,         // null 가능 — 스냅샷 1회 또는 간격 6시간 미만
    "gain_elapsed_days": 1.02
  },

  "channel_context": {                 // channels.csv (있을 때만)
    "channel_baseline": 4100,
    "channel_momentum": 0.82,
    "channel_score": 28.0,
    "score_basis": "baseline+momentum",
    "note": "영상만 터진 채널"          // video_score>=85 & channel_score<=30
  },

  "seed_standing": { "rank": 2, "of": 11, "recent_30d": 18, "before": 41 },

  "measurement_gaps": [                // «못 잰 것» 을 명시한다. 0 으로 채우지 않는다
    "daily_view_gain: 스냅샷 1회 — 측정 불가"
  ]
}
```

**규칙:** `metrics` 의 어떤 필드도 Strategist 가 다시 계산하지 않는다.
`null` 인 필드는 `measurement_gaps` 에 이유가 반드시 있어야 한다.

---

## 4. Evidence — 근거 조각

```jsonc
{
  "evidence_id": "ev_…",
  "opportunity_id": "opp_…",
  "kind": "transcript_digest",   // transcript_digest | comment_analysis | channel_fit
                                 // | seed_performance | competing_videos | own_history
  "source_ref": "data/raw/subs/DD3gDj8cKGo.ja.json3",
  "collected_at": "2026-09-02T18:47:00Z",
  "summary": "…",                // 사람이 읽을 요약 (자막 1,500자 / 댓글 2,500자 상한)
  "payload": { }                 // kind 별 구조. comment_analysis 는 아래
}
```

`comment_analysis` payload — **Radar 의 현재 출력 형식을 정본으로 삼는다.**
AutoMaker 의 `viewer_voice` / `viewer_emotions` / `viewer_phrases` 는 여기서 **파생**시킨다.

```jsonc
{
  "comment_count": 212, "analyzed_count": 30,
  "common_analysis": {
    "top_concerns": [], "questions": [], "fears": [],
    "desired_outcomes": [], "objections": [],
    "viewer_phrases": [{"ja": "…", "ko": "…"}],   // 원문 보존 — 번역 금지
    "unresolved_gaps": []                          // 가장 중요
  },
  "channel_angles": { "loss_defense": { "angle": "…", "unresolved_gaps": [] } }
}
```

> **매핑:** AutoMaker `viewer_phrases` ← `common_analysis.viewer_phrases[].ja` (원문만),
> `viewer_voice` ← `top_concerns` + `fears` 상위, `viewer_emotions` ← `fears` + `objections` 의 감정어.
> **AutoMaker 는 이 값이 들어오면 `analyze/source` 의 댓글 분석 부분을 건너뛴다.**

---

## 5. DecisionSnapshot — 판단 시점 동결 (**신규, 가장 중요**)

Radar 는 점수를 파일로 남기지 않는다. 매번 다시 계산한다.
**판단한 순간의 숫자를 얼리지 않으면 예측/실제 비교는 영원히 불가능하다.**

```jsonc
{
  "snapshot_id": "snap_…",
  "opportunity_id": "opp_…",
  "frozen_at": "2026-09-03T07:12:00Z",
  "code_version": "radar@7ebecad3",     // git commit
  "profile_version": 3,
  "config_digest": "sha256:…",          // config.py 의 가중치·임계값 해시
  "metrics": { /* Opportunity.metrics 를 그대로 복사 */ },
  "population": { "n_videos": 777, "n_snapshots": 1884, "n_in_bucket": 63 }
}
```

`config_digest` 가 있어야 «가중치를 바꾼 뒤의 점수와 바꾸기 전의 점수» 를
섞어 비교하는 사고를 막을 수 있다.

---

## 6. StrategyDecision — MAKE / WATCH / SKIP (**신규**)

```jsonc
{
  "decision_id": "dec_…",
  "opportunity_id": "opp_…",
  "snapshot_id": "snap_…",
  "channel_id": "loss_defense",
  "decided_at": "2026-09-03T07:20:00Z",

  "proposed_by": "ai",                 // rule | ai | human
  "decision": "MAKE",                  // MAKE | WATCH | SKIP
  "confidence": "MEDIUM",              // HIGH | MEDIUM | LOW
  "why_low": [],                       // confidence=LOW 면 비울 수 없다

  "rule_result": {                     // 규칙 엔진이 먼저 낸 결과 (재현 가능)
    "verdict": "MAKE",
    "passed": ["video_score>=85", "svr>=5", "engagement_ok"],
    "failed": []
  },

  "reasons_for": ["…", "…"],
  "reasons_against": ["…", "…"],       // **비울 수 없다.** 반대 근거가 없는 판단은 판단이 아니다
  "evidence_refs": ["ev_…", "ev_…"],

  "channel_fit": {                     // channel_fit.csv 그대로
    "audience_fit": "HIGH", "channel_relevance": "HIGH", "money_impact": "HIGH",
    "problem_strength": "MEDIUM", "longform_potential": "HIGH",
    "news_risk": "LOW", "evergreen_potential": "HIGH",
    "reason": "…", "angle_ko": "…"
  },
  "crossover": { "is_crossover": false, "channels": [] },

  "duplication_check": {
    "checked_against": 0,              // 지금은 제작 이력 0건
    "similar": [], "verdict": "no_history"
  },

  "prediction": {                      // 나중에 실제와 대조할 값. 비워도 된다
    "expected_views_7d": null,
    "expected_grade": "above_median",  // above_median | median | below_median | unknown
    "basis": "우리 채널 이력 없음 — 예측 불가"
  },

  "fact_check_required": true,
  "fact_check_topics": ["연금", "상속"],

  "human": {                           // **사람이 누르기 전에는 null**
    "approved": null, "approved_at": null, "override_reason": null
  }
}
```

**규칙**

- `human.approved` 가 `true` 가 아니면 AutoMaker 로 넘어가지 않는다.
- append-only. 마음이 바뀌면 새 레코드를 쓴다.
- `reasons_against` 가 비면 저장 거부 (`channel_fit.judge` 의 빈 판정 거부와 같은 패턴).

---

## 7. ProductionBrief — Radar → AutoMaker

**지금은 markdown 한 장이다. md 는 사람이 읽고, JSON 은 프로그램이 읽는다. 둘 다 낸다.**

```
data/briefs/{channel_id}/{video_id}.md      ← 지금 있는 것. 유지
data/briefs/{channel_id}/{video_id}.json    ← 신규
```

```jsonc
{
  "brief_id": "brf_…",
  "opportunity_id": "opp_…", "decision_id": "dec_…",
  "channel_id": "loss_defense",
  "generated_at": "2026-09-03T07:25:00Z",
  "profile_version": 3, "prompt_version": 1,

  "topic": {
    "working_title_ko": "…",
    "core_problem": "…",
    "target_viewer": "…",
    "why_now": "…",
    "angle": "…"                        // channel_fit.angle_ko
  },

  "must_cover": [],                     // unresolved_gaps 에서 나온 «기존 영상이 답하지 않은 것»
  "viewer_voice": { "phrases_ja": [], "concerns": [], "fears": [], "objections": [] },

  "reference": {                        // 원 영상 — «다시 쓰지 않는다. 수요의 증거로만»
    "video_id": "DD3gDj8cKGo",
    "transcript_digest": "…",
    "competing_titles": []
  },

  "production_hints": {                 // AutoMaker 3~6단계가 그대로 받는다
    "title_direction": "…",
    "hook_direction": "…",
    "tone": "…",
    "target_length": "15~20분",
    "avoid": ["원본 대본 장문 복사", "사실 검증 없는 단정",
              "같은 구성을 제목만 바꿔 두 채널에 올리기"]
  },

  "fact_check": {
    "required": true,
    "topics": ["연금", "상속"],
    "cleared": false,                   // 사람이 확인해야 true
    "cleared_by": null, "cleared_at": null
  },

  "skip_reanalysis": true               // AutoMaker 에게: analyze/source 를 다시 돌리지 마라
}
```

`skip_reanalysis` 가 이 계약의 실질적 이득이다 — **AutoMaker 3단계의 LLM 호출 4개
중 최소 2개(소재 분석·현지화 분석)를 건너뛸 수 있다.**

---

## 8. ProductionProject — AutoMaker → Strategist (읽기 전용)

AutoMaker 의 `project.json` 에 **필드 3개만 추가**한다. 나머지는 손대지 않는다.

```jsonc
{
  "version": "1.0", "name": "…", "created": "2026-09-03", "path": "…",
  "lang": "ja", "genre": "loss_defense",
  "channel": {…}, "source": {…}, "progress": {…},

  // ── 추가 3개 ──
  "opportunity_id": "opp_…",
  "decision_id": "dec_…",
  "brief_id": "brf_…"
}
```

`project.json` 저장 라우트는 **화면이 모르는 키를 지우지 않고 병합**하도록
이미 되어 있다(`/api/project/save`, 2026-07-30 주석). 따라서 이 3개 필드는
AutoMaker 코드를 고치지 않아도 살아남는다. **이것이 지금 통합에서 가장 싼 연결이다.**

---

## 9. Publication — 게시 기록 (**신규, 사람 입력**)

```jsonc
{
  "publication_id": "pub_…",
  "decision_id": "dec_…", "brief_id": "brf_…", "project_path": "C:/…",
  "channel_id": "loss_defense",
  "youtube_video_id": "abcd1234",       // ← 이것이 있어야 성과 수집이 가능하다
  "published_at": "2026-09-10T21:00:00+09:00",
  "format": "longform",                 // longform | shorts
  "title_ja": "…", "thumbnail_text": "…",
  "angle_used": "…", "hook_type": "질문형",
  "shorts_ids": []
}
```

**입력 수단:** AutoMaker 16단계(등록 가이드) 화면에 «게시한 URL 붙여넣기» 칸 하나.
그 한 칸이 Flywheel 의 유일한 입구다.

---

## 10. PerformanceSnapshot — 성과 관측 (**신규**)

```jsonc
{
  "publication_id": "pub_…",
  "youtube_video_id": "abcd1234",
  "collected_at": "2026-09-11T21:00:00Z",
  "hours_since_publish": 24,
  "bucket": "24h",                      // 24h | 72h | 7d | 30d
  "source": "youtube_data_api",         // youtube_data_api | manual_studio

  "views": 3120, "likes": 88, "comments": 14,
  "ctr": null,                          // Data API 로는 못 받는다 — Studio 수기 입력
  "avg_view_duration_sec": null,
  "retention_pct": null,
  "subscribers_gained": null
}
```

**중요:** `views`/`likes`/`comments` 는 **이미 있는 `snapshot_collector` 로 그대로
수집된다.** videos.list 는 50개 묶어 1 unit 이므로 비용이 사실상 0이다.
CTR·시청유지·구독전환은 YouTube Analytics API(OAuth 필요)이거나 Studio 화면 수기 입력이다.
**초기에는 수기 입력으로 충분하다. OAuth 를 먼저 붙이지 말 것.**

---

## 11. Outcome — 예측 vs 실제 (**신규, 4차**)

```jsonc
{
  "outcome_id": "out_…",
  "publication_id": "pub_…", "decision_id": "dec_…",
  "evaluated_at": "2026-09-18T00:00:00Z",
  "actual": { "views_7d": 5400, "ctr": 0.061, "avg_view_duration_sec": 420 },
  "channel_baseline_at_time": { "median_views_7d": null, "n_samples": 0 },
  "verdict": "unknown",                 // hit | partial | miss | unknown
  "hypotheses": ["…"],                  // LLM. 단정하지 않는다
  "reusable_patterns": [], "discard_patterns": []
}
```

`n_samples < 10` 이면 `verdict` 는 **항상 `unknown`** 이다.
**표본 3건으로 «이 각도가 잘 먹힌다» 고 말하기 시작하면 그때부터 시스템이 거짓말을 한다.**

---

## 12. AIRecommendation · Conversation

```jsonc
// AIRecommendation
{ "rec_id": "…", "created_at": "…", "kind": "daily_brief",
  "model": "gemini-3-flash", "prompt_version": 2,
  "input_refs": ["snap_…", "ev_…"],     // 프롬프트에 실제로 들어간 것만
  "text": "…", "claims": [ { "text": "…", "evidence_ref": "ev_…" } ],
  "unsupported_claims": [] }             // 근거를 못 붙인 문장. 화면에 배지로 표시

// Conversation
{ "conversation_id": "…", "created_at": "…", "title": "…",
  "messages": [ { "role": "user|assistant", "content": "…", "ts": "…",
                  "context_refs": [] } ] }
```

---

## 13. 저장 위치 (Phase 1 기준)

**새 DB 를 도입하지 않는다.** Radar 의 파일 규약을 그대로 늘린다.

```
data/config/channels.json                     ChannelProfile (합본)
data/raw/videos.csv                           SourceVideo
data/raw/video_snapshots.csv                  VideoSnapshot
data/processed/opportunities/{date}.jsonl     Opportunity (하루 한 파일, append)
data/processed/decisions.jsonl                StrategyDecision (append-only)
data/processed/snapshots/{decision_id}.json   DecisionSnapshot
data/briefs/{channel}/{vid}.md  +  .json      ProductionBrief
data/publications.jsonl                       Publication
data/raw/own_snapshots.csv                    PerformanceSnapshot (기존 형식 재사용)
data/processed/outcomes.jsonl                 Outcome
```

M1-2 과제로 Firestore 를 쓸 때는 **같은 스키마를 컬렉션으로 옮기기만 한다** —
`data`(PerformanceSnapshot/VideoSnapshot) · `conversations`(Conversation) ·
`decisions` · `opportunities`. 과제 요구사항 `data` / `conversations` 두 컬렉션과
정확히 겹친다.

---

## 14. 이 계약이 실제로 없애는 수작업

| 지금 | 계약 이후 |
|---|---|
| 화면에서 script_package 복사 | 파일로 자동 저장 |
| Claude 웹에 붙여넣고 대화 | (선택) 유지 — 다만 결과를 정해진 경로에 저장 |
| 대본을 AutoMaker 소재칸에 옮겨 붙이기 | `brief.json` 을 프로젝트 폴더에 두면 AutoMaker 가 읽는다 |
| AutoMaker 가 소재를 다시 분석 | `skip_reanalysis: true` 로 LLM 호출 2개 절약 |
| 왜 이 소재를 골랐는지 기억에 의존 | `decisions.jsonl` 에 근거·반대근거·confidence 가 남는다 |
| 성과를 눈으로 보고 잊음 | `publications.jsonl` + 자동 스냅샷 |
