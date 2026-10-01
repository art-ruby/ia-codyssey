# Phase 01 검증 기록

기준일: 2026-10-01. 실제 호출 결과만 완료로 기록한다. API 키와 사용자 자료 원문은 이 문서나 Git에 넣지 않는다.

## T01.01·T01.02

- 산출물 커밋: `424961b8` (`feat(M1-2): establish Phase 01 server baseline`).
- Python 3.11.9 환경에서 `python -m pytest server/tests -q`: **7 passed**.
- 키를 비운 상태로 Uvicorn을 실행해 `/health` HTTP 200(`ai`, `firebase` 모두 `missing`)과 `/docs` HTTP 200을 확인했다.
- Git 제외 확인: `.env`, `.env.codyssey`, `.venv`, `.pytest_cache`.

## T01.03 — Codyssey GPT 텍스트 호출

**상태: 통과. A25 통과.** 2026-10-01 로컬 smoke 호출이 Codyssey 프록시에서 성공했다. 요청·응답 모델은 `gpt-5-mini`였고, OpenAI SDK `3.22.1`에서 `choices[0].message.content`가 비어 있지 않은 텍스트로 반환됐으며 `finish_reason=stop`, 종료 코드 `0`을 확인했다.

2026-10-01 M1-1 재확인: `submission/src/config.py`의 프록시 주소는 `https://copa.codyssey.kr/v1`이고 기존 번역 모델은 `gemini-3-flash`다. `submission/src/translate.py`는 Bearer 인증으로 `/chat/completions`를 호출한다. 확인한 M1-1 `.env`에는 비어 있는 YouTube 키만 있으며 `OPENAI_API_KEY`는 없다. 인증 없이 `GET /v1/models`를 요청하면 HTTP 401이므로 GPT 모델명도 추측하지 않는다.

`server/scripts/smoke_ai.py`는 `M1-2/.env.codyssey`만 읽고 프록시 주소가 `https://copa.codyssey.kr/v1`인지 확인한다. 검증에 사용한 파일은 Git에서 제외되어 있으며 API 키 값은 이 문서와 저장소에 기록하지 않았다. `AI_PROVIDER_MODEL`은 `gpt-5-mini`로 설정했다.

Phase 01 연결 검증을 보충하면서 서버가 읽는 `.env`를 같은 Codyssey 설정으로 전환했고, 기존 Hermes 설정은 Git 제외 파일 `.env.hermes`로 보존했다. `AI_MAX_OUTPUT_TOKENS=1500`, `AI_TIMEOUT_SECONDS=60`을 적용했다. `max_completion_tokens=1500`을 지정한 1회 호출도 성공했으며 응답 모델 `gpt-5-mini`, `finish_reason=stop`, `completion_tokens=74`, `prompt_tokens=14`, `total_tokens=88`을 확인했다. 이 사용량은 검증용 단문 요청의 실측값이다.

```powershell
.\.venv\Scripts\python.exe server/scripts/smoke_ai.py --list-models
.\.venv\Scripts\python.exe server/scripts/smoke_ai.py
```

성공 결과는 요청 모델명, 응답 모델명, OpenAI SDK 버전, `choices[0].message.content` 비어 있지 않음, 종료 이유와 함께 위에 기록했다. 키가 비어 있을 때 스크립트는 호출 전에 종료 코드 1로 중단됐고, Hermes 설정 파일을 명시해도 주소 검사에서 호출 전에 중단됐다. 이번 검증 범위는 텍스트 호출이며 이미지 입력 지원, 비용, 한도는 아직 확인하지 않았다.

코드 리뷰에서 발견한 응답 종료 판정도 보완했다. 이제 본문이 있어도 `finish_reason`이 `stop`이 아니면 실패로 처리한다. `stop`, `length`, `content_filter`를 모의 응답으로 검증했고, 수정한 스크립트의 실제 Codyssey 재호출도 `finish_reason=stop`, 종료 코드 `0`으로 끝났다.

MVP 서버 실행 경로는 PRD §12에 따라 Codyssey 프록시를 사용한다. 서버용 `.env`는 Codyssey 설정이며, 별도 Hermes 설정은 `.env.hermes`로 Git에서 제외해 보관한다. 실제 Adapter 구현에서는 `Settings.ai_max_output_tokens`와 `Settings.ai_timeout_seconds`를 사용해야 한다.

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
