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
2. `.env`에 공개 웹 설정(`API_BASE_URL`, `FIREBASE_WEB_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`)을 넣고 `node web/scripts/build-config.mjs`로 `web/js/config.js`를 생성한다.
3. 서버 `.env`에 `FIREBASE_SERVICE_ACCOUNT_JSON`(JSON 문자열)과 `ALLOWED_ORIGINS=http://localhost:5500`을 넣고 서버를 실행한다.
4. `web` 폴더에서 `python -m http.server 5500 --bind ::`로 정적 서버를 띄우고 `http://localhost:5500/`(앱) 또는 `/login.html`(인증 점검용)을 연다. Firebase 승인된 도메인에 `localhost`가 있어야 한다.
5. 첫 로그인 화면의 UID를 `.env`의 `OWNER_UID`에 넣고 서버를 다시 시작한 뒤 `/api/me`가 200인지, 로그아웃 후 401인지 확인한다.

## 프로젝트 API (T02.04, PRD §13)

모두 인증·`X-Data-Mode` 필요. 변경 요청은 `Idempotency-Key` 필요. 프로젝트는 소유자·모드별로 따로 관리된다.

| API | 요청 | 응답·규칙 |
|---|---|---|
| `GET /api/projects?include_inactive=false` | — | `{"items": [프로젝트]}`. 기본은 활성만 |
| `POST /api/projects` | `{"name": 1~50자, "description": 0~500자}` | 201 프로젝트. 같은 이름(대소문자·공백 무시, 비활성 포함)은 **409** `reason: duplicate_name`. 100개 초과 422 |
| `PUT /api/projects/{id}` | `{"expected_version", "name"?, "description"?, "active"?}` | 200 프로젝트. 버전 불일치 409, 다른 소유자·모드 404 |

프로젝트: `{id, name, description, active, version, created_at, updated_at}`. 삭제 API는 없고 `active: false`로 비활성 처리한다. 이름 중복 검사와 생성·수정은 소유자·모드별로 원자적으로 처리한다. 기본 프로젝트를 비활성화하면 해당 모드 설정의 `default_project_id`를 같은 변경에서 비우고 설정 버전을 올린다. 자료는 주 프로젝트 `primary_project_id`와 관련 프로젝트 `related_project_ids[]`로 연결한다(Open Decision 1, T03에서 사용).

## 설정 API — PRD 외 추가 (T02.04)

| API | 요청 | 응답·규칙 |
|---|---|---|
| `GET /api/settings` | — | `{interests[], activities[], default_project_id, version, saved}`. 저장 전에는 `saved: false`, `version: 0`과 모드별 기본값(개인: PRD §1의 관심·활동 분야, 표본: 빈 값) |
| `PUT /api/settings` | `{"expected_version", "interests"[], "activities"[], "default_project_id"?}` | 첫 저장은 `expected_version: 0`. 항목은 한 개 1~50자·최대 20개, 앞뒤 공백 제거·중복 제거. 기본 프로젝트는 같은 모드의 활성 프로젝트여야 하며 아니면 422. 버전 불일치 409 |

설정은 소유자·모드마다 문서 하나다. 현재 자료 모드는 서버에 저장하지 않는다(요청마다 `X-Data-Mode`, 마지막 선택은 브라우저가 기억).

## 자료 API (T03.01, PRD §13)

모두 인증·`X-Data-Mode` 필요. 변경 요청은 `Idempotency-Key` 필요.

| API | 요청 | 응답·규칙 |
|---|---|---|
| `POST /api/materials` | `{url?, title?, description?, body?, save_reason?, memo?, primary_project_id?, related_project_ids?}` | 201 자료. URL 또는 제목·설명·본문 중 하나 이상 필요(저장 이유·메모만은 422). URL은 http(s)·호스트 필수. 길이: 제목 200·설명/저장 이유/메모 2,000·본문 20,000자, 넘으면 잘라 저장하지 않고 422(`detail`에 한도). 접수 기록(`intake_records`)이 같은 ID로 원자적으로 함께 생성된다. AI는 호출하지 않는다 |
| `GET /api/materials?limit=20&cursor=` | — | `{items, next_cursor}`, **최신 접수 순** |
| `GET /api/materials/{id}` | — | 자료. 다른 소유자·모드 404 |
| `PUT /api/materials/{id}` | `{expected_version, title?, description?, body?, save_reason?, memo?, primary_project_id?, related_project_ids?}` | 보낸 필드만 수정(null은 비움). `url`은 고칠 수 없다(보내면 422). 내용이 모두 비게 되면 422. 버전 불일치 409 |

