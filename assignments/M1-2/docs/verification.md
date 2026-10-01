# Phase 01 검증 기록

기준일: 2026-10-01. 실제 호출 결과만 완료로 기록한다. API 키와 사용자 자료 원문은 이 문서나 Git에 넣지 않는다.

## T01.01·T01.02

- 산출물 커밋: `424961b8` (`feat(M1-2): establish Phase 01 server baseline`).
- Python 3.11.9 환경에서 `python -m pytest server/tests -q`: **7 passed**.
- 키를 비운 상태로 Uvicorn을 실행해 `/health` HTTP 200(`ai`, `firebase` 모두 `missing`)과 `/docs` HTTP 200을 확인했다.
- Git 제외 확인: `.env`, `.env.codyssey`, `.venv`, `.pytest_cache`.

## T01.03 — Codyssey GPT 텍스트 호출

**상태: 당시 기준 통과.** 2026-10-01 로컬 smoke 호출이 Codyssey 프록시에서 성공했다. 요청·응답 모델은 `gpt-5-mini`였고, OpenAI SDK `3.22.1`에서 `choices[0].message.content`가 비어 있지 않은 텍스트로 반환됐으며 `finish_reason=stop`, 종료 코드 `0`을 확인했다.

2026-10-01 M1-1 재확인: `submission/src/config.py`의 프록시 주소는 `https://copa.codyssey.kr/v1`이고 기존 번역 모델은 `gemini-3-flash`다. `submission/src/translate.py`는 Bearer 인증으로 `/chat/completions`를 호출한다. 확인한 M1-1 `.env`에는 비어 있는 YouTube 키만 있으며 `OPENAI_API_KEY`는 없다. 인증 없이 `GET /v1/models`를 요청하면 HTTP 401이므로 GPT 모델명도 추측하지 않는다.

`server/scripts/smoke_ai.py`는 `M1-2/.env.codyssey`만 읽고 프록시 주소가 `https://copa.codyssey.kr/v1`인지 확인한다. 검증에 사용한 파일은 Git에서 제외되어 있으며 API 키 값은 이 문서와 저장소에 기록하지 않았다. `AI_PROVIDER_MODEL`은 `gpt-5-mini`로 설정했다.

Phase 01 연결 검증을 보충하면서 서버가 읽는 `.env`를 같은 Codyssey 설정으로 전환했고, 기존 Hermes 설정은 Git 제외 파일 `.env.hermes`로 보존했다. `AI_MAX_OUTPUT_TOKENS=1500`, `AI_TIMEOUT_SECONDS=60`을 적용했다. `max_completion_tokens=1500`을 지정한 1회 호출도 성공했으며 응답 모델 `gpt-5-mini`, `finish_reason=stop`, `completion_tokens=74`, `prompt_tokens=14`, `total_tokens=88`을 확인했다. 이 사용량은 검증용 단문 요청의 실측값이다.

```powershell
.\.venv\Scripts\python.exe server/scripts/smoke_ai.py --list-models
.\.venv\Scripts\python.exe server/scripts/smoke_ai.py
```

성공 결과는 요청 모델명, 응답 모델명, OpenAI SDK 버전, `choices[0].message.content` 비어 있지 않음, 종료 이유와 함께 위에 기록했다. 키가 비어 있을 때 스크립트는 호출 전에 종료 코드 1로 중단됐고, Hermes 설정 파일을 명시해도 주소 검사에서 호출 전에 중단됐다. 이번 검증 범위는 텍스트 호출이며 이미지 입력 지원, 비용, 한도는 아직 확인하지 않았다.

코드 리뷰에서 발견한 응답 종료 판정도 보완했다. 이제 본문이 있어도 `finish_reason`이 `stop`이 아니면 실패로 처리한다. `stop`, `length`, `content_filter`를 모의 응답으로 검증했고, 수정한 스크립트의 실제 Codyssey 재호출도 `finish_reason=stop`, 종료 코드 `0`으로 끝났다.

이 문단은 T01.03 당시의 설정 기록이다. 현재 MVP 서버 실행 경로는 아래 T01.04의 Hermes로 변경됐다. 실제 Adapter 구현에서는 `Settings.ai_max_output_tokens`와 `Settings.ai_timeout_seconds`를 사용한다.

## T02.01 — 단일 소유자 Google 로그인과 서버 인증

**상태: 통과.** 2026-10-01.

