# RADAR Decision Assistant

RADAR 가 찾은 콘텐츠 후보를 **AutoMaker 가 제작할 수 있는 결정으로 바꾸는** 중간 판단 계층입니다.

```
RADAR                  Decision Assistant              AutoMaker
소재 발견·수집  →   저장 → 분석 → 요약 → AI 판단 → 결정 기록   →   콘텐츠 제작
                              (이 프로젝트)
```

---

## 1. 무엇을 해결하는가

RADAR 는 하루에도 수십 건의 소재 후보를 찾아냅니다. 문제는 그다음입니다 —
**"이 중에 뭘 만들지"** 를 사람이 매번 감으로 정하고, 왜 그렇게 정했는지는
어디에도 남지 않았습니다.

이 서비스는 그 사이를 메웁니다.

| 없을 때 | 있을 때 |
|---|---|
| 후보가 흩어져 있고 전체 그림이 없다 | 기간·평균·추세·판단 분포를 한 화면에서 본다 |
| "이거 만들까?"를 감으로 판단한다 | 저장된 데이터를 근거로 AI 에게 묻는다 |
| 왜 만들기로 했는지 기록이 없다 | MAKE/WATCH/SKIP 과 사유가 남는다 |
| AutoMaker 로 넘길 때 맥락이 끊긴다 | 근거가 붙은 인계 파일이 생성된다 |

**일반적인 유튜브 조언 챗봇이 아닙니다.** AI 는 저장된 RADAR 후보 데이터만
근거로 답하고, 데이터에 없는 것은 "저장된 데이터에는 없습니다"라고 말합니다.

---

## 2. 기술 스택

| 계층 | 사용 기술 |
|---|---|
| Backend | Python 3.11, FastAPI, Pydantic v2, uvicorn |
| Database | Firebase Firestore (`firebase-admin`) — 미설정 시 in-memory 폴백 |
| AI | OpenAI Chat Completions (호환 프록시 지원) — 미설정 시 규칙 기반 계산 응답 |
| Frontend | HTML + CSS + Vanilla JavaScript (프레임워크 없음) |
| Deploy | Backend → Render · Frontend → Vercel |

---

## 3. 배포 URL