- 응답 자료: `{id, source_type(url|text), url, title, description, body, save_reason, memo, primary_project_id, related_project_ids, review_status, analysis_status, copy_status, lifecycle, ai_excluded, registered_at, storage_approved_at, trashed_at, version, created_at, updated_at, display_title, title_source}`.
- `analysis_status`: URL만 있으면 `link_only`(링크만 저장됨·본문 미확인), 제목·설명·본문이 있으면 `awaiting_start`(사용자가 분석을 시작하기 전).
- `display_title`·`title_source`: 제목이 없으면 화면용으로 도메인(`url`) 또는 설명·본문 앞부분(`text`)을 보여주며 저장하지 않는다. 실제 페이지 제목이라고 주장하지 않는다.
- 프로젝트 참조는 같은 모드의 활성 프로젝트만 허용(422).
- 요청 형식 오류(422)의 `detail`은 한국어 안내 문장이고, `errors`에는 위치·종류만 있으며 입력값은 되돌려 보내지 않는다.

## 같은 URL 처리 (T03.02)

`POST /api/materials`에 같은 URL(비교 키: 스킴·호스트 소문자, 기본 포트 제거, IPv6 대괄호 유지, 경로·쿼리 보존)의 자료가 같은 소유자·모드에 있으면:

```json
409 {"detail": "같은 URL의 자료가 이미 있습니다…", "reason": "duplicate_url",
     "existing": [{"id", "display_title", "title_source", "registered_at", "review_status", "analysis_status", "lifecycle", "version"}]}
```

사용자 선택 후 다시 보내는 요청(새 `Idempotency-Key`):

| 선택 | 요청에 더할 값 | 결과 |
|---|---|---|
| 별도 저장 | `"duplicate_action": "save_separately"` | 같은 소유자·모드에 같은 URL의 기존 자료가 있을 때만 201 새 자료(+접수 기록). 기존 자료가 없으면 쓰기 없이 422 |
| 메모 추가 | `"duplicate_action": "add_memo", "target_id", "target_version", "memo"` | 200 기존 자료(메모만 덧붙음). 대상 없음·다른 URL 422, 휴지통 409 `trashed`, 버전 불일치 409, 2,000자 초과 422 |

`POST /api/materials`의 응답 상태는 결과에 따라 201(새 자료) 또는 200(메모 추가)이며, 같은 키로 다시 보내면 처음 상태와 본문을 그대로 돌려준다. URL 포트가 숫자가 아니거나 0~65535 밖이면 422다. 쓰기 전에 거부된 요청(404·409·422)은 같은 키로 다시 보낼 수 있다.

## 검토·승인 (T03.03)

자료에 `user_importance`(`high|medium|low|null`, null=판단 보류), `review_requested`(bool), `review_requested_at`이 더해졌다. `user_importance`는 접수·`PUT /api/materials/{id}`에서도 고칠 수 있다.

**`GET /api/materials?view=`** — PRD 외 추가. `all`(기본, 전체 최신순) · `inbox`(활성·미검토·검토 요청 안 함) · `review`(활성·미검토·검토 요청함). 다른 값은 422. 커서는 같은 view로만 이어 쓴다.

**`POST /api/reviews/request`** — PRD 외 추가. `{"items": [{"material_id", "expected_version"}], "requested": true|false}`. 결과 `{"results": [...], "updated_count"}`, 항목 상태는 `updated`(material 포함) · `unchanged`(이미 그 상태, 시각 유지) · `conflict`(current_version) · `not_found` · `invalid`(reason `trashed`|`approved`).