- Firebase 프로젝트 `ai-secretary-b5a7c`(Spark). Google 로그인 사용 설정, 승인 도메인 `localhost` 기본 포함, 웹 앱 `ai-secretary-web` 등록. Google Analytics·Firebase의 Gemini는 끈 상태로 생성.
- 서비스 계정 키는 `.env`의 `FIREBASE_SERVICE_ACCOUNT_JSON`(한 줄 JSON)에만 저장했다. 키 내용은 출력·기록하지 않았다. 웹 공개 설정은 Git 제외 파일 `web/js/config.js`.
- `python -m pytest server/tests -q`: **27 passed**(401 6종, 인증 전 모드 미검사, 403, `OWNER_UID` 누락 503, 422 4종, 소유자 통과 2종, Firebase 미설정 503, 서비스 계정 내용 미노출).
- 실제 브라우저(`http://localhost:5500/login.html` → API `:8000`, CORS `http://localhost:5500`):
  - 로그인 전 `GET /api/me` → HTTP 401.
  - Google 로그인 후 `GET /api/me`(`X-Data-Mode: personal`) → HTTP 200, `owner_id`가 로그인 UID와 일치.
  - 로그아웃 후 `GET /api/me` → HTTP 401(서버 로그로 확인).
- 확인한 제한: 정적 서버를 `127.0.0.1`에만 바인딩하면 `localhost`가 IPv6(`::1`)로 해석되는 브라우저에서 접속되지 않았다. `python -m http.server 5500 --bind ::`로 IPv4·IPv6 모두 응답한다.
- Firebase ID 토큰은 로그아웃 후에도 최대 1시간 유효하며, MVP는 토큰 폐기를 요구하지 않는다(미검증 범위 아님, 결정 사항).

### T02.01 최신 코드 재확인 — 2026-10-01

리뷰 수정(`auth.py`의 인증서 조회 실패 503, `auth.js`의 모드 필수·로그인 유지) 이후 최신 코드로 브라우저 흐름을 다시 확인했다. 서버 요청 로그: `GET /api/me 200`(11:26:18, Google 로그인 상태, `owner_id`가 로그인 UID와 일치) → 로그아웃 후 `GET /api/me 401`(11:27:36).

## T02.02 — Firestore 저장 구조·버전·중복 요청 처리

**상태: 통과.** 2026-10-01.

- `python -m pytest server/tests -q`: **68 passed**(소유자·모드 격리, 시스템 필드는 서버가 지정, 버전 409, 커서 페이지·정상 커서 왕복·잘못된 커서 13종 422(Base64 오류·객체 아님·필드 누락·UTC 아닌 시각·`/` 포함 ID 등), 형식이 틀린 문서 ID 404, 중복 요청: 같은 내용 재전송·다른 내용 409·키 없음 422·처리 중 409·실패 후 재시도·재시작 후 유지·1일 만료, HTTP 404/409/422 연결).
- 실제 Firestore(`server/scripts/check_firestore.py`, 임시 소유자 ID 사용, 종료 코드 0): 새 저장소 인스턴스(재시작 흉내)에서 같은 키 요청이 재전송되고 작업은 1회만 실행, 다른 모드 조회 404 대상, 이전 버전 수정 거부(현재 버전 2). 임시 자료 2건을 페이지 크기 1로 조회해 1페이지 다음 커서 있음 → 2페이지는 다른 자료 1건·다음 커서 없음. 목록 오류도 실패로 판정하며, 성공 여부와 관계없이 자료 2건과 중복 요청 기록을 지운다(`cleaned_up: true`).
- `firestore.rules`(전면 거부)·`firestore.indexes.json`(복합 색인 6개)을 `firebase deploy --only firestore`로 배포. 색인 생성 완료 전에는 목록 조회가 `FailedPrecondition`이었고 생성 후 정상.
- 클라이언트 직접 접근(REST): 공개 웹 API 키로 Firestore REST 읽기·쓰기 모두 HTTP 403 `PERMISSION_DENIED`.
- 클라이언트 직접 접근(Firebase 웹 SDK 10.12.2, 일회성 브라우저 콘솔 확인, 시험 페이지는 만들지 않음): `http://localhost:5500/login.html`에서 `getDoc`·`setDoc`·`getDocs`를 실행했다. 로그아웃 상태에서 읽기·쓰기 `permission-denied`, 소유자 Google 로그인 상태(같은 토큰으로 `/api/me` 200)에서 읽기·쓰기·목록 모두 `permission-denied`.
- HTTP 수준의 404/409/422는 시험용 라우트로 확인했다. 실제 자료 API에서의 확인은 T02.04·T03.01에서 이어진다.

## T02.03 — 10개 메뉴와 모바일 공통 화면

**상태: 통과.** 2026-10-01.

