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

후속 코드 리뷰에서 이름 중복 검사의 동시성 문제와 비활성 기본 프로젝트가 설정에 남는 문제를 확인했다. 프로젝트 생성·이름 변경·기본 프로젝트 지정·비활성화는 소유자·모드별 저장소 잠금/트랜잭션으로 묶었다. 메모리 저장소의 동시 생성·동시 이름 변경과 비활성 기본값 해제는 회귀 테스트로 검증했다. 실제 Firestore에서도 임시 소유자·표본 모드로 같은 이름 동시 생성 시 1건만 성공하고, 기본 프로젝트 비활성화 시 설정이 비워지고 버전이 올라감을 확인했다. 시험 문서는 삭제했다.

후속 전체 검증: `pytest server/tests -q` **155 passed**, 웹 공개 설정 생성 테스트 **5 passed**. T03.01 목록 테스트는 생성 시각이 같은 문서의 ID 보조 정렬까지 확인하도록 수정했다.

- 초기 검증은 `server/tests/test_settings.py` 24개 포함 `pytest server/tests -q` **119 passed**였다. 이후 동시 생성·동시 이름 변경과 기본 프로젝트 비활성화 회귀 테스트를 추가했다. 프로젝트 생성·목록·수정·비활성, 이름 중복 409(대소문자·공백 무시), 입력 검증 422(빈 이름·길이 초과·허용 밖 필드), 버전 409, 키 없음 422, 같은 키 한 번만 생성, 모드 분리(다른 모드 404·같은 이름 허용), 설정 기본값(개인/표본), 저장·재조회 유지·버전, 저장 전 수정은 409, 기본 프로젝트는 같은 모드 활성 프로젝트만, 로그인 없는 접근 401을 확인했다.
- 실제 브라우저(최신 코드 API를 8001에 띄우고 표본 모드로만 시험): 저장 전 기본값 표시 → 프로젝트 추가 → 같은 이름(대소문자·공백만 다름) 거부 메시지 → 관심 분야(중복 제거)·기본 프로젝트 저장 → **새로 고침 후 유지**(모드도 표본으로 유지) → 개인 모드로 바꾸면 표본 프로젝트·설정이 보이지 않고 개인 기본값 표시 → 다시 표본으로 돌아오면 저장값 표시 → 비활성화하면 기본 프로젝트 선택지에서 빠짐. 안내 배너·오류 없음.
- 시험 뒤 정리: 표본 모드 프로젝트 1·설정 1·이번 시험의 중복 요청 기록 4건을 Admin SDK로 삭제(시험 전 표본 문서 0건 확인), 브라우저 모드는 개인으로 되돌림, `config.js`를 8000 주소로 다시 생성.
- 확인한 제한: 8000번 포트에 이 세션이 띄우지 않은 이전 코드의 API가 실행 중이어서 8001로 시험했다. 이후 로컬 `.env`의 `API_BASE_URL`과 생성한 `web/js/config.js`를 8001로 맞췄다. `/health` 200, 인증 없는 `/api/projects`·`/api/settings` 401로 최신 API 경로를 확인했다. 열린 대화 갱신은 대화 화면(T07)이 아직 없어 해당 없음 — 모든 화면이 모드 전환 시 다시 그려지고 늦게 도착한 이전 모드 응답은 버리도록 했다.

## T03.01 — URL·텍스트 입력·저장·상세 수정

**상태: 통과.** 2026-10-01. Open Decision 2는 1번(`save_reason` 별도 필드)으로 결정.