> ⚠️ **현재 미배포 상태입니다.** Render·Vercel 계정 연결 및 환경 변수 설정 후 아래 URL이 채워집니다.  
> 지금은 [로컬 실행 방법](#4-로컬-실행-방법)으로 서비스를 확인할 수 있습니다.

| 항목 | 상태 | URL |
|---|---|---|
| Frontend (Vercel) | 🔴 미배포 | — |
| Backend API (Render) | 🔴 미배포 | — |
| Swagger UI | 🔴 미배포 | — |
| Health check | 🔴 미배포 | — |

**배포 전 필요 작업**

1. Render에서 Web Service 생성 → `OPENAI_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_JSON` 환경 변수 입력
2. Vercel에서 프론트엔드 배포 → `API_BASE_URL`을 Render URL로 설정
3. Render URL을 Backend의 `ALLOWED_ORIGINS`에 추가

> **배포 후 참고**: Render 무료 플랜은 15분간 요청이 없으면 서버가 잠듭니다.
> 첫 요청이 **최대 50초** 걸릴 수 있습니다. 느린 첫 응답은 실패가 아닙니다.

---

## 4. 로컬 실행 방법

### 4-1. 백엔드

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # macOS/Linux: cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>

**키가 없어도 실행됩니다.** 대신 `/api/health` 가 어떤 모드인지 알려주고,
화면 상단에 경고 배너가 뜹니다. 키 없이 조용히 가짜 응답을 주는 상태가
가장 위험하기 때문에 반드시 표시합니다.

### 4-2. 표본 데이터 적재

```bash
python sample_data/generate.py                       # 168건 생성 (선택)
curl -X POST "http://127.0.0.1:8000/api/data/import?source=sample&replace=true"
```

화면의 **[표본 적재]** 버튼으로도 됩니다.

### 4-3. 프론트엔드

```bash
cd frontend
python -m http.server 8080
```

<http://127.0.0.1:8080> 접속. 백엔드 주소가 다르면 우측 상단 **⚙** 에서 바꿉니다
(브라우저에 저장됩니다).

---

## 5. 환경 변수

| 변수 | 필수 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | 권장 | 없으면 규칙 기반 계산 응답으로 동작 |
| `OPENAI_BASE_URL` | **프록시 사용 시 필수** | OpenAI 호환 게이트웨이 주소. 비우면 `api.openai.com` 으로 나갑니다 |
| `OPENAI_MODEL` | 선택 | 기본 `gpt-5-mini` |
| `OPENAI_MAX_TOKENS` | 선택 | 기본 `800` — 과금 통제용 상한 |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | 권장 | 서비스 계정 키 **JSON 전체**를 한 줄로. 없으면 메모리 저장(재시작 시 소멸) |
| `FIRESTORE_COLLECTION_DATA` | 선택 | 기본 `data` |
| `FIRESTORE_COLLECTION_CONVERSATIONS` | 선택 | 기본 `conversations` |
| `ALLOWED_ORIGINS` | 배포 시 필수 | CORS 허용 도메인. 예: `https://my-app.vercel.app` |
| `RADAR_ROOT` | 선택 | 실제 RADAR 저장소 경로(**읽기 전용**). 비우면 표본만 사용 |
| `DEBUG` | 선택 | `true` 면 `/api/chat/preview` 진단 경로가 열립니다. **운영에서는 반드시 끄세요** (기본 꺼짐) |

키는 코드에 넣지 않습니다. `.env` 는 `.gitignore` 에 있습니다.

---

## 6. API

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/health` | 구동 모드·의존성 상태 |
| GET | `/api/data` | 후보 목록 (`channel`/`decision`/`source` 필터) |
| POST | `/api/data` | 후보 추가 |
| GET | `/api/data/{id}` | 후보 단건 |
| PUT | `/api/data/{id}` | 후보 수정 (부분 수정) |
| DELETE | `/api/data/{id}` | 후보 삭제 |
| **GET** | **`/api/data/summary`** | **AI 프롬프트 주입용 요약** |
| PATCH | `/api/data/{id}/decision` | MAKE/WATCH/SKIP 변경 |
| POST | `/api/data/import` | 어댑터에서 일괄 적재 (`source=sample\|radar`) |
| GET | `/api/data/sources` | 데이터 소스 상태 |
| POST | `/api/chat` | 데이터 기반 AI 대화 (대화 자동 저장) |
| POST | `/api/chat/preview` | **[DEBUG 전용]** 주입될 System Prompt 확인. 운영 기본 **404**, Swagger 미노출 |
| GET | `/api/conversations` | 대화 목록 (**본문 제외**) |
| POST | `/api/conversations` | 대화 저장 |
| GET | `/api/conversations/{id}` | **대화 불러오기 (전체 messages)** |
| DELETE | `/api/conversations/{id}` | 대화 삭제 |
| GET | `/api/handoff` | 인계 파일 목록 |
| POST | `/api/handoff/{id}` | MAKE 후보를 인계 파일로 생성 |

### Summary 응답 예시

```json
{
  "period": "2026-06-27 ~ 2026-09-11",
  "count": 168,
  "metrics": { "average_score": 40.5, "max_score": 86.3, "min_score": 3.0 },
  "trend": "최근 7일 평균 46.5점 — 직전 구간과 유지(+0.5)",
  "decisions": { "MAKE": 3, "WATCH": 28, "SKIP": 78, "PENDING": 59 },
  "top_topics": ["定年後 孤独", "熟年離婚", "年金 損"],
  "channels": { "solo_pride": 98, "loss_defense": 70 },
  "source_mix": { "sample": 168 }
}
```

---

## 7. AI 컨텍스트 주입과 환각 방지

```
질문 → /api/data/summary 계산 → 관련 후보 선별(최대 25건)
     → System Prompt 에 [데이터 요약] + [후보 목록] 주입 → GPT 호출
     → 답변 반환 + conversations 자동 저장
```

### 주입 내용을 눈으로 확인하는 법 — `DEBUG=true` 전용

답변 문장만으로는 컨텍스트 주입이 실제로 일어났는지 증명되지 않습니다
(모델이 우연히 맞게 답할 수도 있습니다). 그래서 주입 **직전 문자열 자체**를
돌려주는 경로를 뒀습니다. 모델을 부르지 않으므로 과금이 없습니다.

> ⚠️ **운영에서는 기본 차단됩니다.** 이 응답에는 내부 지시문 전문과 후보
> 데이터가 들어 있습니다. `DEBUG=true` 일 때만 동작하고, 꺼져 있으면
> **404**(403 이 아니라 — 403 은 "여기 뭔가 있다"를 알려 줍니다)로 답하며
> Swagger 에도 **절대 노출되지 않습니다**(`include_in_schema=False`).

```bash
# 개발 환경에서만
DEBUG=true uvicorn app.main:app --port 8000

curl -X POST http://127.0.0.1:8000/api/chat/preview \
  -H "Content-Type: application/json" -d "{\"message\":\"MAKE 후보만 보여줘\"}"
```

컨텍스트 주입은 이 경로 없이도 **테스트로 증명**됩니다 —
`tests/test_edge_cases.py::TestContextInjection` 이 모델에 보내는 `messages[0]`
을 직접 가로채 Summary 수치와 후보 번호가 들어 있는지 확인합니다.

```json
{
  "selection_basis": "decision",
  "summary_injected": { "count": 168, "metrics": { "average_score": 40.5 }, "...": "..." },
  "candidates_injected": 3,
  "total_candidates_in_store": 168,
  "system_prompt_chars": 3327,
  "system_prompt": "당신은 RADAR Decision Assistant다 … [데이터 요약] … #1 [표본] …"
}
```

### 선별 근거를 숨기지 않습니다 — `selection_basis`

| 값 | 의미 |
|---|---|
| `decision` | 질문에 MAKE/WATCH/SKIP 이 있어 그 상태로 걸렀다 |
| `keyword` | 질문의 낱말이 채널·주제·제목과 일치했다 |
| `top_score` | 일치가 없어 점수 상위로 채웠다 |

`top_score` 일 때는 프롬프트와 화면 양쪽에 **"질문의 낱말과 일치한 후보가 없어
점수순으로 채웠습니다"** 를 함께 띄웁니다.

없는 채널(`money_retirement`)이나 없는 소재(`비트코인`)를 물었을 때, 점수 상위
후보를 조용히 끼워 넣으면 **후보 자체는 진짜여도 «질문에 대한 답»으로는 거짓**이
됩니다. 실제로 구현 중 이 문제가 발생했고, 선별 근거를 함께 반환하도록 고쳤습니다.

### OpenAI 호환 프록시 지원

과정에서 제공하는 게이트웨이처럼 **OpenAI 호환 엔드포인트**를 쓸 수 있습니다.
`OPENAI_BASE_URL` 만 지정하면 되고 코드 변경은 필요 없습니다.

```bash
# backend/.env
OPENAI_API_KEY=<발급받은 virtual-key>
OPENAI_BASE_URL=https://copa.codyssey.kr/v1
OPENAI_MODEL=gpt-5-mini
```

> ⚠️ **`OPENAI_BASE_URL` 을 비워 두면 401 이 납니다.** SDK 기본값이
> `api.openai.com` 이라 프록시용 virtual-key 가 거부됩니다. 이 값이 비어 있으면
> `base_url` 인자를 아예 넘기지 않아 SDK 기본 동작이 유지됩니다(테스트로 고정).

`/api/health` 가 실제로 어디로 나가는지 알려 줍니다 — 키는 노출하지 않습니다.

```json
{ "openai_configured": true, "openai_model": "gpt-5-mini",
  "openai_endpoint": "https://copa.codyssey.kr/v1" }
```

게이트웨이의 CHAT 모델(과정 콘솔 기준): `gpt-5-mini`(0.5) ·
`claude-haiku-4`(0.5) · `gemini-3.1-flash-lite`(0.5) ·
`claude-sonnet-4`(1) · `gemini-3.1-pro`(1.5). 과제 요구가 GPT 이므로
기본값은 **`gpt-5-mini`** 입니다.

### AI 응답과 대체 응답을 섞지 않습니다 — `answer_source`

규칙 기반 결과를 GPT 응답처럼 보여주는 것이 가장 나쁜 표시 방식입니다.
화면이 모델명 문자열을 보고 추측하지 않도록 **전용 필드**로 못박습니다.

| `answer_source` | 화면 배지 | 색 | 의미 |
|---|---|---|---|
| `openai` | **AI 응답** | 초록 | 실제 GPT 응답 |
| `rule_based` | 규칙 기반 대체 응답 | 주황 | 키가 없어 계산 결과로 대체 |
| `error_fallback` | AI 호출 실패 → 대체 | 빨강 | 호출 실패로 대체 |
| `missing_package` | openai 미설치 → 대체 | 빨강 | 키는 있으나 패키지 없음 |

대체 응답은 첫 줄에도 그 사실을 적습니다. 다만 **네 줄 구조는 동일**하므로
키를 넣어도 화면 구조가 달라지지 않습니다.

### 환각 방지 4겹

1. 후보를 **번호가 붙은 목록**으로 주고, 답변에서 `#3` 형식으로 인용하게 합니다.
2. 행마다 `[표본]` / `[실측]` 을 표시해 둘을 섞어 단정하지 못하게 합니다.
3. **선별 근거**를 프롬프트에 명시해, 일치하지 않은 목록을 검색 결과로 오인하지
   않게 합니다.
4. API 키가 없을 때 그럴듯한 문장을 지어내는 대신, **계산 결과만** 돌려주는
   규칙 기반 응답으로 떨어지고 그 사실을 답변 첫 줄에 밝힙니다.

### 답변 구조

특정 후보를 논할 때는 **관찰과 해석을 분리**한 네 줄 구조를 씁니다.

```
후보: #1 終活 一人｜専門家が語る本当の話
판정 제안: MAKE
근거 데이터: 86.3점 · solo_pride · 2026-08-27 · 현재 상태 MAKE · [표본]
판단 이유: 전체 평균 40.5점 대비 +45.8점으로 상위 구간이다.
```

`근거 데이터`는 목록의 값을 그대로 옮긴 것이고, `판단 이유`는 거기서 끌어낸
해석입니다. 규칙 기반 응답도 **같은 구조**로 내므로, 키를 넣어도 화면이
달라지지 않습니다.

---

## 7-B. MAKE / WATCH / SKIP — 책임 범위

```
AI 제안  →  사용자 확인  →  MAKE/WATCH/SKIP 저장  →  MAKE 인 경우만 Handoff
```

| 상태 | 의미 |
|---|---|
| `MAKE` | 지금 제작 대상으로 넘길 가치가 있음 |
| `WATCH` | 가능성은 있으나 추가 관찰·검토 필요 |
| `SKIP` | 현재 제작 우선순위에서 제외 |
| (없음) | 아직 판단하지 않음 — 새 상태를 만들지 않고 `null` 로 둡니다 |

- **AI 판단만으로 AutoMaker 를 실행하지 않습니다.** AI 는 `판정 제안`만 내고,
  상태 저장은 화면의 버튼(`PATCH /api/data/{id}/decision`)으로만 일어납니다.
- 이미 사용자가 정한 판단이 있으면 규칙 기반 제안이 **그것을 뒤집지 않습니다.**
- 판단을 바꿨는데 사유칸이 이전 판단의 근거 그대로면, 그것을 새 판단의 근거로
  넘기지 않습니다. SKIP 사유가 MAKE 의 근거로 인계 파일에 실리면 나중에 왜
  만들기로 했는지 되짚을 수 없기 때문입니다.
- `MAKE` 가 아닌 후보를 인계하려 하면 **409** 로 거부하며, 상태를 대신
  바꿔주지 않습니다.

---

## 8. 데이터 소스 — 표본과 실측의 구분

| | 표본 (`sample`) | 실측 (`radar`) |
|---|---|---|
| 출처 | `sample_data/candidates.json` | `RADAR_ROOT` 의 `outbox/*.json` 또는 `data/decisions.jsonl` |
| 점수 | 생성된 값 | **RADAR 가 계산한 값만** 사용 |
| 표시 | 화면·API 에 `표본` | 화면·API 에 `실측` |
| `radar_id` | `SAMPLE_0001` 접두어 | 실제 `video_id` |

- 표본 어댑터는 파일이 `source: "radar"` 라고 주장해도 **`sample` 로 덮어씁니다.**
- RADAR 어댑터는 **읽기만** 합니다. 점수를 새로 계산하지 않고, 없으면 그 후보를
  건너뜁니다. 실제 RADAR 로 갈아탈 때 바꾸는 지점은
  [`build_source()`](backend/app/adapters/sources.py) 한 곳입니다.

### RADAR envelope 은 v2 가 필요합니다 (실측 확인)

실제 아카이브(`.radar-intake/1.json`)를 확인한 결과 **`schema_version: 1`** 이었고,
`demand`(점수) · `discovery`(시점) · `decision` 필드가 **아예 없습니다.** 이 필드들은
RADAR 의 structured v2 에서 추가된 것입니다.

따라서 현재 실측 어댑터는 v1 envelope 을 건너뜁니다. 점수가 없는데 만들어 넣을 수는
없기 때문입니다. 다만 **왜 0건인지 반드시 표시합니다** —

```json
"skipped": { "schema_version 1 — 점수·시점 필드 없음 (v2 필요)": 1 }
```

`GET /api/data/sources` 와 `POST /api/data/import` 응답에서 확인할 수 있습니다.
표시 없는 0건은 원인을 알 수 없게 만들므로, 조용히 비우지 않습니다.

실제 연동 조건: RADAR 가 v2 로 패키지를 내보내고 `RADAR_ROOT/outbox/*.json` 에
쌓이면 그때부터 `source=radar` 로 적재됩니다. 코드 변경은 필요 없습니다.

---

## 9. AutoMaker 인계

MAKE 로 확정한 후보만 `handoff/<시각>_<radar_id>.json` 으로 남깁니다.

```json
{
  "radar_id": "SAMPLE_0112",
  "decision": "MAKE",
  "channel": "loss_defense",
  "topic": "年金 損",
  "title": "【年金 損】知らないと損する3つのこと",
  "score": 86.7,
  "reason": ["최근 상승세가 강함", "채널 적합성이 높음", "기존 콘텐츠와 중복도가 낮음"],
  "selected_at": "2026-09-11T00:00:00+00:00",
  "source": "sample",
  "candidate_id": "88d642ff66c34b4f"
}
```

**인계는 파일 생성까지입니다.** AutoMaker 를 실행시키거나 AutoMaker 의
데이터·파이프라인을 수정하지 않습니다. 언제 집어갈지는 AutoMaker 가 정합니다.

---

## 9-B. Firestore 구조

컬렉션은 **두 개만** 둡니다. 판단(decision)은 별도 컬렉션을 만들지 않고 후보
문서의 필드로 둡니다 — 판단은 후보의 *상태*이지 독립 개체가 아니기 때문입니다.

```
data/{docId}                          후보 (과제 필수 3필드 + RADAR 확장)
  ├─ date: timestamp                  ← 필수
  ├─ value: number (0~100)            ← 필수. RADAR video_score
  ├─ memo: string                     ← 필수
  ├─ radar_id: string | null          RADAR opportunity_id
  ├─ channel: string | null           RADAR target_channel.id
  ├─ topic / title: string | null
  ├─ radar_score: number | null
  ├─ decision: "MAKE"|"WATCH"|"SKIP"|null
  ├─ decision_reason: string
  ├─ source: "sample"|"radar"|"manual"
  └─ created_at / updated_at: timestamp

conversations/{docId}                 대화 기록
  ├─ title: string
  ├─ messages: [{ role, content }]    role: user|assistant|system
  └─ created_at / updated_at: timestamp
```

**자격증명이 없으면 in-memory 로 떨어집니다.** 그 상태를 정상처럼 보여주지
않도록 `/api/health` 가 `store_is_persistent: false` 와 경고를 반환하고,
화면 상단에도 배너가 뜹니다.

| | Firestore | in-memory |
|---|---|---|
| 브라우저 새로고침 후 유지 | ✅ | ✅ (서버가 살아 있으므로) |
| **서버 재시작 후 유지** | ✅ | ❌ **소멸** |

---

## 10. 테스트

자동 테스트와 브라우저 수동 검증을 구분해 기록합니다.

### 10-1. 백엔드 자동 테스트 — 76 passed / 0 failed

```bash
python -m pytest tests/test_units.py tests/test_edge_cases.py -q   # 54 passed
python tests/smoke_test.py                                          # 22 passed
python tests/verify_openai.py    # 실제 GPT 검증 — OPENAI_API_KEY 필요
```

| 파일 | 수 | 무엇을 보는가 |
|---|---:|---|
| `test_units.py` | 21 | 계산이 맞는가 — Summary·어댑터·Handoff |
| `test_edge_cases.py` | 33 | 틀린 입력에 조용히 답하지 않는가 + **컨텍스트 주입 증명** + DEBUG 게이트 |
| `smoke_test.py` | 22 | **실제로 뜨는가** — 진짜 서버 + HTTP |
| `verify_openai.py` | 7문항 | **실제 GPT 응답인가** — 키가 있을 때만 |

`verify_openai.py` 는 `answer_source == "openai"` 일 때만 PASS 를 줍니다.
규칙 기반 fallback 결과를 AI 검증으로 치지 않기 위해서입니다. 키가 없으면
아무것도 호출하지 않고 필요한 환경 변수만 알립니다.

`smoke_test.py` 는 **TestClient 를 쓰지 않습니다.** 실제로 uvicorn 을 띄우고
HTTP 로 호출합니다. TestClient 는 ASGI 앱을 프로세스 안에서 직접 부르므로
기동·포트 bind·직렬화 경계를 건너뛰는데, 바로 그 구간이 "테스트는 다
통과하는데 첫 화면이 죽는" 장애가 사는 곳이기 때문입니다.

**예외 케이스 검증**: 빈 데이터 · null/누락 필드 · 잘못된 decision 값 ·
Firestore 미설정 폴백 · OpenAI 호출 실패 · **openai 패키지 부재** ·
빈 채팅 입력 · 없는 conversation ID · 없는 data ID · 168건 전체 Summary ·
선별 근거 4종 · 범위 밖 점수(422).

### 10-2. 브라우저 수동 E2E — 14/14 PASS

실제 클릭·입력·새로고침으로 검증했습니다.

| # | 흐름 | 결과 |
|---|---|---|
| 1 | 후보 목록 표시 | PASS — 168행 |
| 2 | 파일 = API = Summary 일치 | PASS — 168/168/168 |
| 3 | Summary 표시 | PASS — 기간·평균·추세·분포·그래프·주제 |
| 4 | 후보 선택 | PASS — 선택 행 1개, 패널 렌더 |
| 5 | MAKE/WATCH/SKIP 변경 | PASS — 행·API·Summary 동시 갱신 |
| 6 | **새로고침 후 유지** | PASS (in-memory: 서버 재시작 시에는 소멸) |
| 7 | 채팅 입력 | PASS — 전송 후 입력칸 비움 |
| 8 | 로딩 표시 | PASS — 요청 중 표시·버튼 비활성, 완료 후 복구 |
| 9 | 저장 데이터 근거 답변 | PASS — 요약 168건 + 후보 주입 확인 |
| 10 | 대화 자동 저장 | PASS |
| 11 | 이전 대화 목록 | PASS — 본문 제외 |
| 12 | 대화 불러오기 | PASS — user/assistant 복원 |
| 13 | 대화 삭제 | PASS |
| 14 | MAKE → Handoff | PASS — 파일 생성, 사유 줄 분리 |

---

## 10-3. 과제 요구사항 대조표

| 요구사항 | 구현 위치 | 검증 방법 | 상태 |
|---|---|---|---|
| `POST /api/data` | [routers/data.py](backend/app/routers/data.py) `create_candidate` | 실측 201 · smoke S6 | **PASS** |
| `GET /api/data` | 같은 파일 `list_candidates` | 실측 200 · 브라우저 168행 | **PASS** |
| `PUT /api/data/{id}` | 같은 파일 `update_candidate` | 실측 200 · smoke S6c | **PASS** |
| `DELETE /api/data/{id}` | 같은 파일 `delete_candidate` | 실측 200 · smoke S10/S10b(404) | **PASS** |
| `GET /api/data/summary` | 같은 파일 → [services/summary.py](backend/app/services/summary.py) | 실측 200 · smoke S5 · 168건 계산 | **PASS** |
| `POST /api/conversations` | [routers/conversations.py](backend/app/routers/conversations.py) | 실측 201 | **PASS** |
| `GET /api/conversations` | 같은 파일 (본문 제외) | 실측 200 · smoke S9d | **PASS** |
| 대화 불러오기 | `GET /api/conversations/{id}` — 과제 (A)안 | 실측 200 · smoke S9e · E2E-12 | **PASS** |
| `DELETE /api/conversations/{id}` | 같은 파일 | 실측 200 · E2E-13 | **PASS** |
| `POST /api/chat` | [routers/chat.py](backend/app/routers/chat.py) | 실측 200 · smoke S9 | **PASS** |
| Context Injection | [services/chat.py](backend/app/services/chat.py) `build_context_block` | `/api/chat/preview` 로 주입 문자열 확인 (3,327자) | **PASS** |
| AI 자동 대화 저장 | `routers/chat.py` ⑤단계 | 채팅 후 목록에 즉시 생성 확인 | **PASS** |
| 데이터 관리 UI | [frontend/index.html](frontend/index.html) ① + `app.js` | E2E-1·추가 폼·✕ 삭제 | **PASS** |
| Summary UI | ② 영역 (통계·추세·분포·그래프·주제) | E2E-3 | **PASS** |
| Chat UI | ③ 영역 | E2E-7·9 | **PASS** |
| 로딩 표시 | `#chatLoading` + 버튼 비활성 | E2E-8 (요청 중 포착) | **PASS** |
| Conversation UI | ③ 상단 select + 삭제 | E2E-11·12·13 | **PASS** |
| MAKE/WATCH/SKIP | ④ 영역 + `PATCH .../decision` | E2E-5·6 | **PASS** |
| Handoff | [services/radar_bridge.py](backend/app/services/radar_bridge.py) — RADAR `automaker_intake.package()`+`send()` 호출 (v1 의 `handoff/*.json` 은 폐기: 읽는 쪽이 없었음) | smoke S7b/S8(409) · TestRadarBridge | **PASS** |
| 시계열 100건 이상 | [sample_data/candidates.json](sample_data/candidates.json) | 168건 / 75일 | **PASS** |
| CORS 설정 | [main.py](backend/app/main.py) `ALLOWED_ORIGINS` | 8081→8000 교차 호출 동작 | **PASS** |
| Swagger `/docs` | FastAPI 기본 | 실측 200 · smoke S3 | **PASS** |
| 키를 코드에 두지 않음 | [config.py](backend/app/config.py) · `.env` gitignore | 소스 내 키 문자열 0건 | **PASS** |
| Render 배포 | [render.yaml](render.yaml) | 정의 완료 · **배포 미실행** | 대기 |
| Vercel 배포 | [vercel.json](vercel.json) | 정의 완료 · **배포 미실행** | 대기 |
| Firestore 실연동 | [repositories/store.py](backend/app/repositories/store.py) | 코드 완료 · **자격증명 미설정** (in-memory 동작 중) | 대기 |
| 실제 GPT 응답 | [services/chat.py](backend/app/services/chat.py) | 코드 완료 · **API 키 미설정** (규칙 기반 동작 중) | 대기 |

**필수 기능 23/23 PASS.** 대기 4건은 모두 코드가 아니라 **외부 계정·키 발급**이
남은 항목입니다.

---

## 11. 제출 스크린샷

`docs/` 에 아래 3장을 넣습니다.

| 파일 | 담아야 할 것 |
|---|---|
| `01-chat.png` | ② 요약이 보이는 상태에서 ③ 채팅에 질문하고 답변이 온 화면 |
| `02-data.png` | ① 후보 목록 + [+ 추가] 로 데이터를 넣거나 ✕ 로 지운 직후 |
| `03-conversation.png` | ③ 상단 대화 선택으로 **이전 대화를 불러온** 화면 |

---

## 12. 이번 버전에서 하지 않은 것

- NotebookLM 자동 접속·입력, 영상 자동 생성, YouTube 자동 게시
- 새 scoring engine 개발 — RADAR 점수를 **그대로** 사용합니다
- RADAR / AutoMaker 재설계, 두 시스템 간 완전 자동 실행
- Function Calling / MCP — 기본 기능 완료 후 선택적 보너스 단계로 남깁니다

**AI 판단이 곧 제작 실행이 아닙니다.** MAKE 확정과 인계는 모두 사용자의
명시적 행위입니다.

---

## 13. 폴더 구조

```
m1-2-decision-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI 앱 · CORS · 전역 예외 핸들러
│   │   ├── config.py            환경 변수 (키는 코드에 없음)
│   │   ├── deps.py              의존성 주입
│   │   ├── models/schemas.py    Pydantic 계약
│   │   ├── repositories/store.py Firestore + 메모리 폴백
│   │   ├── services/            summary · chat · handoff (교체 가능하게 분리)
│   │   ├── routers/             data · conversations · chat · handoff
│   │   └── adapters/sources.py  표본 ↔ 실제 RADAR 전환 지점
│   ├── requirements.txt
│   └── .env.example
├── frontend/                    index.html · styles.css · app.js · config.js
├── sample_data/                 generate.py · candidates.json (168건)
├── handoff/                     인계 산출물 (gitignore)
├── tests/                       test_units.py · smoke_test.py
├── docs/                        제출 스크린샷
├── render.yaml                  Render 배포 정의
└── vercel.json                  Vercel 설정
```