**`POST /api/reviews/approve`** — PRD §13.
```json
{"items": [{"material_id": "…", "expected_version": 2, "action": "keep",
            "changes": {"title": "…", "user_importance": "high", "primary_project_id": "…", "related_project_ids": []}}]}
```
- `changes`는 선택이며 보낸 필드만 바꾼다(null은 비움). 다른 필드를 보내면 422.
- 요청 전체 422: 항목 0개, 50건 초과, 같은 `material_id` 중복, `action`이 `link`·`trash`(Phase 05에서 같은 형식으로 지원)이거나 그 밖의 값, 형식 오류. 쓰기 전 거부이므로 같은 키로 다시 보낼 수 있다.
- 그 밖에는 **200** `{"results": [...], "approved_count"}`. 항목 순서대로 결과를 준다.

| status | 뜻 |
|---|---|
| `approved` | `review_status=approved`, `storage_approved_at` 기록, 수정값 반영. `material` 포함 |
| `already_approved` | 수정값 없는 새 요청의 자료가 이미 승인됨. 버전과 관계없이 쓰지 않는다. `current_version`, `material` 포함 |
| `conflict` | 버전 불일치 또는 이미 승인된 자료에 새 수정값을 보냄. 쓰지 않음. `current_version` 포함 |
| `not_found` | 없거나 다른 소유자·모드의 자료 |
| `invalid` | `reason`: `trashed`(휴지통) · `project`(없거나 비활성 프로젝트) · `no_content`(제목을 비워 내용이 없어짐) |

- 자료 한 건은 버전 확인을 포함한 쓰기 한 번이다. 묶음 전체를 한꺼번에 성공·실패시키지 않는다.
- 같은 `Idempotency-Key`로 다시 보내면 처음 응답 그대로다. 새 키로 수정값 없이 다시 보내면 `already_approved`이며 승인 시각은 바뀌지 않는다. 새 키에 수정값을 담아 이미 승인된 자료에 보내면 `conflict`로 알려 수정값을 조용히 버리지 않는다. 화면은 최신 자료와 수정값을 함께 보여주고, 사용자가 확인한 뒤 기존 `PUT /api/materials/{id}`로 수정값을 저장한다.
- 웹 화면은 선택 항목을 최대 50건씩 나눠 순서대로 요청한다. 각 묶음은 별도 `Idempotency-Key`를 사용한다. 중간 전송이 실패하면 남은 묶음을 멈추고 성공·충돌 항목의 상태를 유지하며, 재시도 시 실패한 묶음에 같은 키를 사용한다. 받은 자료로 되돌리기도 같은 상한을 따른다.
- **보관 완료** = `review_status=approved` + `copy_status=not_applicable` + `lifecycle=active`. 웹 자료는 승인과 동시에 보관 완료다(PRD §9.1).

## 나중에 보기·AI 분석 제외 (T03.04)

자료에 `revisit_on`(`YYYY-MM-DD` 또는 null)과 계산 값 `revisit_due`(bool, 저장하지 않음)가 더해졌다. `ai_excluded`는 항상 bool로 응답한다.

**`GET /api/materials?view=later`** — 활성·나중에 보기(`review_status=later`) 자료. 최신 접수순. `revisit_due`는 서울 기준 오늘 ≥ `revisit_on`이면 true(날짜 없으면 false).

**`POST /api/reviews/later`** — PRD 외 추가. `{"items": [{"material_id", "expected_version"}], "later": true|false, "revisit_on": "YYYY-MM-DD"|null}`.
- 요청 전체 422: 항목 0개·50건 초과·중복, 오늘(서울)보다 이른 날짜, 형식이 틀린 날짜, `later=false`에 날짜를 보냄.
- 날짜 경과 판정은 같은 `Idempotency-Key`의 완료 결과를 재생한 뒤 새 요청에만 적용한다. 따라서 자정 전 완료한 요청을 자정 후 같은 키·본문으로 재시도하면 원래 결과를 돌려주고, 새 키로 과거 날짜를 보내면 422다.
- 200 `{"results": [...], "updated_count"}`. 항목 상태: `updated`(material 포함) · `unchanged`(이미 같은 상태·같은 날짜) · `conflict`(current_version) · `not_found` · `invalid`(reason `trashed`|`approved`).
- `later=true`: `review_status=later`, `revisit_on` 기록, 검토 요청 해제. `later=false`: 미검토로 되돌리고 `revisit_on=null`.
- 나중에 보기 자료를 `POST /api/reviews/request`로 옮기면 미검토·검토 요청으로 바뀌고 날짜는 지운다. `POST /api/reviews/approve`로 바로 승인할 수 있으며 승인하면 날짜를 지운다.

