# 채널 운영 판단 아키텍처 — Decision Assistant v3 설계

2026-09-14. 목표: «영상 1편을 잘 고르는 도구» 가 아니라, **하나의 채널을 장기간 운영하면서 수십~수백 편을
일관되게 판단하고, 적합한 화자와 제작 방식으로 AutoMaker 제작까지 잇는 시스템**.

방아쇠가 된 사례: 소재 `tV8q8bQ9vKc` «60대 집돌이는 돈을 지키는 전략인가» — 점수 95, RADAR 적합성
MEDIUM, 프로필 v3 에서 미평가(not_available) 인데 DA 는 점수만 보고 MAKE 를 제안했고, 그 패키지 1건으로
AutoMaker 채널 페르소나가 만들어져 채널이 «집돌이 채널» 로 기울었다.

---

## 1. 현재 데이터 흐름 (실측)

```
RADAR                                   DA (v2)                       AutoMaker
videos.csv / signal_history ─┐
analysis.build() ──▶ score   │   outbox.sqlite3 ──▶ RadarSource ──▶ 후보표
channel_fit.csv (LLM 판정)   │      (payload.production_signals)     select_candidates: 낱말일치→점수순
data/dna/<ch>.json           │                                       _suggest: score − 평균
channels.json (프로필 v3)    │                                            │ 사람 MAKE
decisions.jsonl ◀────────────┼──────────── DecisionsLedger ◀──────────────┘
automaker_intake.package() ◀─┴── RadarBridge(subprocess) ──▶ send() ──▶ intake.sqlite3 ──▶ project.json
   payload.decision = decisions.jsonl 마지막 줄                              draft-input(패키지 1건) ──▶ persona
```

## 2. 개념 ↔ 파일 관계 · Source of Truth

| 개념 | 정본 | 소유 | 비고 |
|---|---|---|---|
| Channel Profile (audience·promise·core_question·tone·lenses·profile_version) | RADAR `data/config/channels.json` | RADAR, 사람이 편집, git 동기화 | 코드가 쓰지 않는다 |
| **Channel Identity (문제공간·Pillars·Boundary·Narrator Pool)** | **신설** RADAR `data/config/channel_identity/<channel_id>.json` | DA 가 제안·사람이 승인·DA 가 기록 | profile_version 을 참조, identity_version 보유 |
| Benchmark DNA | RADAR `data/dna/<yt_channel>.json` | RADAR `channel_dna.run` | 구조 패턴 + 벤치마크 페르소나 |
| Channel Fit (소재×채널 LLM 판정) | RADAR `data/processed/channel_fit.csv` | RADAR `channel_fit.judge` | (video, channel, profile_version) 키 |
| Market signals | RADAR 패키지 `production_signals.{demand,discovery,patterns,similar}` | RADAR | DA 는 재계산하지 않는다 |
| **Episode Assessment (4층 판정 결과)** | **신설** RADAR `data/decision_assistant/assessments/<channel>/<video>.json` | DA | (video, identity_version, fit.analyzed_at) 로 캐시 |
| Decision (MAKE/WATCH/SKIP) | RADAR `data/decisions.jsonl` | DA·RADAR 공용 | `signals` 에 assessment 요약·narrator 동승 |
| Package → AutoMaker | RADAR `outbox.sqlite3` → AutoMaker `intake.sqlite3` → `project.json` | RADAR/AutoMaker | `payload.decision` 에 결정 전체, `payload.target_channel.identity` 에 승인된 Identity |
| AutoMaker channelPersona | `project.json.genre` | AutoMaker, 사람 승인 | Identity 에서 **파생** — 별도 정체성이 아님 |

원칙: **Identity 는 한 곳(RADAR data/config/channel_identity)**. RADAR 는 판단에, AutoMaker 는 제작 기준에 쓴다.
Episode(패키지) 는 Identity 를 **참조**만 하고 절대 생성 입력이 되지 않는다.

## 3. 현재 판단 로직의 문제 목록

| # | 문제 | 위치 | 결과 |
|---|---|---|---|
| P1 | 판단 = 점수 − 평균 | `services/chat._suggest` | Market ≠ Fit 구분 없음 |
| P2 | RADAR channel_fit 을 읽지 않음 | DA 전체 | relevance MEDIUM 을 무시하고 MAKE |
| P3 | fit 미평가/stale 을 점수가 덮음 | `_suggest` | v3 미평가인데 MAKE |
| P4 | Portfolio 관점 0 | — | 중복·편중·정체성 이동 감지 불가 |
| P5 | Narrator 개념 없음 | RADAR·DA·AutoMaker 모두 | AutoMaker «화자» 는 TTS 음성 id 뿐 |
| P6 | 페르소나 = 패키지 1건 역산 | AutoMaker `draft_input` | Episode → Identity 오염 |
| P7 | 후보 선별이 질문 낱말·점수 | `select_candidates` | 채널 운영 질문에 답 못함 |
| P8 | 1편짜리 vs 확장 소재 구분 없음 | — | 시리즈성 판단 부재 |

