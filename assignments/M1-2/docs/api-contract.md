# API 계약

실제 구현된 API만 적는다. 전체 목록의 기준은 PRD §13이며, PRD에 없는 API는 `PRD 외 추가`로 표시한다. 서버 실행 중에는 Swagger(`/docs`)에서도 확인할 수 있다.

## 공통 요청 규칙

| 헤더 | 필수 | 내용 |
|---|---|---|
| `Authorization` | 보호된 API | `Bearer <Firebase ID 토큰>` (Google 로그인) |
| `X-Data-Mode` | 보호된 API | `personal` 또는 `sample`. 요청에 담긴 모드가 그 요청의 기준이다 |
| `Idempotency-Key` | 변경 요청 | 중복 요청 식별자. 규칙은 T02.02에서 확정 |

판정 순서와 응답 코드:

| 순서 | 조건 | 코드 |
|---|---|---|
| 1 | 토큰 없음·형식 오류·무효·만료 | 401 (`WWW-Authenticate: Bearer`) |
| 2 | 서버의 Firebase 설정 또는 `OWNER_UID` 누락 | 503 — 아무도 통과시키지 않는다 |
| 3 | 인증됐지만 `OWNER_UID`가 아닌 계정 | 403 |
| 4 | `X-Data-Mode` 없음·허용 밖 | 422 |

다른 소유자·모드의 자료를 숨기는 404는 자료 API(T02.02~)에서 적용한다. Firebase ID 토큰은 로그아웃 후에도 최대 1시간 유효하며, MVP는 토큰 폐기를 요구하지 않는다.

## GET /health

인증 없음. 서버 기동과 설정 묶음(`ai`, `firebase`)의 준비 상태만 반환한다. 값은 반환하지 않는다.

## GET /api/me — PRD 외 추가 (T02.01)

로그인·소유자·모드 확인용.

```json
{"owner_id": "<OWNER_UID>", "mode": "personal"}
```

## 로컬 로그인 확인 방법

1. Firebase 콘솔에서 Authentication → Google 로그인을 켜고, 웹 앱을 등록한다.
2. `web/js/config.example.js`를 `web/js/config.js`로 복사해 공개 설정(`apiKey`, `authDomain`, `projectId`)과 API 주소를 채운다.
3. 서버 `.env`에 `FIREBASE_SERVICE_ACCOUNT_JSON`(JSON 문자열)과 `ALLOWED_ORIGINS=http://localhost:5500`을 넣고 서버를 실행한다.
4. `web` 폴더에서 `python -m http.server 5500`으로 정적 서버를 띄우고 `http://localhost:5500/login.html`을 연다. Firebase 승인된 도메인에 `localhost`가 있어야 한다.
5. 첫 로그인 화면의 UID를 `.env`의 `OWNER_UID`에 넣고 서버를 다시 시작한 뒤 `/api/me`가 200인지, 로그아웃 후 401인지 확인한다.