- 공개 설정 생성(`web/scripts/build-config.mjs`): `node --test web/scripts/build-config.test.mjs` **5 passed** — 값 누락 시 파일 미생성·실패, `http(s)`가 아닌 API 주소 거부, `.env`에서 공개 변수 4개만 읽고 서버 비밀값(`OPENAI_API_KEY`, 서비스 계정)은 결과에 없음, 환경변수 우선, 따옴표가 든 값도 문자열로만 들어감.
- 실제 생성: `.env`의 공개 값으로 `web/js/config.js` 생성, `git check-ignore web/js/config.js` 제외 확인, 생성 파일에서 비밀값 패턴 미검출. `config.example.js`는 `config.template.js`로 대체.
- 브라우저(`http://localhost:5500/`, 로그인 상태): 데스크톱에서 10개 메뉴 모두 해시·제목·선택 표시가 일치하고 S08·S09는 `확장 단계 예정 · PC 연결 안 됨`, 나머지는 예시 숫자 없는 빈 상태. 서버 확인(`/api/me`) 성공으로 안내 배너 없음. 새로 고침 후 콘솔 오류 없음.
- 390px: 같은 출처 390px iframe에서 확인(창 크기 변경이 화면 폭에 반영되지 않아 대체). 메뉴는 ☰로 접힘·열림(배경 막 표시), 메뉴 선택 시 이동 후 닫힘, 가로 스크롤 없음, 매우 긴 제목도 가로 넘침 없음.
- 표본 모드 전환 시 상단 `표본 자료` 배지와 화면 머리글 `표본 자료 보기` 표시.
- `web/js`에 `innerHTML`·`insertAdjacentHTML`·`document.write` 사용 없음(모든 문자열 `textContent`).
- 서버 테스트 `pytest server/tests -q`: 68 passed.
- 확인하지 못한 것: 실제 휴대폰 기기, 콜드스타트 안내 문구의 실제 표시(지연 서버에서 재현하지 않음), 401·403·503 배너의 브라우저 표시(분기 코드만 작성). 화면 캡처는 브라우저 도구의 캡처 시간 초과로 남기지 못했다.

### T02.03 코드 리뷰 보완 — 2026-10-01

- 잘못된 해시(`#constructor`, `#__proto__`, 미등록 키)는 `today` 화면으로 돌아가도록 수정했다. 실제 `currentKey()` 함수를 추출해 유효·무효 해시를 Node에서 확인했다.
- 두 요청이 함께 느릴 때 첫 요청이 끝나도 대기 안내가 남는지, 마지막 요청이 끝나면 사라지는지 모의 응답으로 확인했다. 모드 변경 전 `/api/me`의 늦은 응답이 현재 상태를 덮지 않도록 했다.
- 응답 본문 수신이 끊기면 네트워크 오류로 분류한다. 본문 수신이 끝날 때까지 대기 안내와 90초 제한을 유지한다. 지연·중단·시간 초과 본문과 HTTP 503을 모의 응답으로 확인했고, 재시도에 동일 `Idempotency-Key`를 사용하는지도 확인했다.
- `node --test web/scripts/build-config.test.mjs`: 5 passed. `pytest server/tests -q`: 73 passed(T02.02 회귀 테스트 추가 후 현재 수). `node --check`로 `app.js`, `api.js`, `build-config.mjs` 구문 확인. 리뷰 수정 뒤의 브라우저 화면과 실제 휴대폰은 다시 확인하지 않았다.

## T01.04 — Hermes 로컬 AI 경로 전환 (2026-10-01)

- 로컬 Hermes API의 인증된 `/v1/models`는 HTTP 200으로 `hermes-agent`를 반환했다. `/health/detailed`는 `ok`였고 `/v1/toolsets`의 29개 항목은 모두 `enabled=false`였다.
- `/api/model/options`에서 `openai-codex`와 Claude 구독 경로가 인증된 것을 확인했다. 기본 Claude `sonnet` 호출은 HTTP 200이어도 `finish_reason=error`였고, 응답 내용은 upstream 429를 알렸다. 이를 성공으로 처리하지 않는다.
- `provider=openai-codex`, `model=gpt-6-luna`를 명시한 짧은 텍스트 호출은 `finish_reason=stop`, 비어 있지 않은 응답, `total_tokens=1023`이었다.
- 서버 `.env`의 AI 설정만 Hermes 로컬 주소·경로·모델로 전환했다. Firebase 및 웹 설정은 유지했다. `.env`, `.env.hermes`, `.env.codyssey`는 Git 제외 파일이다.
- `server/scripts/smoke_hermes.py`를 Python `openai` SDK로 실행해 `success=true`, 응답 모델 `gpt-6-luna`, 정상 종료를 다시 확인했다. 키와 응답 원문은 출력하지 않았다.
- Hermes 호스트의 `platform_toolsets.api_server`를 `[no_mcp]`로 지정해 기본 MCP 도구도 제외했다. API 도구 세트 조회는 계속 전부 비활성으로 보이고, 설정 변경 후 스모크 호출도 정상 종료됐다.
- `pytest server/tests -q`: **101 passed**. 도구 활성·도구 목록 확인 불가·HTTP 200 오류 종료를 모의 응답으로 거부하는 테스트를 포함한다. `git diff --check` 통과, 세 AI 설정 파일의 Git 제외를 확인했다.
- 아직 확인하지 않은 것: 실제 AI Secretary 분석·채팅 API(해당 Task 미구현), Claude 경로의 한도 회복, Render에서 접근 가능한 Hermes 경로, 과제의 API 사용 조건 인정 여부.