- `server/tests/test_material_intake.py` **32 passed**(전체 `pytest server/tests -q` 통과): URL만 → `link_only`·임시 표제는 도메인이며 저장 안 함·가짜 제목/요약 없음(A01), 제목만 접수, 설명·본문·저장 이유·메모 분리 보존, 빈 입력·저장 이유/메모만 422, http(s) 외·호스트 없음·공백 URL 422, 필드별 길이 초과 422(한도 안내, 입력값 미반환, 저장 안 됨)·한도 정확히는 통과, HTML 문자열 그대로 저장, 파일·상태·소유자 필드 거부, 접수 기록 동시 생성, 일괄 생성 원자성, 같은 키 1회 생성, 키 없음 422, 최신순 커서 페이지·모드 분리, 상세 조회·수정(제목 비우면 다시 `link_only`), URL 수정 거부·버전 409, 내용 전부 삭제 거부, 다른 모드 404, 프로젝트 참조 검증, URL 비교 키는 호스트·기본 포트만 정규화.
- 실제 Firestore(임시 소유자 ID 후 삭제): 자료와 접수 기록 일괄 생성, 최신순 커서 2페이지 순서 일치·마지막 페이지 종료. 최신순 목록을 위해 `materials` 내림차순 복합 색인을 추가 배포(생성까지 약 5분, 그 전에는 `FailedPrecondition`).
- 실제 브라우저(최신 코드 API를 8001, 표본 모드): 빈 목록 → URL만 접수 시 `링크만 저장됨 · 본문 미확인`과 `주소로 표시` → HTML 제목은 글자로 표시(요소 0개) → 저장 이유만·`ftp://`·201자 제목은 각각 안내 문구로 거부 → 상세에서 제목·본문 추가 후 `분석 시작 대기`, URL은 고칠 수 없음 안내 → **새로 고침 후 유지** → 개인 모드에서는 보이지 않음. 콘솔 오류·안내 배너 없음.
- 정리: 표본 자료 2·접수 기록 2·중복 요청 기록 3건 삭제(시험 전 표본 문서 0건 확인), 브라우저 모드는 개인. 이후 구형 API를 피하기 위해 로컬 `config.js`의 API 주소를 8001로 변경했다.
- 연결 실패 후 다시 시도는 같은 `Idempotency-Key`를 다시 보내도록 했다(실제 연결 끊김은 재현하지 않음).

## T03.02 — 동일 URL 확인과 세 가지 선택 (+ T03.01 리뷰 결함 수정)

**상태: 통과.** 2026-10-02.

- 리뷰에서 재현한 T03.01 결함 4건을 먼저 재현 후 수정: 잘못된 포트(`:abc`·`:99999`·`:-1`)가 500 → **422**, 쓰기 전 422·409가 요청 키를 `processing`에 남김 → `NoChange` 거부는 기록 해제, 입력창 `maxlength`가 붙여 넣은 내용을 조용히 자름 → 제거하고 보내기 전 같은 문구로 안내(250자 제목은 그대로 남고 안내 표시), IPv6 비교 키에서 대괄호 소실 → 유지.
- `server/tests/test_url_duplicates.py` 17개 포함 `pytest server/tests -q` **172 passed**: 위 결함 회귀, 같은 URL 409와 기존 자료 요약(본문·메모 미포함), 쿼리·경로가 다르면 다른 URL, 별도 저장만 접수 기록 증가, 메모 추가는 본문 유지·접수 기록 없음·같은 키 재전송 시 200 그대로·두 번 덧붙지 않음, 대상 없음·다른 URL·빈 메모 422, 버전 409, 2,000자 초과 422, 휴지통 후보 표시·메모 차단, 다른 소유자·모드는 후보 아님, 동시 첫 등록은 하나만 생성, 남은 예약 자동 정리, 별도 저장은 예약 안 씀.
- 실제 Firestore(임시 소유자 후 삭제): 중복 감지, 예약 문서 생성, 상태 201·201·200, 메모 덧붙임. 같음 조건 검색은 추가 색인 없이 동작.
- 실제 브라우저(표본 모드, 테스트 서버 8011): 같은 URL 재접수 시 선택 패널 → 메모 없이 '메모 추가'는 안내 → 메모 입력 후 추가하면 `[2026-10-02 추가] 다시 본 이유`가 붙고 본문 유지·새 행 없음 → '새 자료로 따로 저장'은 새 행 → 다음 재접수 때 후보 2개 → '기존 자료 열기'로 상세 열림. 콘솔 오류 없음. 이 과정에서 패널이 409 시점의 입력값을 써서 메모 추가가 안 되던 결함을 발견·수정 후 재확인.
- 정리: 표본 자료 2·접수 기록 2·URL 예약 1·중복 요청 기록 3건 삭제, 브라우저는 개인 모드. 8000·8001 포트는 다른 세션이 쓰고 있어 8011로 시험했다.