## 4. 데이터 모델 (Identity / Pillar / Narrator / Episode)

```jsonc
// data/config/channel_identity/loss_defense.json
{
  "channel_id": "loss_defense",
  "identity_version": 1,
  "built_on_profile_version": 3,
  "status": "proposed" | "approved",
  "audience": "…", "promise": "…", "problem_space": "…",
  "expectations": "시청자가 이 채널에서 기대할 수 있는 것",
  "pillars": [ {"id": "pension", "label": "연금·퇴직금 함정", "description": "…", "lenses": ["pension_trap"]} ],
  "boundary": { "in": ["정년 후 소비 감소", "고정비", "현금흐름"], "out": ["홈트레이닝", "외로움", "실내 취미"] },
  "narrator_pool": [ {"id": "experience", "role_type": "경험형", "label": "…", "viewpoint": "…", "tone": "…"} ],
  "proposal_basis": { "profile": "…", "dna": ["UC…"], "make_history": 1, "performance": 0 },
  "proposed_at": "…", "approved_at": null, "approved_by": null
}
```
- Pillar ↔ Narrator 는 **느슨한 연결**(narrator 에 `fits_pillars` 없음). Narrator 는 «설명 관점·역할» 이다.
- Narrator 수와 역할은 **시스템이 프로필+DNA+MAKE 이력+성과를 보고 제안**하고 사람이 승인한다.

```jsonc
// data/decision_assistant/assessments/loss_defense/tV8q8bQ9vKc.json
{
  "video_id": "…", "channel_id": "…", "identity_version": 1, "assessed_at": "…",
  "market":    {"level": "HIGH", "score": 95.0, "signals": {...}},
  "fit":       {"state": "VALID|STALE|NOT_EVALUATED|INVALID", "profile_version": 3, "evaluated_at": "…",
                "evaluation_basis": "sha256:…", "stale_reason": null, "channel_relevance": "MEDIUM", ...},
  "pillar":    {"id": "living_cost", "confidence": "…", "anchor_angle": "…"},
  "portfolio": {"duplicates": [], "pillar_balance": {...}, "boundary_risk": "HIGH", "boundary_reason": "…",
                "expansion_kind": "reinforce|extend|drift"},
  "series":    {"potential": "MEDIUM", "followups_in": [...], "followups_out": [...]},
  "narrator":  {"recommended": "experience", "why": "…"},
  "decision":  {"suggested": "WATCH", "blockers": [...], "gates": {"fit": "pass", "market": "pass", "portfolio": "warn", "production": "pass"}, "reasons": [...]}
}
```

## 5. 판단 파이프라인 (규칙 게이트 → AI 해석 → 사람 승인)

```
Identity 없음/미승인 ─────────────────────────────▶ REVIEW_REQUIRED (Identity 부터)
Gate 1 Channel Fit   fit.state ≠ VALID ─────────▶ REVIEW_REQUIRED (blocker fit_not_evaluated · RADAR 재판정 버튼)
                     relevance LOW ──────────────▶ SKIP
Gate 2 Market        level LOW ──────────────────▶ WATCH (우선순위 낮음)
Gate 3 Portfolio     duplicate ──────────────────▶ WATCH/SKIP · boundary_risk HIGH ─▶ WATCH(앵글 조건) · drift ─▶ WATCH
Gate 4 Production    brief 없음 / narrator 미정 ─▶ REVIEW_REQUIRED
통과 ────────────────────────────────────────────▶ MAKE 후보 + narrator 추천
```
- 점수는 Gate 2 입력 하나일 뿐이다. **Fit 미평가를 점수가 덮어쓰지 않는다.**
- AI 는 두 곳에만: (a) Identity 제안, (b) Episode 의 pillar·boundary·series·narrator 해석. 둘 다 캐시되고 근거를 남긴다.
- 최종 MAKE/WATCH/SKIP 은 사람이 누른다. DA 는 `suggested` 와 `blockers` 를 내고 원장 `signals` 에 남긴다.

## 6. Fit 상태 모델 · 재평가 정책

| 상태 | 조건 | 처리 |
|---|---|---|
| VALID | channel_fit.csv 에 (video, channel, **현재 profile_version**) 행 | 사용 |
| STALE | 행은 있으나 옛 profile_version. `evaluation_basis`(프롬프트가 쓰는 프로필 필드의 해시)가 같으면 `stale_reason=version_only` | RADAR `channel_fit.judge(force)` 로 재판정 — basis 가 같아도 RADAR 파일·패키지가 v3 로 맞춰져야 AutoMaker 가 not_available 을 받지 않는다 |
| NOT_EVALUATED | 행 없음 | 재판정 필요 |
| INVALID | 행 있으나 필드 결손 | 재판정 필요 |