**AI 분석 제외** — `ai_excluded`를 `POST /api/materials`·`PUT /api/materials/{id}`로 바꾼다(null은 바꾸지 않음). `analysis_status`는 바뀌지 않는다. 분석(T04)·채팅(T07)은 보내기 직전에 `ai_allowed`/`chat_eligible`로 확인한다.

| 판정 | 조건 |
|---|---|
| 보관 완료 `is_kept` | `review_status=approved` + `copy_status=not_applicable` + `lifecycle=active` |
| AI 전송 가능 `ai_allowed` | `ai_excluded`가 아님 |
| 채팅 근거 `chat_eligible` | `is_kept` + `ai_allowed`(소유자·모드는 저장소가 보장) |

## 자료 분석 (T04.02)

**`POST /api/materials/{id}/analyze`** — PRD §13. `{"expected_version": n}`, `Idempotency-Key` 필요.
- **202** `{"status": "accepted", "material"}`: 접수만 의미한다. `analysis_status=analyzing`이 되고 서버 백그라운드 작업이 AI를 1회 호출한다. 결과는 `GET /api/materials/{id}`로 조회한다(화면은 3초 간격).
- **200** `{"status": "reused", "material"}`: 완료된 결과와 입력 지문(보낼 내용 + 활성 프로젝트 `id`·`name` + 프롬프트 버전)이 같으면 새 키여도 AI를 부르지 않는다. 모델명은 지문에 넣지 않는다.
- **409**: 버전 불일치(`current_version`), `reason`이 `analysis_in_progress`(분석 중·기한 전) · `trashed` · `ai_excluded` · `no_content`(URL만 있는 자료). 모두 AI 호출 없음.
- 같은 키 재전송은 처음 응답을 그대로 주며 작업을 다시 만들지 않는다.
- 분석 쓰기는 자료 `version`을 올리지 않는다. 분석 중에도 `PUT`으로 고칠 수 있고, 끝났을 때 내용이 바뀌었으면 결과를 버리고 `awaiting_start` + `analysis_error=input_changed`가 된다.

자료 응답에 더해진 필드:
- `analysis_status`: `link_only` · `awaiting_start` · `analyzing` · `done` · `failed`. 분석 전·실패 자료의 내용을 고치면 `awaiting_start`(또는 `link_only`)로 맞춘다.
- `analysis_error`: 오류 종류만(`rate_limited`·`timeout`·`invalid_output`·`ungrounded_output`·`output_truncated`·`missing_ai_settings`·`hermes_tools_enabled`·`provider_*`·`internal_error`·`input_changed`). 본문은 저장하지 않는다.
- `analysis_started_at` · `analysis_deadline_at`(시작 + 요청 시간 × 2) · `analysis_finished_at`.
- `analysis_stale`(조회 때 계산): `analyzing`인데 기한이 지났다. 서버 재시작 등으로 작업이 사라졌을 수 있어 '결과 확인 필요'로 표시하고, 사용자가 다시 시작할 때만 호출한다.
- `analysis_outdated`(조회 때 계산): 저장된 AI 결과가 지금 내용 기준이 아니다(완료 후 내용을 고침). 상태는 `done`으로 두고 '다시 분석 필요'로 표시한다.
- `ai_title` · `ai_summary` · `ai_importance` · `ai_importance_reason` · `ai_primary_project_id` · `ai_kind` · `ai_keywords` · `ai_uncertainties` · `ai_recommended_action` · `ai_evidence` · `ai_checked_scope` · `ai_grounding`: AI 제안값(T04.01). 사용자 최종값(`title`·`user_importance`·`primary_project_id`)을 덮어쓰지 않는다.
- 내부 저장 필드(응답에 없음): `analysis_job_id`, `analysis_result_fp`, `ai_content_hash`, `analysis_request_sent`, `analysis_total_tokens`, `analysis_model`(T04.03 사용량용).
