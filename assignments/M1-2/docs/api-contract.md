# API 계약

실제 구현된 API만 적는다. 전체 목록의 기준은 PRD §13이며, PRD에 없는 API는 `PRD 외 추가`로 표시한다. 서버 실행 중에는 Swagger(`/docs`)에서도 확인할 수 있다.

## 공통 요청 규칙

| 헤더 | 필수 | 내용 |
|---|---|---|
| `Authorization` | 보호된 API | `Bearer <Firebase ID 토큰>` (Google 로그인) |
| `X-Data-Mode` | 보호된 API | `personal` 또는 `sample`. 요청에 담긴 모드가 그 요청의 기준이다 |
| `Idempotency-Key` | 변경 요청 | 중복 요청 식별자(1~200자). 아래 "중복 요청" 규칙 |

판정 순서와 응답 코드:

| 순서 | 조건 | 코드 |
|---|---|---|
| 1 | 토큰 없음·형식 오류·무효·만료 | 401 (`WWW-Authenticate: Bearer`) |
| 2 | 서버의 Firebase 설정 또는 `OWNER_UID` 누락, 검증용 공개 인증서 조회 실패 | 503 — 아무도 통과시키지 않으며 내부 오류 내용은 응답에 넣지 않는다 |
| 3 | 인증됐지만 `OWNER_UID`가 아닌 계정 | 403 |
| 4 | `X-Data-Mode` 없음·허용 밖 | 422 |

Firebase ID 토큰은 로그아웃 후에도 최대 1시간 유효하며, MVP는 토큰 폐기를 요구하지 않는다.

## 저장소 규칙 (T02.02, `server/app/core/firestore.py`)

| 상황 | 결과 |
|---|---|
| 없거나 다른 소유자·다른 모드의 문서, 형식이 틀린 문서 ID(빈 값·`/` 포함 등) 조회·수정·삭제 | **404** `찾을 수 없습니다` (존재 여부를 드러내지 않음) |
| 수정 요청의 `expected_version`이 현재 버전과 다름 | **409**, 응답에 `current_version` |
| 페이지 커서 해석 불가 | **422** |
| 서버의 Firestore 설정 누락 | **503** |

- 최상위 컬렉션 `materials`, `intake_records`, `settings`, `projects`, `data`, `conversations`, `idempotency`. 문서마다 `owner_id`·`mode`·`version`·`created_at`·`updated_at`(UTC ISO-8601)을 서버가 채우며, 요청 본문의 같은 이름 값은 무시한다.
- 목록은 `created_at`·문서 ID 순서이며 한 페이지 최대 100건. 다음 페이지는 응답의 불투명 커서로 요청한다.
- 브라우저의 Firestore 직접 읽기·쓰기는 보안 규칙(`firestore.rules`, `allow read, write: if false`)으로 거부된다. 모든 접근은 서버를 거친다.

## 중복 요청 (T02.02, `server/app/core/requests.py`)

| 상황 | 결과 |
|---|---|
| 변경 요청에 `Idempotency-Key` 없음·빈 값·200자 초과 | **422** |
| 같은 키·같은 내용(모드·메서드·경로·본문) | 처음 응답을 그대로 반환. 작업은 한 번만 실행 |
| 같은 키·다른 내용 | **409** `reason: different_request` |
| 같은 키의 첫 요청이 처리 중 | **409** `reason: in_progress` |

- 키는 소유자 단위이며 기록은 Firestore `idempotency`에 저장되어 서버를 다시 시작해도 유지된다. 정상 완료된 기록은 완료 후 1일이 지나면 새 요청으로 본다.
- 작업 중 오류가 나거나 서버가 멈추면 변경 적용 여부가 불확실하므로 `processing` 기록을 유지하고 같은 키에 409를 반환한다. 이 기록은 자동 만료되지 않는다. 상태를 확인한 뒤 새 키로 다시 요청하거나 관리자가 기록을 직접 해소해야 한다.
- 입력 검증 등 변경 전에 확인할 수 있는 오류는 중복 요청 키를 차지하기 전에 처리한다.
- 만료 확인과 새 기록 차지는 한 트랜잭션에서 처리해, 만료된 키로 동시에 들어온 요청도 한 번만 실행된다.
- 모든 응답에 `X-Request-ID`가 붙고, 서버 로그에는 메서드·경로 템플릿·상태·소요 시간·요청 ID만 남는다.

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
