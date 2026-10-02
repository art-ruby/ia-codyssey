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
- 분석 쓰기는 자료 `version`을 올리지 않는다. 분석 중에도 `PUT`으로 고칠 수 있고, 끝났을 때 내용이 바뀌었으면 결과를 버리고 `awaiting_start` + `analysis_error=input_changed`가 된다. 분석 중에 AI 분석 제외를 켰으면 같은 방식으로 결과를 버리고 `analysis_error=ai_excluded`가 된다(이미 보낸 요청은 사용량에 남긴다).

자료 응답에 더해진 필드:
- `analysis_status`: `link_only` · `awaiting_start` · `analyzing` · `done` · `failed` · `quota_waiting`(T04.03 호출 한도 대기). 분석 전·실패 자료의 내용을 고치면 `awaiting_start`(또는 `link_only`)로 맞춘다.
- `analysis_error`: 오류 종류만(`rate_limited`·`timeout`·`invalid_output`·`ungrounded_output`·`output_truncated`·`missing_ai_settings`·`hermes_tools_enabled`·`provider_*`·`internal_error`·`input_changed`·`ai_excluded`). 본문은 저장하지 않는다. `ai_excluded`는 분석 중에 AI 분석 제외를 켜서 결과를 버린 경우다.
- `analysis_started_at` · `analysis_deadline_at`(시작 + 요청 시간 × 2) · `analysis_finished_at`.
- `analysis_stale`(조회 때 계산): `analyzing`인데 기한이 지났다. 서버 재시작 등으로 작업이 사라졌을 수 있어 '결과 확인 필요'로 표시하고, 사용자가 다시 시작할 때만 호출한다.
- `analysis_outdated`(조회 때 계산): 저장된 AI 결과가 지금 내용 기준이 아니다(완료 후 내용을 고침). 상태는 `done`으로 두고 '다시 분석 필요'로 표시한다.
- `ai_title` · `ai_summary` · `ai_importance` · `ai_importance_reason` · `ai_primary_project_id` · `ai_kind` · `ai_keywords` · `ai_uncertainties` · `ai_recommended_action` · `ai_evidence` · `ai_checked_scope` · `ai_grounding`: AI 제안값(T04.01). 사용자 최종값(`title`·`user_importance`·`primary_project_id`)을 덮어쓰지 않는다.
- 내부 저장 필드(응답에 없음): `analysis_job_id`, `analysis_result_fp`, `ai_content_hash`, `analysis_request_sent`, `analysis_total_tokens`, `analysis_model`(T04.03 사용량용).

## AI 사용량·한도 (T04.03)

**`GET /api/ai/usage`** — PRD 외 추가. 오늘(서울 날짜) AI 요청 사용량.
- 200 `{date, used, limit, remaining, failed_sent, by_kind: {analysis, chat}, total_tokens, resets_at, pending_count, pending_capped, max_output_tokens, timeout_seconds}`.
- `used`·`limit`·`remaining`은 **개인·표본 모드를 합산**한 소유자 전체 값이다(같은 구독을 쓰므로). `pending_count`는 현재 모드의 `quota_waiting` 자료 수이며 100건까지 센다(`pending_capped`).
- `resets_at`은 다음 서울 자정(UTC). 날짜가 바뀌어도 대기 자료를 저절로 분석하지 않는다.
- 금액은 제공하지 않는다(가격 미확인). 화면은 '구독 경로, 금액 미확인'으로 표시한다.

분석 API의 사용량 규칙:
- `POST /api/materials/{id}/analyze`는 AI를 부르기 전에 요청 1회를 원자적으로 예약한다. 동시 요청도 한도를 넘지 않는다.
- 오늘 한도에 도달했으면 **200** `{"status": "quota_waiting", "material"}`이고 자료는 `analysis_status=quota_waiting`(호출 한도 대기)이 된다. AI는 부르지 않는다. 재개는 사용자가 같은 API를 다시 부를 때만 한다.
- 보내기 전에 멈춘 실패(설정 누락·도구 확인 실패 등)는 예약을 돌려준다. 실제로 보낸 요청은 실패·429·시간 초과도 사용량에 남는다(`failed_sent`). 응답은 받았지만 형식·근거 검증에 실패한 경우(`invalid_output`·`ungrounded_output`)도 그 응답의 토큰을 `total_tokens`에 더한다.
- Provider 429(`rate_limited`)는 `failed`가 아니라 `quota_waiting` + `analysis_error=rate_limited`다.
- 재사용(`reused`)·거부(409)·한도 대기는 사용량을 쓰지 않는다. Hermes 도구 확인 호출과 수동 스모크 스크립트는 세지 않는다.