## Tailscale Funnel Hermes Relay — 로컬 검증 (2026-10-01)

**상태: 로컬 relay 통과, Funnel 공개 연결·무인증 차단 확인, Render 원격 경로 미검증.**

- `pytest server/tests -q`: **119 passed**. relay 인증, 정확한 경로·메서드 allowlist, 쿼리 거부, 1 MiB 본문 제한, Hermes API 키 교체, timeout·연결 실패, loopback 실행 설정을 포함한다. `compileall`도 통과했다.
- 실제 로컬 relay(`127.0.0.1:8766`)를 통해 `GET /v1/toolsets`가 HTTP 200, 항목 29개, 전체 `enabled=false`로 응답했다. 잘못된 토큰은 401, `/v1/models` 및 쿼리 포함 요청은 404였고 Hermes에 전달되지 않았다.
- 기존 `HermesProvider`를 통해 relay 경유 텍스트 호출 1회를 확인했다. 요청 모델 경로 `openai-codex` / 응답 모델 `gpt-6-luna`, 비어 있지 않은 응답, Provider의 `finish_reason=stop` 검사 통과, 총 사용량 1,023 토큰이었다. 응답 원문과 키 값은 출력하거나 기록하지 않았다.
- relay access log는 비활성화했다. 로그 파일에서 relay 토큰, Hermes 키, 시험 입력 문구가 나오지 않음을 값 자체를 표시하지 않고 확인했다.
- `.env`에 별도 relay 토큰을 로컬 생성했고, `.env`가 Git 제외 대상임을 확인했다. 토큰은 기록하지 않는다.
- Tailscale Funnel을 활성화했다. `funnel status --json`에서 공개 HTTPS 443이 로컬 `127.0.0.1:8766`으로 연결됨을 확인했다. 공개 주소의 무인증 `GET /v1/toolsets`는 HTTP 401이었다. Render 환경변수 설정과 Render → Funnel → relay → Hermes의 인증된 왕복 검증은 남아 있다.

## T02.04 — 프로젝트·관심 분야·자료 모드 설정

**상태: 통과.** 2026-10-01. Open Decision 1은 2번(주 프로젝트 + 관련 프로젝트)으로 결정(`docs/decisions.md`).

코드 리뷰에서 서로 다른 요청 키로 프로젝트 이름을 동시에 생성·변경하면 이름 중복 검사가 원자적이지 않아 중복될 수 있음을 확인했다. 단일 요청 및 순차 요청 검증은 통과했으며, 동시 요청 보완은 후속 수정으로 남긴다.

- `server/tests/test_settings.py` 24개 포함 `pytest server/tests -q` **119 passed**: 프로젝트 생성·목록·수정·비활성, 이름 중복 409(대소문자·공백 무시), 입력 검증 422(빈 이름·길이 초과·허용 밖 필드), 버전 409, 키 없음 422, 같은 키 한 번만 생성, 모드 분리(다른 모드 404·같은 이름 허용), 설정 기본값(개인/표본), 저장·재조회 유지·버전, 저장 전 수정은 409, 기본 프로젝트는 같은 모드 활성 프로젝트만, 로그인 없는 접근 401.
- 실제 브라우저(최신 코드 API를 8001에 띄우고 표본 모드로만 시험): 저장 전 기본값 표시 → 프로젝트 추가 → 같은 이름(대소문자·공백만 다름) 거부 메시지 → 관심 분야(중복 제거)·기본 프로젝트 저장 → **새로 고침 후 유지**(모드도 표본으로 유지) → 개인 모드로 바꾸면 표본 프로젝트·설정이 보이지 않고 개인 기본값 표시 → 다시 표본으로 돌아오면 저장값 표시 → 비활성화하면 기본 프로젝트 선택지에서 빠짐. 안내 배너·오류 없음.
- 시험 뒤 정리: 표본 모드 프로젝트 1·설정 1·이번 시험의 중복 요청 기록 4건을 Admin SDK로 삭제(시험 전 표본 문서 0건 확인), 브라우저 모드는 개인으로 되돌림, `config.js`를 8000 주소로 다시 생성.
- 확인한 제한: 8000번 포트에 이 세션이 띄우지 않은 이전 코드의 API가 실행 중이어서 8001로 시험했다. 열린 대화 갱신은 대화 화면(T07)이 아직 없어 해당 없음 — 모든 화면이 모드 전환 시 다시 그려지고 늦게 도착한 이전 모드 응답은 버리도록 했다.