재평가는 DA 가 계산하지 않고 **RADAR 의 `channel_fit.judge` 를 RADAR 런타임에서 호출**한다(프롬프트·CSV·모델 모두 RADAR 것). VALID 면 호출하지 않는다(RADAR 캐시).

## 7. RADAR → AutoMaker 전달 항목 (실측)

| 항목 | 전달 | 경로 |
|---|---|---|
| topic · brief · source_url · benchmark(video, dna) · audience(댓글) · rationale | ✅ | payload |
| score · growth · patterns · similar · channel_fit | ✅ | payload.production_signals |
| decision(MAKE·note·decision_id) | ✅ | payload.decision (decisions.jsonl 마지막 줄) |
| **channel_identity (pillars·boundary·narrator_pool)** | ❌ → ✅ | v3: `payload.target_channel.identity` |
| **pillar · narrator 추천 · assessment 요약** | ❌ → ✅ | v3: `payload.decision.signals` |
| 채널명·타깃·promise | ✅ | target_channel (AutoMaker 는 name_ko 만 씀) |

AutoMaker 중복 입력: 벤치마킹 URL(패키지에 channel_id 있음 — AutoMaker 미반영, 수동), 페르소나(승인 관문, 근거는 패키지 1건 → v3 에서 Identity 가 target_channel 에 실려 근거가 채널 수준이 됨), 화자(TTS 음성 선택은 AutoMaker 수동 — 추천 역할은 decision.signals 로 표시).

## 8. 최소 변경안

DA 안에서만 바꾼다. RADAR·AutoMaker 코드는 손대지 않고 **RADAR 의 함수를 부르고 RADAR 의 파일에 쓴다.**
1. `services/identity.py` — Identity 제안(AI)·저장·승인. 입력: 프로필 + DNA + decisions.jsonl MAKE 이력 + (있으면) outcomes.
2. `services/fit_state.py` — 상태 모델·basis 해시·RADAR 재판정 호출(subprocess).
3. `services/assessment.py` — Market/Fit/Pillar/Portfolio/Series/Narrator + 게이트 → suggested + blockers. 캐시 파일.
4. `decisions_ledger.append(..., signals=)` — assessment 요약·narrator 동승.
5. `radar_bridge` runner — `target_channel.identity` 주입. 승인된 Identity 가 없으면 주입하지 않고 보고.
6. `chat.py` — 컨텍스트에 Identity 요약·후보별 assessment 한 줄, 규칙 8항 «Episode 로 Identity 를 역산하지 않는다».
7. API: `/api/identity/{channel}` GET/propose/approve, `/api/assessment/{candidate}` GET/run, `/api/fit/{candidate}/reevaluate`.
8. 프론트: Identity 패널(제안→검토→승인), 후보 판정 패널(8항목 + suggested + blockers).

## 9. Version / Migration

- `channel_identity/*.json` 은 신설 — 기존 데이터 영향 없음. Identity 없으면 모든 후보가 REVIEW_REQUIRED (안전 쪽으로).
- `decisions.jsonl` 은 append-only. 기존 줄의 `signals: {}` 는 그대로. 새 줄부터 assessment 동승. RADAR 소비자(`automaker_intake`, `outcomes`)는 `signals` 를 통째로 옮기거나 무시하므로 호환.
- 패키지 payload 에 `target_channel.identity` 추가 → payload_hash 변경 → 새 revision. AutoMaker `validate` 는 추가 키 허용(실측). `source_pack.load_selected` 의 `digest(profile)` 은 channels.json 프로필 기준이라 영향 없음(identity 는 별도 파일).
- 성과(Closed loop): assessment 와 decision 이 `video_id`·`decision_id`·`identity_version` 을 갖고 있어 RADAR `outcomes` 가 붙으면 «판단 vs 성과» 를 identity_version 별로 맞댈 수 있다. 지금 만들지 않는다.

## 10. 테스트 계획

- 단위: fit 상태 4종 · basis 해시 · 게이트 규칙 표(각 blocker) · portfolio 중복/편중 · identity 승인 시 version 증가 · ledger signals 동승 · bridge identity 주입.
- 회귀(이번 소재): 기록된 입력(score 95, relevance MEDIUM, audience HIGH, money MEDIUM, angle «집돌이=경제전략», boundary in/out)으로 → suggested ≠ MAKE(by score), blockers 에 boundary/relevance 포함, narrator 추천 존재, 그리고 «왜 Episode 로 Identity 를 만들면 안 되는가» 가 assessment.reasons 에 문장으로 남는다.
- E2E: Identity 제안 → 승인 → fit 재판정(RADAR judge) → assessment → 결정 → package(identity 주입) → AutoMaker intake → 보관본에 identity·narrator 존재 확인.