## 오늘·AI 동향 우선순위 (T04.04)

**`GET /api/materials/priority`** — PRD 외 추가. 현재 모드의 활성 자료(휴지통 제외)를 우선순위로 정렬한다.
- 200 `{items, pending, counts: {unreviewed, kept}, scanned, truncated}`. `items`는 최종 중요도가 있는 자료의 정렬 결과, `pending`은 판단 보류 자료(최신 접수 순).
- 최종 중요도 = `user_importance`, 없으면 지금 내용 기준으로 끝난 AI 제안(`analysis_status=done`이고 `analysis_outdated=false`일 때의 `ai_importance`).
- 정렬: 최종 중요도(높음→보통→낮음) → 대응 필요(`needs_action=true`) 우선 → 최신 접수 → ID.
- 각 자료에 `final_importance`, `importance_source`(`user`|`ai`|null), `needs_action`(true|false|null=미확인), `reason`(사용자가 정했으면 저장 이유 우선, 아니면 AI 중요 이유)이 더해진다.
- 계산값이라 Firestore 정렬을 쓰지 않고 **최신 접수부터** 최대 500건을 읽어 서버에서 정렬한다. 넘으면 오래된 자료가 빠지고 `truncated=true`.
- `counts.unreviewed`는 활성·미검토 자료 수, `counts.kept`는 보관 완료(`is_kept`) 수.

AI 출력 계약에 `needs_action`(bool, 필수)이 더해졌다(`PROMPT_VERSION` 2026-10-02.2). 참이면 권장 행동이 있어야 한다. 자료 응답에 `ai_needs_action`이 더해지며, 이전 결과에는 없다(null).

자료 응답의 `analysis_prompt_outdated`(조회 때 계산): 완료된 결과가 이전 분석 기준(`analysis_prompt_version`이 현재 `PROMPT_VERSION`과 다르거나 없음)으로 만들어졌다. 결과는 계속 쓰며(최종 중요도에도 반영), 화면은 '다시 분석 가능'으로 표시한다. 자동 호출은 없고, 사용자가 시작하면 재사용하지 않고 새로 분석한다.

## 보관함 검색 (T05.01)

**`GET /api/materials/search`** — PRD 외 추가. 현재 모드의 보관 완료 자료(`is_kept`: 보관 승인·활성)만 검색한다. 미승인·나중에 보기·휴지통은 제외.
- 쿼리: `q`(200자 이하, 공백으로 나눈 검색어가 모두 들어 있어야 일치, 대소문자 무시·한글 부분 일치), `date_from`·`date_to`(`YYYY-MM-DD`, 접수일 서울 날짜, 양 끝 포함), `kind`(AI 종류), `source_type`(`url`|`text`), `project_id`(주 또는 관련 프로젝트), `limit`(1~50, 기본 20), `cursor`.
- 검색 필드: 제목·설명·본문·저장 이유·메모·URL. AI가 만든 필드는 검색하지 않는다.
- 200 `{items, next_cursor, total_matches, scope}`. `items`는 최신 접수 순이며 각 자료에 `match: {field, snippet}`(검색어가 없으면 null)이 더해진다. `scope`: `{scanned, scan_limit, truncated, kept_scanned, fields}` — 실제로 검색한 범위다. `truncated=true`면 최근 접수 `scan_limit`(1,000)건까지만 검색했다는 뜻이다.
- 422: 날짜 형식·존재하지 않는 날짜, 시작이 끝보다 늦음, `limit` 범위 밖, 허용 밖 `kind`·`source_type`, 다른 검색 조건에서 만든 커서·망가진 커서.
- 저장소 오류는 5xx로 그대로 알린다(결과 0건으로 바꾸지 않는다).

## 관련 자료 (T05.02)

**`GET /api/materials/{id}/related`** — PRD §13. 다른 소유자·모드 자료는 404.
- 200 `{candidates, confirmed, unrelated_count, scope}`.
- `candidates`(제안, 아직 연결되지 않음): 같은 모드의 보관 완료 자료 중 근거가 충분한 것 최대 5건, 근거 점수 → 최신 순. 자기 자신, 같은 URL(비교 키) 자료, 이미 연결했거나 관련 없음으로 판단한 짝은 뺀다. 각 항목 `{material: {id, display_title, url, registered_at, review_status, lifecycle, version}, evidence: [{type: project|keywords|terms, label, values}], score}`.
- 근거가 충분한 조건: (같은 프로젝트 + 공통 단어·핵심어 1개 이상) 또는 공통 AI 핵심어 2개 이상 또는 공통 내용 단어 3개 이상. 근거가 약하면 빈 목록이다. AI는 호출하지 않는다.
- `confirmed`(사용자가 확정한 연결): `{material, state: "linked", available, source_id, target_id, source_version, target_version, evidence, decided_at}`. 상대가 휴지통에 가면 `available=false`.
- `unrelated_count`: 관련 없음으로 기록해 제안에서 뺀 수. `scope`: `{scanned, truncated}`(최신 1,000건 기준).