2026-10-02 후속 코드 리뷰 보완: `save_separately`를 처음 보는 URL에 직접 보내면 예약 없이 생성되던 문제를 재현하는 테스트를 먼저 실패시킨 뒤, 같은 소유자·모드의 기존 자료가 없으면 쓰기 없이 422로 거부하도록 수정했다. 동일 키 재전송도 422이며 자료·접수·예약·중복 요청 기록이 남지 않는다. 중복 선택 요청 중에는 선택 버튼과 접수 버튼을 비활성화하고 재클릭 실행을 막는다. 기존 비활성 버튼 상태와 실패 후 재시도를 확인하는 웹 테스트를 추가했다. 새 검증: `pytest server/tests -q` **173 passed**, `node --test web/scripts/build-config.test.mjs web/scripts/single-flight.test.mjs` **7 passed**, `node --check web/js/views/inbox.js` 통과. 이번 후속 검증에서 실제 브라우저 재시연은 하지 않았다. 동일 URL 후보가 10건을 넘을 때 일부만 표시되는 제한은 남아 있다.

## T03.03 코드 리뷰 보완 — 승인 충돌과 50건 단위 처리 (2026-10-02)

- 수정값이 있는 새 승인 요청에서 자료가 이미 승인됐으면 `conflict`와 현재 버전을 반환한다. 같은 키 재전송은 기존 응답을 재생하고, 수정값 없는 새 요청은 `already_approved`로 처리한다. 기존 테스트의 낡은 기대값을 고쳤다. 새 충돌 테스트는 수정 전 실패, 수정 후 통과했다.
- 검토 화면은 승인과 받은 자료로 되돌리기를 최대 50건씩 순서대로 전송한다. 묶음마다 새 요청 키를 쓰고, 전송 실패 뒤에는 다음 묶음을 멈춘다. 재시도는 실패한 묶음의 기존 요청 키를 재사용한다. 성공 항목만 목록에서 제거하고 실패·충돌 항목의 수정값은 남긴다. 51건 분할 및 중간 묶음 실패·재개를 웹 테스트로 확인했다.
- 실제 Chrome + 로컬 API(`localhost:5500` → `127.0.0.1:8012`)의 표본 모드에서 임시 자료 1건을 접수·검토로 이동했다. 한 화면에서 제목·중요도를 고친 상태로 두고 다른 화면에서 먼저 승인했다. 첫 화면의 승인 요청은 충돌로 처리됐고 수정값·최신 승인 상태·`수정값 저장` 버튼이 함께 보였다. 저장 후 Firestore에서 승인 상태, 고친 제목, `user_importance=high`를 확인했다. 시험 자료와 접수 기록은 삭제했다. `GET /api/materials?view=review`도 실제 Firestore에서 HTTP 200으로 응답했다.
- 단위 테스트와 실제 브라우저 검증은 이 수정 범위에 집중했다. 51건의 분할 처리와 실패 후 재개는 자동화 테스트로 확인했다. 51건을 실제 Firestore에 만들어 브라우저에서 승인하는 대량 시연은 후속 보완 검토로 남긴다. T03.03 완료 판정의 필수 조건으로 두지 않는다.
- 수정 후 전체 회귀: `pytest server/tests -q` **202 passed**, 웹 Node 테스트 **9 passed**, `node --check`(검토 화면·묶음 처리) 통과, `git diff --check` 종료 코드 0.

## T03.03 받은 자료·일괄 검토·보관 승인 — 2026-10-02

- 자동 시험: `pytest server/tests -q` **202 passed**(새 `test_review_approval.py` 28개 포함, 다른 세션 추가분 포함), `node --test web/scripts/*.test.mjs` 7 passed, `node --check` 화면 파일 통과.
- 실제 Firestore(임시 소유자 `check-t0303-…`, 표본 모드, 끝난 뒤 삭제): 새 복합 색인 배포 후 약 4분 빌드 대기. 받은 자료·승인 요청 목록 분리, 묶음 중 한 건만 충돌 시 `approved`·`conflict`, 같은 키 재전송은 같은 응답, 새 키 재전송은 `already_approved`이고 승인 시각·버전 유지, `is_kept` 참, 승인 뒤 승인 요청 목록에서 빠짐 — 모두 통과.
- 기존 자료 보정: `backfill_review_fields.py` 시험 실행 결과 소유자 자료 0건(개인·표본) → 실행 불필요.
- 실제 브라우저(표본 모드, 테스트 서버 8011·5511): 받은 자료에서 URL 자료 A·텍스트 자료 B·C 접수 → A·B만 골라 '검토로 이동'(2건 이동, C는 받은 자료에 남음) → 검토·승인에서 A만 선택하고 제목을 '승인 시험 A (고친 제목)', 중요도 '높음'으로 고쳐 승인(1건 승인, B는 목록에 남음) → 새로고침 뒤에도 승인 요청 목록 B, 받은 자료 C. 서버 값 A: `user_importance=high`, `review_status=approved`, `storage_approved_at` 있음, version 3. 콘솔 오류 없음.
- 발견·수정: 비활성 버튼이 활성처럼 보여(선택 0건일 때 승인 버튼) `.button:disabled` 스타일 추가.
- 정리: 이번 시험의 자료 3·접수 기록 3·URL 예약 1·중복 요청 기록 5건 삭제(다른 세션이 만든 표본 자료는 건드리지 않음), 브라우저는 개인 모드, `config.js` 원래대로.