**`POST /api/reviews/approve`의 `action=link`** — 관련 자료 판단.
- 항목: `{material_id, expected_version, action: "link", link: {target_id, target_version, decision: "link"|"unrelated"|"unlink"}}`. `changes`와 함께 보낼 수 없고 자기 자신을 대상으로 할 수 없다(요청 전체 422). 한 요청에서 같은 자료를 여러 상대와 판단할 수 있다. 같은 짝은 방향과 관계없이 한 번만(A→B와 B→A를 함께 보내면 422).
- 항목 결과: `linked` · `marked_unrelated` · `unlinked` · `conflict`(`side`: source|target|link, `current_version`) · `not_found`(`side`) · `invalid`(`reason`: `trashed` 기준 자료가 휴지통, `target_unavailable` 상대가 보관 상태가 아님, `same_url` 같은 URL은 중복 처리에서, `not_linked` 연결되지 않은 짝의 해제).
- 해제(`unlink`)는 상대가 휴지통에 있어도 할 수 있도록 상대의 상태·버전을 확인하지 않는다.
- 짝마다 기록 하나(`material_links`): 두 자료 ID·당시 버전·근거·상태·시각. 두 자료의 상태·버전 확인과 기록 쓰기는 한 트랜잭션이다. 자료 자체의 `version`은 바뀌지 않는다. 응답에 `linked_count`가 더해졌다.

## 웹 자료 휴지통 (T05.03)

**휴지통 이동** — `POST /api/reviews/approve`의 `action=trash`. 항목 `{material_id, expected_version, action: "trash"}`(수정값·관련 자료 판단과 함께 보낼 수 없음). 활성 자료(미승인 포함)를 `lifecycle=trash`로 바꾸고 `trashed_at`을 기록한다. 검토 상태·승인일은 그대로다. 결과 `trashed`(material) · `conflict` · `not_found` · `invalid`(`trashed`: 이미 휴지통·삭제 중). 응답에 `trashed_count`.

**`GET /api/trash`** — PRD §13. 현재 모드의 휴지통 자료와 영구 삭제가 끝나지 않은 자료(`lifecycle=deleting`)를 휴지통에 넣은 시각의 최신순으로. 200 `{items, truncated}`(최대 500건). 각 자료에 `deletion_failed_step`.

**`POST /api/trash/{id}/restore`** — PRD §13. `{expected_version}`. `lifecycle=active`, `trashed_at=null`. 검토 상태·승인일은 그대로(미승인 자료는 미승인으로). 409: 휴지통에 없음(`not_in_trash`), 삭제 중(`deleting`), 버전 충돌. 404: 없거나 다른 모드.

**`DELETE /api/trash/{id}?expected_version=N&confirm=permanent`** — PRD §13. 휴지통·삭제 중 자료만. `confirm=permanent`가 없거나 다르면 422.
- ① 자료를 `deleting`으로 바꿔 모든 화면에서 숨기고 작업 ID를 남긴다. ② 접수 기록 → 같은 URL 예약 → 관련 자료 기록(건수 제한 없이 모두) → 중복 요청 기록 정리(응답 본문에 이 자료 ID가 있는 기록의 본문을 `{"deleted": true}`로 비움, 기록·지문은 유지) → 마지막으로 자료 문서 삭제와 감사 완료 기록을 한 트랜잭션으로.
- 200 `{"status": "deleted", "job_id"}`. 일부 단계가 실패하면 200 `{"status": "partial", "job_id", "failed_step", "steps_done"}`이고 자료는 `deleting`으로 남는다. 같은 API(새 키, 현재 버전)를 다시 부르면 남은 단계부터 이어서 한다.
- 감사 기록 `audit_events`: `{action: "permanent_delete", job_id, status: running|done|partial, steps_done, failed_step, started_at, finished_at}`. 자료 ID·본문은 남기지 않는다.
- 삭제 중인 자료는 `PUT /api/materials/{id}` 409(`deleting`), 복원 409, 분석 409(`trashed`).
- 색인: `materials`의 `owner_id·mode·lifecycle·created_at DESC`(2026-10-02 배포).

## 숫자 기록 (T06.01)

모두 인증·`X-Data-Mode` 필요, 변경 요청은 `Idempotency-Key` 필요. `data`에는 수기(개인 모드)·표본(표본 모드) 기록만 있다. 실제 지표는 저장하지 않는다(요약에서 계산, T06.02).

| API | 요청 | 응답·규칙 |
|---|---|---|
| `POST /api/data` | `{date, metric_type, value, memo?}` | 201 기록. `origin`은 모드에서 정한다(개인 `manual`, 표본 `sample`). 보내면 422 |
| `GET /api/data?metric_type=&date_from=&date_to=&limit=50&cursor=` | — | `{items, next_cursor, total, truncated}`. 날짜 최신순(같은 날짜는 최근 생성 먼저). `limit` 1~100. 다른 조건의 커서·망가진 커서 422 |
| `GET /api/data/{id}` | — | 기록. 다른 소유자·모드 404 |
| `PUT /api/data/{id}` | `{expected_version, date?, metric_type?, value?, memo?}` | 보낸 필드만 수정. 바꿀 필드가 하나도 없으면 422. 날짜·지표·값은 null 불가, 메모 null은 비움. 버전 불일치 409(`current_version`) |
| `DELETE /api/data/{id}?expected_version=N` | — | `{deleted: true, id}`. 버전 확인과 삭제는 한 트랜잭션. 버전 없으면 422, 불일치 409 |

- 기록: `{id, date, metric_type, value, memo, origin, mode, version, created_at, updated_at}`.
- `date`: 실제 있는 `YYYY-MM-DD`, 2000-01-01~2100-12-31. `metric_type`: `received_count`|`kept_count`. `value`: 0~1,000,000 정수(소수·`2.0`·문자열·참거짓 422). `memo`: 500자 이하.
- 같은 날짜·지표에 여러 기록을 둘 수 있다. 요약의 일별 값은 합계다(T06.02).
- `GET /api/data/summary`(T06.02)는 `/{id}`보다 먼저 등록한다.

## 숫자 요약 (T06.02)

**`GET /api/data/summary?source=&metric_type=kept_count&start_date=&end_date=`** — PRD §11.2. `/api/data/{id}`보다 먼저 등록돼 있다.
- `source`: 기본은 개인 모드 `actual`, 표본 모드 `sample`. 허용은 개인 `actual`·`manual`, 표본 `sample`·`actual`. 그 밖은 422(`source_not_allowed`).
- `metric_type`: `kept_count`(기본) · `received_count` · `all`(지표별로 나눈 `{source, mode, results: [...]}`).
- `actual`: 접수 수 = 접수 기록(휴지통 자료 포함, 영구 삭제 자료 제외)을 서울 날짜로, 보관 수 = 현재 보관 완료·활성 자료를 승인일(서울)로. `manual`·`sample`: `data`의 같은 출처 기록을 날짜별 합계로.
- 200 `{metric_type, source, mode, label, period: {start, end}|null, days, daily: [{date, value}], total, average, min, max, trend}`.
  - 기간은 관측 시작(첫 값이 있는 날)부터 기준일까지. `start_date`가 관측 시작보다 이르면 관측 시작으로 맞춘다. 기록 없는 날은 0.
  - 값이 전혀 없으면 `total=0`, `period`·`average`·`min`·`max`·`trend`는 null, `daily=[]`.
  - `trend`: `{status: increase|decrease|flat|insufficient|new|both_zero, recent_average, previous_average, change_rate, reference_date}`. 기준일은 개인 모드 오늘(서울), 표본 모드 그 계열의 최신 날짜. 최근 7일 vs 이전 7일, +10% 이상 증가·-10% 이하 감소. 관측 14일 미만은 `insufficient`, 이전 0건은 `new` 또는 `both_zero`(백분율 없음).
- `label`: 지표·출처 조합의 화면 이름. `kept_count`: actual '현재 보관 자료 수'·manual '사용자 입력 보관 기록'·sample '가상 보관 기록'. `received_count`: actual '실제 접수 건수'·manual '사용자 입력 접수 기록'·sample '가상 접수 기록'(PRD §11.3: 표본 숫자를 실제 수로 오해하지 않게 '가상').
- 날짜 형식·범위 오류, 시작이 끝보다 늦음, 허용 밖 지표는 422.