## T03.04 나중에 보기·분석 제외·승인 상태 — 2026-10-02

- 자동 시험(.venv): `pytest server/tests -q` **227 passed**(새 `test_material_states.py` 24개, `test_firebase_init.py` 1개). `node --test web/scripts/*.test.mjs` 9 passed, 화면 파일 `node --check` 통과.
- 날짜 경과: 비교 기준일을 바꿔(오늘·어제·내일·지난 날짜) `revisit_due`만 바뀌고 상태·버전·승인 시각·보관 수명이 그대로임을 확인. 나중에 보기 자료는 `is_kept`·`chat_eligible`이 거짓.
- 실제 브라우저(표본 모드, 테스트 서버 8011·5511): D(다시 볼 날짜 10/3)·E(날짜 없음)를 나중에 보기로 → '나중에 볼 자료'에 '10월 3일에 다시 보기'·'날짜 없이 나중에 보기' 표시, 받은 자료에서 빠짐 → F 상세에서 'AI 분석 제외' 저장 → 태그 'AI 분석 제외'. 서버에서 D의 날짜만 10/1로 바꿔 날짜 경과를 재현 → 새로고침 뒤 D가 '다시 볼 날짜 지남 · 정리 후보'로 맨 위, 상태는 그대로 나중에 보기. F 제외도 유지 → D를 '검토로 이동' → 검토·승인 화면에 D. 서버 값: D 미검토·검토 요청·날짜 없음(v3), E 나중에 보기(v2), F `ai_excluded=true`·`analysis_status=awaiting_start` 유지(v2). 콘솔 오류 없음.
- 발견·수정: ① 서버를 막 켠 직후 동시에 온 요청 중 일부가 503(Firebase 앱 동시 초기화). 수정 전 코드에서 실패하는 시험을 먼저 확인한 뒤 잠금으로 고쳤고, 재시작 후 첫 동시 요청이 모두 정상. ② 날짜 입력이 체크박스 크기로 줄어 보이던 스타일, 상세의 'AI 분석 제외' 문구가 체크박스 아래로 내려가던 배치를 고침.
- 정리: 이번 시험의 자료 3·접수 기록 3·중복 요청 기록 7건 삭제, 브라우저 개인 모드, `config.js` 원래대로, 테스트 서버 종료.

### T03.04 코드 리뷰 보완 — 2026-10-02

- 나중에 보기 목록은 모든 페이지를 모은 뒤 기한 경과 여부와 다시 볼 날짜로 정렬한다. 첫 페이지의 20건은 미래 날짜이고 다음 페이지에 기한이 지난 1건이 있는 경우, 그 1건이 맨 위로 오는 웹 테스트를 확인했다. MVP에서는 전체 페이지를 읽으므로 자료가 크게 늘면 서버 정렬·페이지네이션을 다시 설계해야 한다.
- 자정 직전 완료한 나중에 보기 요청을 같은 키로 자정 직후 재시도하면 200 결과가 재생되고, 새 키로는 지난 날짜 422가 나는 서버 회귀 테스트를 확인했다.
- 받은 자료와 나중에 보기의 일괄 작업도 서버 상한인 50건씩 분할한다. 기존 공통 묶음 테스트에서 51건 분할과 실패 묶음부터 같은 요청 키로 재개하는 동작을 확인했다. 이 화면에서 실제 51건을 선택해 브라우저로 전송하는 검증은 하지 않았다.
- `pytest server/tests -q`: 258 passed. `node --test web/scripts/*.test.mjs`: 10 passed. `node --check web/js/views/inbox.js`와 `git diff --check` 통과. 테스트 실행 당시 다른 세션의 AI 분석 기능 미커밋 변경도 작업 트리에 있었다.
