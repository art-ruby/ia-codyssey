# AI Secretary — Phase·Task 실행 목록

- [x] **Phase 01. 개발 기준과 AI 연결 검증 — MVP**
  - [x] **T01.01** 최신 PRD·작업 경로·미결정 사항 확인
  - [x] **T01.02** Python 환경·환경변수·프로젝트 기본 실행 구성
  - [x] **T01.03** Codyssey 프록시 GPT 텍스트 호출 검증
  - [x] **T01.04** Hermes 로컬 API·도구 제한·GPT 텍스트 호출 검증
- [x] **Phase 02. 인증·데이터 기반·웹 공통 화면 — MVP**
  - [x] **T02.01** 단일 소유자 로그인과 서버 인증
  - [x] **T02.02** Firestore 저장 구조·버전·중복 요청 처리
  - [x] **T02.03** 10개 메뉴와 모바일 공통 화면
  - [x] **T02.04** 프로젝트·관심 분야·자료 모드 설정
- [ ] **Phase 03. URL·텍스트 접수와 보관 승인 — MVP**
  - [x] **T03.01** URL·텍스트 입력·저장·상세 수정
  - [x] **T03.02** 동일 URL 확인과 세 가지 선택
  - [x] **T03.03** 받은 자료·일괄 검토·보관 승인
  - [x] **T03.04** 나중에 보기·분석 제외·승인 상태 검증
- [x] **Phase 04. AI 분석과 개인 중요도 — MVP**
  - [x] **T04.01** AI Adapter와 구조화 분석 결과
  - [x] **T04.02** 사용자 시작 분석·상태 조회·재시도
  - [x] **T04.03** AI 사용량·한도·전송 범위 표시
  - [x] **T04.04** 오늘·AI 동향·중요도 수정 화면
- [x] **Phase 05. 보관함·관련 자료·웹 휴지통 — MVP**
  - [x] **T05.01** 보관함 검색·필터·페이지네이션
  - [x] **T05.02** 관련 자료 제안·연결·해제
  - [x] **T05.03** 웹 자료 휴지통 이동·복원·영구 삭제
  - [x] **T05.04** 검색·채팅에 전달할 자료의 공통 필터
- [x] **Phase 06. 숫자 기록·요약·표본 데이터 — MVP**
  - [x] **T06.01** 숫자 기록 CRUD와 입력 검증
  - [x] **T06.02** 실제·수기·표본 Summary와 추세 계산
  - [x] **T06.03** 숫자 표본 100건 이상과 채팅 평가 자료
  - [x] **T06.04** 활동 기록·요약 화면과 변경 반영
- [ ] **Phase 07. 자료 기반 채팅과 대화 기록 — MVP**
  - [x] **T07.01** 질문 검색·자료 문맥·숫자 요약 구성
  - [x] **T07.02** 근거 답변·출처 검증·실패 구분
  - [x] **T07.03** 대화 자동 저장·불러오기·삭제
  - [x] **T07.04** 채팅 화면과 검색 품질 평가
- [ ] **Phase 08. MVP 통합 검증과 배포 — MVP 완료 지점**
  - [ ] **T08.01** MVP 인수 기준과 보안·실패 흐름 검증
  - [ ] **T08.02** Render API·Vercel 웹 배포
  - [ ] **T08.03** 실제 배포 환경과 모바일 시연 검증
  - [ ] **T08.04** README·제출 화면·MVP 완료 기록
- [ ] **Phase 09. Windows 연결과 파일 분석 — 확장 단계**
  - [ ] **T09.01** 장치 연결·인증·허용 폴더 등록
  - [ ] **T09.02** 수동 폴더 확인·파일 식별·상태 보고
  - [ ] **T09.03** PDF·Office·텍스트·설치/압축 형식 처리
  - [ ] **T09.04** 이미지·스캔 PDF와 OCR 대체 경로 검증
  - [ ] **T09.05** 스크린샷·Downloads 분류와 검토 화면
- [ ] **Phase 10. 승인된 파일 정리와 연결 삭제 — 확장 단계 완료 지점**
  - [ ] **T10.01** 작업 승인·영속 큐·실행 임대·취소
  - [ ] **T10.02** 이름 변경·이동·새 폴더·되돌리기
  - [ ] **T10.03** 승인 원본 사본 보관과 인증 다운로드
  - [ ] **T10.04** Windows 휴지통과 클라우드 연결 삭제
  - [ ] **T10.05** 부분 실패·재시작·복원·영구 삭제
  - [ ] **T10.06** 확장 단계 인수 검증·설치 안내·완료 기록

---

## 1. 문서 기준과 사용 방법

- 작성일: 2026-10-01.
- 기준: [prd.md](prd.md) **v1.10**, 기준 커밋 `c324ede9`.
- 현재 작업 폴더: `C:\ia-codyssey-m1-2\assignments\M1-2`, Git 브랜치 `m1-2`.
- 저장소 안의 기준 경로: `assignments/M1-2/`. 다른 체크아웃에서 작업할 때도 이 상대 경로를 사용한다.
- 확인된 현재 산출물: PRD, 사용자 시나리오, 단일 HTML 목업, README, `.env.example`, `.gitignore`. 서비스 서버·웹 구현과 실제 배포는 아직 없다.
- `C:\ia-codyssey\assignments\M1-2\prd.md`는 확인 시 v1.4였다. 다음 세션에서 두 경로를 혼용하거나 오래된 PRD로 최신 문서를 덮어쓰지 않는다.
- 목표: Phase 01~08로 URL·텍스트 기반 MVP와 과제 제출을 완료하고, Phase 09~10으로 PC 파일 정리 기능을 확장한다.
- 구조: 바닐라 웹 → FastAPI → Firestore 및 AI Adapter. 확장 단계에서 Windows 연결 프로그램과 비공개 원본 저장소를 연결한다.
- 기술: Python 3.10+, FastAPI, uvicorn, firebase-admin, openai, python-dotenv, Pydantic, 바닐라 HTML·CSS·JavaScript. 웹은 Vercel, 서버는 Render를 사용한다.

**실행 안내:** 다음 세션은 이 문서와 PRD를 함께 읽고 `executing-plans` 스킬로 선택한 Task를 진행한다. 이 문서는 실행 계획이며, 체크박스가 비어 있는 기능은 구현되거나 검증된 것으로 간주하지 않는다.

### 소통과 체크 규칙

1. 대화에서는 `T03.02 진행`, `Phase 05 검토`, `T07.01부터 재개`처럼 ID를 사용한다. Task 번호는 삭제하거나 재사용하지 않는다.
2. **상단 체크박스를 유일한 완료 현황으로 사용한다.** 하단 상세 설명에는 중복 완료 체크박스를 만들지 않는다.
3. Task는 구현·관련 검증·결과 기록까지 끝났을 때만 체크한다. Phase는 하위 Task가 모두 완료되고 해당 Phase의 종료 조건을 충족했을 때 체크한다.
4. 진행 중·보류·외부 설정 필요 상태는 마지막의 세션 기록에 적는다. 키·로그인·배포 권한이 없다고 검증을 통과한 것으로 표시하지 않는다.
5. 추가 작업은 해당 Phase에 새 Task ID를 붙이고 상단 목록과 하단 상세를 함께 추가한다.
6. 다음 단계 구현으로 검증 결과가 무효가 되면 관련 Task의 체크를 해제하고 이유를 기록한다.

### 범위와 해석 원칙

- MVP 입력은 URL·텍스트만이다. URL 자동 본문 추출, 파일 업로드, OCR, PC 연결, Cloud Storage는 MVP 작업에 끼워 넣지 않는다.
- URL만 받은 자료는 `링크만 저장됨 / 본문 미확인`이다. 사용자가 주지 않은 제목·본문·자막을 읽었다고 표시하지 않는다.
- 모든 조회와 변경은 서버에서 소유자·자료 모드를 확인한다. 변경은 버전과 중복 요청 ID를 검증한다.
- 표본과 개인 자료, 비서 자료 `materials`와 숫자 기록 `data`, AI 제안과 사용자 최종 값을 각각 구분한다.
- 채팅 근거는 보관 승인·보관 완료·활성 자료 중 AI 분석 제외가 아닌 자료만 사용한다. 이 조건은 매 질문과 과거 문맥 재사용 시 다시 확인한다.
- 분석은 사용자 시작 이후에만 호출한다. 미리 정한 한도와 실제 Provider 제한을 구분하고, 입력 저장은 AI 호출 성공 여부와 무관하게 보장한다.
- 중요도는 `높음 / 보통 / 낮음`, 정보 부족은 `판단 보류`다. 자동 학습 모델이나 외부 인기 점수를 만들지 않는다.
- 시간은 UTC로 저장하고 화면·날짜별 집계는 Asia/Seoul을 사용한다.
- 실제 키는 `.env` 또는 배포 환경변수에만 둔다. `.env.example`에는 변수 이름과 빈 값만 기록한다.
- 목업만 단일 HTML이다. 실제 서비스 파일은 기능별로 분리할 수 있다.
- **PRD §17은 MVP 범위 정의가 아니라 목업·실제 화면에 반영할 변경 목록이다.** 이 계획은 목업을 고치지 않고 실제 화면을 `web/`에 새로 만들므로, §17 항목을 해당 화면 Task(T02.03·T03.03·T04.04·T05.02·T06.04·T07.04, PC 항목은 T09.05·T10.x)의 확인 목록으로 사용한다. PC 관련 항목은 §3.1·§16에 따라 확장 단계에 적용한다.
- Phase 01~08에서 외부 자동 수집·예약 정리·자동 삭제·Telegram·Obsidian·macOS·다중 PC를 구현하지 않는다.

### 미결정 사항을 다루는 방법

| PRD 항목 | 결정이 필요한 시점 | 결정 전 적용할 기준 |
|---|---|---|
| Open Decision 1: 복수 프로젝트 관계 | ✅ 결정됨(2026-10-01) | 주 프로젝트 `primary_project_id` + 관련 프로젝트 `related_project_ids[]`. MVP 화면은 주 프로젝트만 고른다(`docs/decisions.md`). |
| Open Decision 2: 저장 이유와 메모 | ✅ 결정됨(2026-10-01) | 별도 필드 `save_reason`(선택, 2,000자), 메모는 나중 생각용(`docs/decisions.md`). |
| Open Decision 3: 모바일 삭제 썸네일 | T09.05 검토 화면 확정 전 | MVP에 영향 없음. 확장 단계에서 파일명·요약·이유만으로 충분한지 확인한다. |
| Open Decision 4: 실제 접수 수의 채팅 사용 | T07.01 | 결정 전 `source=actual`의 `received_count`는 채팅 문맥에서 제외한다. UI의 접수 통계 조회까지 금지하는 의미는 아니다. |
| Open Decision 5: 분석 제외 자료의 메타데이터 | T05.04·T07.01 | 결정 전 해당 자료는 채팅에서 완전히 제외한다. 제목·파일명만 보내는 우회도 만들지 않는다. |

미결정 항목이 있는 Task의 독립적인 부분은 진행할 수 있다. 사용자 선택을 받지 않은 설계를 확정 요구사항으로 바꾸거나 그 항목까지 완료 체크하지 않는다.

## 2. 제안 파일 구조와 공통 계약

아래 경로는 `assignments/M1-2/` 기준의 **새 구현 파일 제안**이다. 현재 파일이 존재하거나 인터페이스가 구현되어 있다는 뜻이 아니다. 구현 중 구조를 조정하면 해당 Task의 파일 경로와 이 절을 함께 고친다.

```text
M1-2/
  prd.md / task.md / README.md / .env.example / .gitignore
  ai-secretary/AI_SECRETARY_SCENARIO.md
  mockup/index.html
  web/
    index.html
    assets/app.css
    js/app.js / api.js / auth.js / config.template.js
    js/views/       # Task별 화면 파일
    scripts/build-config.mjs  # 로컬·배포에서 공개 설정만 사용해 js/config.js 생성
  server/
    requirements.txt / requirements-dev.txt
    app/main.py
    app/core/config.py / auth.py / firestore.py / requests.py
    app/features/   # 기능마다 schemas.py·routes.py·service.py 등
    scripts/smoke_ai.py / seed_sample.py
    tests/
  connector/       # Phase 09부터 생성
    requirements.txt
    app/
    tests/
    packaging/      # Phase 10에서 설치 패키지 구성
  docs/
    decisions.md / verification.md / api-contract.md / deployment.md
  render.yaml
  web/vercel.json
```

`docs/verification.md`에는 실제 실행한 결과만 적는다. 성공/실패, 날짜, 명령, 관찰 결과, 제한을 기록한다. 미실행 항목은 `미검증`으로 남긴다. 비용이 발생하는 실제 AI 호출은 꼭 필요한 연결·최종 시연에 사용하고, 상태·권한·오류 테스트는 가짜 Provider 응답으로 재현한다.

### 공통 요청과 서버 내부 인터페이스

다음 이름은 Task 간 연결을 위한 권장 구현 계약이다. PRD의 한글 상태 표시와 대응시킨다. 변경하면 소비하는 Task도 같이 수정한다.

```python
from dataclasses import dataclass
from typing import Literal

Mode = Literal["personal", "sample"]
Source = Literal["actual", "manual", "sample"]
Metric = Literal["received_count", "kept_count"]

@dataclass(frozen=True)
class RequestContext:
    owner_id: str
    mode: Mode
    request_id: str

# 아래는 계약 표기다. 구현은 각 기능 모듈에 둔다.
# material_is_chat_eligible(material, context) -> bool
# search_materials(context, query, filters, cursor) -> SearchPage
# summarize_data(context, source, metric, start_date, end_date) -> Summary
# analyze_material(context, material_id, expected_version) -> AnalysisState
# approve_review(context, payload) -> ApprovalResult
# handle_chat(context, conversation_id, question) -> ChatResult   # 채팅 서비스: 문맥 구성·Adapter 호출·대화 저장
# (AI Adapter의 answer_question(messages) -> 답변 과 구분한다. T04.01 참고)
```

- 소유자 ID는 인증 토큰에서 얻는다. 브라우저가 보낸 `owner_id`를 신뢰하지 않는다.
- 프론트는 요청마다 `X-Data-Mode: personal|sample` 헤더로 현재 모드를, 변경 요청에는 `Idempotency-Key` 헤더로 중복 요청 식별자(`RequestContext.request_id`)를 보낸다. 모드가 없거나 허용 밖이면 422다. **요청에 담긴 모드를 그 요청의 기준으로 삼는다.** 마지막 사용 모드는 브라우저에만 보관하며, 창이 여러 개여도 각 요청은 자기 모드의 자료만 다룬다. 수정·승인에는 `expected_version`을 포함한다. 묶음 승인은 각 자료의 ID·버전·선택 작업을 유지한다.
- 상태 변경과 승인 기록을 일관되게 저장한다. 같은 요청을 다시 보내면 처음 결과를 돌려주고, 같은 ID로 다른 내용을 보내면 409로 거부한다.
- HTTP 401: 인증 없음/무효, 403: 인증됐지만 허용 소유자가 아닌 계정, 404: 없거나 다른 소유자의 자료, 422: 잘못된 입력/허용 밖 경로, 409: 버전·상태·이름 충돌. PC 작업의 202는 접수만 의미한다.
- `SearchPage`는 자료와 다음 커서, 검색한 범위를 포함한다. `Summary`는 PRD §11.2의 출처·모드·기간·일별 값·합계·평균·최소·최대·추세를 포함한다.
- `AnalysisState`는 상태·자료 버전·실제 분석 범위·구조화 결과·오류 분류를 포함한다. `ChatResult`는 답변·검증된 출처·숫자 출처·저장된 대화/메시지 ID를 포함한다.
- 상세 API 요청/응답 예시는 구현 때 `docs/api-contract.md`와 FastAPI Swagger에 맞춰 기록한다. 이 문서의 권장 계약만으로 미구현 API를 사용 가능하다고 표시하지 않는다.

### 개발·검증 명령 기준

작업 폴더에서 PowerShell로 실행한다. 아래 명령은 T01.02에서 해당 파일을 만든 뒤 사용한다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r server/requirements.txt -r server/requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir server --reload
.\.venv\Scripts\python.exe -m pytest server/tests -q
```

Task 상세에 나온 `server/tests/test_*.py`는 그 Task에서 작성할 테스트다. 상태 전이·권한·집계·재시도처럼 실패 시 사용자가 잘못된 결과를 받는 규칙을 우선 검증한다. 단순 문구나 파일 존재를 확인하는 테스트를 반복 작성하지 않는다. PC 실제 파일 검증은 Phase 09~10 전용 테스트 폴더에서만 수행한다.

## 3. Phase별 상세 작업

## Phase 01. 개발 기준과 AI 연결 검증

**범위:** MVP. **선행:** 없음. **종료 조건:** 최신 요구사항·개발 환경을 확인하고 A25 실제 호출 결과를 남긴다. A25 실패 시 원인과 다음 조치를 기록하며 MVP 제출 가능 판정을 보류한다.

### T01.01 최신 PRD·작업 경로·미결정 사항 확인

- **파일:** 읽기 `prd.md`, `README.md`, `mockup/index.html`, `ai-secretary/AI_SECRETARY_SCENARIO.md`; 생성 `docs/decisions.md`.
- **작업:** `git status`·브랜치·PRD 버전을 확인하고 진행 중인 변경을 보존한다. PRD §3·§16으로 MVP 경계를 고정한다. Open Decisions 1·2의 결정 시점을 기록한다. 과제 원문이 외부에 있으면 접근 여부를 기록하고 PRD만으로 새 과제 조건을 만들어내지 않는다.
- **산출/연결:** 다음 Task들이 참조할 작업 경로, 단계별 범위, 결정 기록. §17은 이 문서의 해석 원칙에 따라 실제 화면 확인 목록으로 사용한다.
- **완료/검증:** 현재 기준 커밋과 10개 화면 키를 기록하고 Phase 08까지 파일 업로드·PC 작업이 들어가지 않았는지 대조한다.

### T01.02 Python 환경·환경변수·프로젝트 기본 실행 구성

- **선행:** T01.01. **파일:** 생성 `server/requirements.txt`, `server/requirements-dev.txt`, `server/app/main.py`, `server/app/core/config.py`; 수정 `.env.example`, `.gitignore`.
- **작업:** Python 3.10+ 환경에서 PRD 필수 패키지와 개발용 pytest를 구성한다. 설정은 환경변수에서 읽고 필수값 누락을 구분한다. `/health`로 서버 시작을 확인한다. 테스트 환경에서는 실제 키가 없어도 가짜 의존성을 주입할 수 있게 한다.
- **산출/연결:** 다음 Task에서 가져다 쓸 설정 객체와 FastAPI 앱. 키 누락과 Provider 호출 실패를 구분한다.
- **완료/검증:** 공통 실행 명령으로 서버 시작과 `/health` 응답을 확인한다. `git check-ignore .env`와 추적 파일 목록을 확인한다. 실제 키 값은 출력하거나 기록하지 않는다.

### T01.03 Codyssey 프록시 GPT 텍스트 호출 검증

- **선행:** T01.02. **파일:** 생성 `server/scripts/smoke_ai.py`, `docs/verification.md`.
- **작업:** `OPENAI_API_KEY`, `AI_PROVIDER_BASE_URL`, `AI_PROVIDER_MODEL`을 환경변수에서 읽어 Python `openai` SDK로 GPT 텍스트 1회를 호출한다. 모델명·응답 형태·SDK 버전·실제 성공 여부를 기록한다. 이미지 지원·비용·한도 정보는 확인한 범위와 미확인 범위를 분리한다.
- **산출/연결:** 당시 Codyssey 호출 방식의 검증 기록. 현재 기본 경로는 T01.04에서 선택한 Hermes다.
- **완료/검증:** `server/scripts/smoke_ai.py`의 과거 성공 결과를 보존한다. 현재 A25 판정은 T01.04의 Hermes 경로를 사용한다.

### T01.04 Hermes 로컬 API·도구 제한·GPT 텍스트 호출 검증

- **선행:** T01.02, T01.03의 과거 기록 보존. **파일:** 생성 `server/app/features/analysis/provider.py`, `server/scripts/smoke_hermes.py`; 수정 `server/app/core/config.py`, `.env.example`, `prd.md`, `docs/verification.md`.
- **작업:** 서버 `.env`를 로컬 Hermes API로 전환하고, 구독 경로와 모델을 요청마다 명시한다. Hermes `api_server`의 도구 세트가 전부 꺼져 있는지 호출 직전에 확인한다. Claude 구독 경로가 한도 오류일 때 임의로 다시 호출하거나 자동 전환하지 않는다.
- **완료/검증:** Python `openai` SDK로 `provider=openai-codex`, `model=gpt-6-luna` 텍스트 응답이 정상 종료되고 내용이 비어 있지 않아야 한다. `finish_reason=error`·도구 활성·도구 조회 실패를 실패로 처리한다. 키·원문·오류 본문을 기록하지 않는다. 전체 분석 및 채팅 API는 T04.01·T07.02가 구현한다.

## Phase 02. 인증·데이터 기반·웹 공통 화면

**범위:** MVP. **선행:** Phase 01의 환경 구성. **종료 조건:** 소유자가 로그인해 PC·모바일에서 10개 메뉴와 자신의 자료 모드를 사용할 수 있다.

### T02.01 단일 소유자 로그인과 서버 인증

- **파일:** 생성 `server/app/core/auth.py`, `server/app/core/context.py`, `web/login.html`, `web/js/auth.js`, `server/tests/test_auth.py`, `docs/api-contract.md`; 수정 `server/app/main.py`, `server/app/core/config.py`, `.env.example`.
- **작업:** Firebase Authentication의 **Google 로그인**으로 구성한다. 서버는 `Authorization: Bearer <ID 토큰>`을 Admin SDK로 검증하고 `uid == OWNER_UID`인 소유자만 허용한다. 토큰 검증 함수는 주입 가능하게 두어 테스트에서 실제 Firebase 없이 대체한다. 서비스 계정은 `FIREBASE_SERVICE_ACCOUNT_JSON`에 JSON 문자열로 넣고, 형식 오류 메시지에 내용을 출력하지 않는다. 요청 헤더 `X-Data-Mode: personal|sample`과 `Idempotency-Key`로 `RequestContext`를 만든다. 보호된 확인용 API `GET /api/me`(소유자 UID·현재 모드 반환)를 추가하고 `docs/api-contract.md`에 PRD 외 추가 API로 기록한다. Admin SDK는 클라이언트 보안 규칙을 우회하므로 서비스 계층에서도 소유권을 확인한다.
- **산출/연결:** 인증 공통 의존성과 `RequestContext`. 최소 로그인 페이지(`web/login.html`)는 Google 로그인·로그아웃·`/api/me` 호출만 제공하며, 웹 화면 통합은 T02.03에서 한다. 프론트에는 공개 인증 값(`apiKey`, `authDomain`, `projectId`)만 전달한다.
- **완료/검증:** `test_auth.py`에서 토큰 없음·무효 토큰 **401**, 인증됐지만 `OWNER_UID`가 아닌 계정 **403**, `X-Data-Mode` 없음·허용 밖 값 **422**, 소유자 정상 통과를 확인한다. 다른 소유자 자료를 숨기는 404는 자료 API가 생기는 T02.02에서 검증한다. Firebase 프로젝트 준비 후 실제 Google 로그인 1회로 `/api/me` 200을 확인하고, 로그아웃 직후 브라우저가 토큰을 보내지 않아 401이 되는지 확인한다. Firebase ID 토큰은 로그아웃 후에도 최대 1시간 유효하며 MVP는 토큰 폐기(`check_revoked`)를 요구하지 않는다. 실제 로그인 확인 전에는 단위 테스트 통과만으로 이 Task를 체크하지 않는다. A16의 웹 범위에 대응한다.

### T02.02 Firestore 저장 구조·버전·중복 요청 처리

- **파일:** 생성 `server/app/core/firestore.py`, `server/app/core/requests.py`, `server/tests/test_request_consistency.py`, `docs/api-contract.md`.
- **작업:** PRD §9의 자료·접수 기록·설정·프로젝트·숫자 기록·대화를 소유자와 모드로 격리한다. 자료 변경은 현재 버전 확인 후 처리한다. 요청 ID와 내용 요약값을 저장해 재전송과 ID 오용을 구분한다. PC 관련 컬렉션은 확장 단계에서 생성한다. 데이터 접근은 서버 Admin SDK로만 하므로 **Firestore 보안 규칙은 클라이언트 읽기·쓰기를 전면 거부**하고 규칙 파일(`firestore.rules`)을 배포한다. 서버 로그에는 요청·작업 ID·상태·오류 분류만 남기고 자료 원문·토큰·비밀키를 기록하지 않는다(PRD §14).
- **산출/연결:** 데이터 접근 경계, 페이지 커서 규칙, 상태 변경의 원자성/재시도 규칙. AI 호출은 DB 트랜잭션 내부에 넣지 않는다.
- **완료/검증:** 같은 요청 두 번에 자료가 하나만 생기고, 이전 버전의 수정과 같은 ID의 다른 요청은 409가 되는지 검증한다. 서버 재시작 후에도 중복 여부가 유지되어야 한다. 브라우저의 Firebase SDK로 Firestore를 직접 읽기·쓰기하면 거부되는지 확인한다(A16 웹 범위). T02.01에서 옮겨온 검증: 다른 소유자·다른 모드의 자료 조회·수정은 존재를 숨기는 404다.

### T02.03 10개 메뉴와 모바일 공통 화면

- **파일:** 생성 `web/index.html`, `web/assets/app.css`, `web/js/app.js`, `web/js/api.js`, `web/js/config.template.js`, `web/scripts/build-config.mjs`; 수정 `.gitignore`, `.env.example`.
- **작업:** 기존 목업의 색·간격·레이아웃을 참고하되 실제 서비스 화면은 `web/`에 구성한다. PRD의 `today/inbox/knowledge/trends/ask/conversations/review/screenshots/downloads/settings` 키를 유지한다. PC는 세로 메뉴, 모바일은 접히는 메뉴로 만든다. 로딩·빈 상태·실패·재시도·로그인 만료를 공통 처리한다. 첫 요청이 늦으면 `서버 연결을 기다리고 있습니다. 첫 연결은 시간이 걸릴 수 있습니다`처럼 확인되지 않은 원인이나 완료 시간을 단정하지 않는 안내를 표시한다(PRD §14). 저장소에는 공개 설정의 구조만 담은 `config.template.js`를 두고, 로컬 실행과 배포 모두 `build-config.mjs`로 `API_BASE_URL`과 공개 인증 설정을 읽어 `web/js/config.js`를 생성한다. 필요한 값이 없으면 생성에 실패하게 하고 생성 파일은 `.gitignore`에서 제외한다.
- **산출/연결:** 각 기능 화면이 등록될 웹 셸과 인증·모드가 포함된 API 클라이언트. S08·S09는 `확장 단계 예정`과 PC 미연결 상태만 표시한다.
- **완료/검증:** 데스크톱과 390px 모바일 폭에서 10개 메뉴 이동·긴 제목·빈 목록을 확인한다. 예시 카드의 숫자와 실제 API 데이터를 혼동시키지 않는다. 입력 문자열은 HTML 실행 없이 렌더링한다. 공개 설정 누락 시 생성 실패, 정상 설정 시 `config.js` 생성, `git check-ignore web/js/config.js`로 Git 제외를 확인하고 생성 파일에 서버 비밀키가 없는지 검사한다.

### T02.04 프로젝트·관심 분야·자료 모드 설정

- **선행:** T02.01~03 및 Open Decision 1 확인. **파일:** 생성 `server/app/features/projects/routes.py`, `server/app/features/projects/service.py`, `server/app/features/settings/routes.py`, `server/app/features/settings/service.py`, `web/js/views/settings.js`, `server/tests/test_settings.py`.
- **작업:** 프로젝트 목록·생성·수정 API와 관심/활동 분야 설정을 만든다. 설정 저장을 위한 `GET/PUT /api/settings`는 PRD 기능을 구현하는 추가 API 제안으로 `docs/api-contract.md`에 기록한다. 현재 주 프로젝트와 복수 관계의 결정 결과를 반영한다. 개인/표본 모드 전환 시 목록·캐시·열린 대화까지 갱신한다.
- **산출/연결:** 분석이 참조할 사용자 설정과 프로젝트, 모든 화면이 사용할 현재 모드.
- **완료/검증:** 설정이 새로고침 뒤 유지되고, 모드 전환 후 이전 모드 자료·대화가 나타나지 않는지 확인한다. 별도 관리자 계정은 만들지 않는다.

## Phase 03. URL·텍스트 접수와 보관 승인

**범위:** MVP. **선행:** Phase 02. **종료 조건:** AI가 없어도 URL·텍스트를 저장·수정·검토·보관할 수 있고 승인 상태가 유지된다.

### T03.01 URL·텍스트 입력·저장·상세 수정

- **파일:** 생성 `server/app/features/materials/schemas.py`, `server/app/features/materials/routes.py`, `server/app/features/materials/service.py`, `web/js/views/inbox.js`, `server/tests/test_material_intake.py`.
- **작업:** URL 또는 제목·설명·본문 중 하나 이상을 받는다. HTTP(S)만 허용하고 원래 URL을 보존한다. 설명과 입력 본문을 분리하며 Open Decision 2의 결정대로 저장 이유를 보존한다. PRD의 권장 입력 길이를 설정으로 관리하고 초과 시 422와 사용자 안내를 반환한다. 파일 업로드 필드를 만들지 않는다.
- **산출/연결:** `POST/GET /api/materials`, `GET/PUT /api/materials/{id}`. 접수 기록과 자료를 함께 저장하고 입력만으로 자동 AI 호출하지 않는다.
- **완료/검증:** URL만 입력, 제목만 입력, 빈 입력, 잘못된 스킴, 길이 초과, HTML 문자열을 검사한다. URL만 있으면 본문 미확인 상태이며 가짜 페이지 제목·요약이 없다. A01에 대응한다.

### T03.02 동일 URL 확인과 세 가지 선택

- **선행:** T03.01. **파일:** 생성 `server/app/features/materials/url_keys.py`, `server/tests/test_url_duplicates.py`; 수정 자료 서비스와 받은 자료 화면.
- **작업:** 호스트 대소문자·기본 포트만 안전하게 정규화한다. 쿼리와 의미 있는 경로는 보존한다. 중복 결과에 기존 자료의 접수일·현재 상태를 포함하고 `기존 자료 열기 / 메모 추가 / 별도 저장`을 제공한다. 메모 추가는 기존 본문을 덮어쓰지 않는다.
- **산출/연결:** 중복 선택 값과 대상 버전을 자료 접수 계약에 추가한다. 내용 유사도는 이 Task에서 동일 URL로 취급하지 않는다.
- **완료/검증:** 같은 URL의 세 선택, 서로 다른 쿼리, 동시 등록, 휴지통에 있는 기존 자료, 다른 소유자/모드 자료 비노출을 확인한다. 별도 저장 선택일 때만 새 접수 기록이 증가한다 — 이는 PRD에 없는 해석이므로 `docs/decisions.md`에 기록하고 사용자 확인을 받는다. A18에 대응한다.

### T03.03 받은 자료·일괄 검토·보관 승인

- **파일:** 생성 `server/app/features/reviews/schemas.py`, `server/app/features/reviews/routes.py`, `server/app/features/reviews/service.py`, `web/js/views/review.js`, `server/tests/test_review_approval.py`.
- **작업:** 받은 자료와 승인 요청 목록을 구분한다. 묶음 선택·일부 제외·제목/중요도/프로젝트 수정 후 승인한다. `POST /api/reviews/approve`의 `keep`은 자료 ID·예상 버전·선택 내용을 검증하고 승인 시각을 기록한다. URL·텍스트는 보관 승인 시 보관 완료가 된다.
- **산출/연결:** 승인 결과와 자료별 성공/충돌 결과. `link`·`trash`는 Phase 05에서 같은 승인 API로 연결한다.
- **완료/검증:** 선택한 항목만 승인되고 충돌 항목을 성공으로 표시하지 않는다. 동일 요청 재전송으로 승인 시각·자료 수가 중복 변경되지 않는다. 사용자 수정값은 새로고침 후 유지된다. A02 중 검토·승인 범위에 대응한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 검토 요청은 `review_requested`·`review_requested_at` 별도 필드, 목록은 `GET /api/materials?view=inbox|review`(PRD 외 추가)와 `POST /api/reviews/request`(PRD 외 추가), 중요도는 사용자 최종값 `user_importance`(높음·보통·낮음·판단 보류)만, 일괄 승인은 요청 전체 오류만 422이고 그 밖에는 200 + 항목별 결과(`approved / already_approved / conflict / not_found / invalid`).
- **추가 검증:** 다른 소유자·모드 자료가 섞이면 그 항목만 `not_found`, 휴지통 자료 거부, 일부만 충돌할 때의 응답, 이미 승인된 자료를 새 키로 다시 보낼 때 `already_approved`, 보관 완료 판정 조건, 사용자 수정값의 새로고침 후 유지는 실제 브라우저로 확인.
- **2026-10-02 코드 리뷰 보완:** 새 키로 이미 승인된 자료에 수정값을 보내면 `conflict`로 응답하고 화면에서 입력을 보존한 뒤 `PUT /api/materials/{id}`로 저장한다. 승인·되돌리기는 50건씩 순차 전송하고 실패 묶음부터 같은 키로 재개한다. 실제 브라우저 충돌 복구와 Firestore 저장은 `docs/verification.md`에 기록했다. 51건 분할·실패 재개는 자동화 테스트로 확인했으며, 실제 브라우저 대량 시연은 후속 보완 검토로 남긴다.

### T03.04 나중에 보기·분석 제외·승인 상태 검증

- **파일:** 생성 `server/tests/test_material_states.py`; 수정 자료 스키마·서비스·검토 화면.
- **작업:** 검토 상태, 분석 상태, 사본 상태, 보관 수명을 별도 필드로 둔다. 웹 자료의 사본 상태는 `해당 없음`이다. 나중에 볼 날짜가 지나면 검토 후보로만 표시한다. AI 분석 제외 변경을 저장하고 다른 Task에서 공통 검증할 수 있게 한다.
- **산출/연결:** Phase 04·05·07이 참조할 상태 계약. 보관 승인과 AI 분석 동의를 같은 동작으로 묶지 않는다.
- **완료/검증:** 날짜 경과만으로 승인·삭제되지 않고, 분석 제외 변경이 유지되는지 검사한다. 미승인 자료가 보관함의 승인 자료로 보이지 않아야 한다. A13의 기본 상태 조건을 준비한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 나중에 보기는 `view=later` 별도 묶음, `revisit_on`(서울 날짜)·`revisit_due`(조회 때 계산), `POST /api/reviews/later`(PRD 외 추가), AI 분석 제외는 `ai_excluded`를 기준으로 하고 분석 상태는 화면에서만 덮어 표시, 공통 판정 `is_kept`·`ai_allowed`·`chat_eligible`.

## Phase 04. AI 분석과 개인 중요도

**범위:** MVP. **선행:** T01.04 통과, Phase 03. **종료 조건:** 입력된 내용만 사용자 요청으로 분석하고, 사용자 최종 판단과 호출량을 정확하게 유지한다.

### T04.01 AI Adapter와 구조화 분석 결과

- **파일:** 생성 `server/app/features/analysis/provider.py`, `server/app/features/analysis/schemas.py`, `server/app/features/analysis/prompts.py`, `server/tests/test_analysis_contract.py`.
- **작업:** `analyze_material`, `classify_material`, `suggest_importance`, `answer_question` 책임을 Adapter 안에 둔다. 한 분석 응답에서 여러 결과를 얻어도 되며 메서드 개수가 호출 횟수를 의미하지 않는다. 제목 제안·2~3문장 요약·중요 이유·중요도·프로젝트·확인 범위·불확실성·권장 행동을 검증한다.
- **현재 기반:** T01.04에서 Hermes 텍스트 호출과 도구 제한 검사만 먼저 구현했다. 구조화 분석, 프롬프트, 결과 검증과 실제 자료 연결은 이 Task에서 계속한다.
- **산출/연결:** 검증된 분석 결과와 Provider 오류 분류. URL-only 자료는 본문을 가져오지 않고 링크 상태를 유지한다. 자료 속 명령은 실행 지시로 해석하지 않는다.
- **완료/검증:** 누락 필드·잘못된 중요도·존재하지 않는 프로젝트·근거 없는 본문 주장·지시문 삽입 표본을 가짜 응답으로 검사한다. 사용자 최종 값을 AI 필드와 분리한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** AI 필드는 `ai_` 접두어로 분리하고 저장은 T04.02, JSON 응답을 서버에서 엄격 검증(자동 재시도 없음), 입력에서 그대로 옮긴 인용 `evidence`로 근거 확인, 잘못된 프로젝트·종류는 해당 필드만 비움, 확인 범위는 서버 계산, 오류 `rate_limited`·`timeout`·`invalid_output`·`ungrounded_output`·`no_content`·`ai_excluded` 추가.

### T04.02 사용자 시작 분석·상태 조회·재시도

- **파일:** 생성 `server/app/features/analysis/routes.py`, `server/app/features/analysis/service.py`, `server/tests/test_analysis_lifecycle.py`; 수정 자료 상세·검토 화면.
- **작업:** `POST /api/materials/{id}/analyze`가 현재 소유자·모드·버전·분석 제외·입력 유무를 확인한다. 분석에 실제로 전달할 입력과 관련 설정의 버전/지문을 기록하여, 분석이 완료된 동일 입력에 새 request_id가 와도 기존 결과를 돌려주고 Provider를 다시 호출하지 않는다. 입력이 바뀌면 새 분석 대상으로 취급하고, 실패한 호출의 재시도는 사용자가 선택할 때만 진행한다. 분석 상태를 DB에 저장하고 `GET /api/materials/{id}`로 조회한다. 요청 연결이 끊겨도 저장된 상태를 볼 수 있게 한다. 서버 재시작 후 불명확한 호출은 결과 확인 필요/사용자 재시도로 처리하며 몰래 재호출하지 않는다.
- **산출/연결:** 분석 시작·완료·대기·실패 상태와 재분석 진입점. 재분석 결과는 분석 대상 버전이 같은 경우에만 적용한다.
- **완료/검증:** 분석 전 이탈, 실패, 처리 중 자료 수정, 서버 재시작, 같은 요청 반복을 검사한다. 새 request_id로 완료된 동일 입력을 다시 요청해도 Provider 호출 수가 증가하지 않고, 실패 후 사용자 재시도는 가능해야 한다. 원래 입력은 보존되고 사용자의 중요도·제목 수정은 덮어쓰지 않는다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 202 접수 + 같은 프로세스 백그라운드 실행 + `GET` 조회, 분석 쓰기는 버전을 올리지 않는 `transform`(분석 중 수정 허용, 끝날 때 내용이 바뀌었으면 결과 버림), 입력 지문 = 보낼 내용 + 활성 프로젝트 + 프롬프트 버전(모델명 제외), 상태 `link_only·awaiting_start·analyzing·done·failed`, 결과 확인 필요는 기한(요청 시간 × 2) 경과 시 조회 때 계산, 받은 자료 상세·검토 카드의 공통 분석 패널.

### T04.03 AI 사용량·한도·전송 범위 표시

- **파일:** 생성 `server/app/features/analysis/usage.py`, `server/tests/test_ai_usage.py`; 수정 API 응답·분석 확인 화면·채팅 공통 사용량 영역.
- **작업:** Provider에 실제 보낸 요청마다 사용량을 기록하고 분석·채팅이 같은 일별 한도를 사용하게 한다. PRD 초깃값 50회/일·출력 1,500토큰 상당과 로컬 Hermes 요청 시간 120초를 검증 가능한 설정으로 둔다. 요청 예약과 실제 전송을 구분하여 동시 요청의 한도 초과를 막고, 실제 전송된 실패/429 요청도 기록한다. 묶음 20개와 AI 1회를 같은 것으로 세지 않는다.
- **산출/연결:** 현재 사용량·남은 한도·분석 대기 자료 수·전송 범위 안내. 확인되지 않은 가격은 금액을 만들어 표시하지 않는다.
- **완료/검증:** 한도 직전 동시 요청, 429, 타임아웃, 날짜 변경, 사용자 재개를 검사한다. 초과분은 분석 대기로 남고 일자 변경만으로 호출되지 않는다. A23에 대응한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 소유자 전체(개인·표본 합산)·서울 날짜 기준, 시작 시 원자적 예약·보내기 전 실패만 환불, 한도 도달·Provider 429는 `quota_waiting`(날짜 변경만으로 호출하지 않고 사용자가 재개), `GET /api/ai/usage`(PRD 외 추가)와 분석 확인 상자의 사용량 줄, 요청 시간 기본값 120초, 1,500토큰은 요청당 출력 상한.

### T04.04 오늘·AI 동향·중요도 수정 화면

- **파일:** 생성 `web/js/views/today.js`, `web/js/views/trends.js`, `server/tests/test_material_priority.py`; 수정 자료 목록 정렬·검토 화면.
- **작업:** 최종 중요도 높은 순 → 대응 필요 우선 → 최신 접수 순으로 정렬한다. 오늘은 같은 규칙으로 최대 3건을 표시한다. 판단 보류는 별도로 보여주며 미승인 자료에는 검토 대기를 표시한다. 사용자 수정은 다음 정렬에 즉시 반영한다.
- **산출/연결:** S01·S04 실제 자료 화면. 외부 인기 숫자나 예약 브리핑이 실행된 것 같은 문구를 제거한다.
- **완료/검증:** 자료 없음, 1건, 3건 초과, 중요도 동률, 사용자 변경, AI 실패를 확인한다. A02의 요약·이유·최종 중요도 유지까지 완료한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 최종 중요도 = 사용자 값, 없으면 지금 내용 기준의 AI 제안(출처 표시), 대응 필요는 AI 출력 `needs_action` 추가(`PROMPT_VERSION` .2), `GET /api/materials/priority`(PRD 외 추가)에서 최대 500건 서버 정렬, 오늘은 높음·보통 최대 3건, AI 동향은 대응 필요·학습 자료·판단 보류와 바로 수정, 검토 카드의 AI 제안 표시·'제안 적용'.

## Phase 05. 보관함·관련 자료·웹 휴지통

**범위:** MVP. **선행:** Phase 03, 관련 제안에는 Phase 04. **종료 조건:** 자료를 찾고 연결하며 휴지통·복원·영구 삭제를 일관되게 처리한다.

### T05.01 보관함 검색·필터·페이지네이션

- **파일:** 생성 `server/app/features/materials/search.py`, `web/js/views/knowledge.js`, `server/tests/test_material_search.py`.
- **작업:** 제목·설명·입력/추출 본문·메모와 기간·종류·프로젝트를 검색한다. 소규모 MVP는 서버/Python 검색을 우선 검증하되 실제 Firestore 에디션·자료량을 확인하고 전략을 기록한다. 전체 검색 범위와 화면 페이지 크기를 구분한다. 검색을 제한하면 일부 자료 기준임을 응답과 화면에 표시한다.
- **산출/연결:** `search_materials`와 S03 목록/상세. 채팅·관련 자료도 같은 검색 계약을 재사용한다.
- **완료/검증:** 첫 페이지 밖의 정답 자료, 한글, 긴 본문, 기간 경계, 다른 모드, 미승인/휴지통 제외를 확인한다. 검색 오류를 결과 0건으로 바꾸지 않는다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 보관 완료 자료만, 사용자 입력 6개 필드(AI 결과 제외), 검색어 AND·대소문자 무시·부분 일치, 서울 날짜 기간·AI 종류·링크/텍스트·프로젝트(주·관련) 필터, Firestore Standard라 최신 1,000건을 Python으로 검색하고 `scope`로 범위 표시, `GET /api/materials/search`(PRD 외 추가).

### T05.02 관련 자료 제안·연결·해제

- **파일:** 생성 `server/app/features/materials/related.py`, `server/tests/test_related_materials.py`; 수정 검토·보관함·승인 서비스.
- **작업:** 실제 내용·프로젝트·키워드의 근거로 기존 승인·활성 자료를 후보로 낸다. 근거가 약하면 빈 목록을 반환한다. 승인 API의 `action=link` 안에 연결/관련 없음/해제 선택과 두 자료의 ID·버전을 기록한다. 제안 상태와 사용자가 확정한 관계를 구분한다.
- **산출/연결:** `GET /api/materials/{id}/related`, 관계 저장과 화면 표시. 정확한 URL 중복 선택과 혼합하지 않는다.
- **완료/검증:** 관련 없는 후보, 삭제된 대상, 버전 변경, 연결 해제, 같은 URL과 유사 내용의 차이를 확인한다. A19에 대응한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 같은 모드 보관 완료 자료 중 자기·같은 URL·판단한 짝 제외, AI 없이 프로젝트·AI 핵심어·공통 단어로 근거 계산, (프로젝트+1) 또는 핵심어 2 또는 단어 3 미만이면 후보 없음, 최대 5건, 승인 API `action=link`(link|unrelated|unlink)와 짝마다 `material_links` 기록(두 버전·근거), 자료 버전 유지, 검토 카드·보관함 상세의 관련 자료 패널.

### T05.03 웹 자료 휴지통 이동·복원·영구 삭제

- **파일:** 생성 `server/app/features/trash/routes.py`, `server/app/features/trash/service.py`, `server/tests/test_web_trash.py`; 수정 승인 서비스·보관함 탭.
- **작업:** 승인 API의 `action=trash`로 활성 웹 자료를 휴지통으로 보내고 보관 수명 상태와 `trashed_at`을 기록한다(PRD §9.2 `materials`. 파일 사본의 `trash_at`과 구분). 휴지통 목록·복원·별도 확인을 요구하는 영구 삭제를 구현한다. 복원은 기존 승인 여부와 승인일을 보존하여 미승인 자료를 승인 자료로 바꾸지 않는다. 자동 만료는 만들지 않는다.
- **산출/연결:** `GET /api/trash`, `POST /api/trash/{id}/restore`, `DELETE /api/trash/{id}`. 영구 삭제 시 자료 본문·검색 데이터·연결 접수 기록을 제거하고 남은 관계/출처는 삭제 상태로 처리한다. 중복 요청 결과·승인 스냅샷 등에 삭제한 자료의 본문이나 자료 ID가 남지 않게 정리한다. 작업 감사 기록에는 자료 ID를 제거하고 작업 ID·상태·시간만 남긴다. 이전 대화 인용문이 남을 수 있다는 안내를 표시한다.
- **T05.02에서 넘어온 일:** 영구 삭제 시 그 자료가 들어간 `material_links` 기록도 지운다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 승인 API `action=trash`(검토 상태·승인일 유지), 복원은 원래 상태로, 영구 삭제 2단계(`deleting` 후 접수 기록·URL 예약·관련 기록·중복 요청 본문 비우기·자료 순, 실패 시 `partial`과 이어서 하기), `confirm=permanent` 필수, 휴지통 목록 새 색인(배포함), 감사 기록 `audit_events`(자료 ID 없음), 보관함 휴지통 탭과 상세의 휴지통 이동.
- **완료/검증:** 휴지통 이동→검색 제외→복원→재포함→영구 삭제를 검증한다. 일부 제거 실패는 완료로 표시하지 않는다. 영구 삭제 뒤 검색·접수 기록·중복 요청/승인 기록·감사 기록에 본문과 자료 ID가 남지 않는지 확인한다. 이전 대화 인용문은 별도 삭제 전까지 남을 수 있다는 안내를 검증한다. `kept_count` 감소와 `received_count` 재계산은 T06.02와 통합 검증한다. A26에 대응한다.

### T05.04 검색·채팅에 전달할 자료의 공통 필터

- **파일:** 생성 `server/app/features/materials/eligibility.py`, `server/tests/test_material_eligibility.py`.
- **작업:** `material_is_chat_eligible`에 소유자·모드·보관 승인·보관 완료·활성·AI 분석 제외 조건을 모은다. 분석 제외 자료의 제목·메타데이터도 결정 전에는 AI에 보내지 않는다. 일반 보관함에 보일 수 있는 자료와 AI 문맥에 보낼 수 있는 자료의 조건을 구분한다.
- **산출/연결:** Phase 07의 새 질문·과거 대화 문맥 모두에서 호출할 공통 함수. 관련 후보를 AI에 전달할 때도 동일 제외 조건을 적용한다.
- **완료/검증:** 한 조건씩 바꾼 표본으로 허용/거부를 확인하고 실제 Provider 요청 캡처에 금지 자료가 없는지 검사한다. A13 웹 범위와 AI 분석 제외 원칙에 대응한다. PRD A21의 파일 검증은 확장 단계에서 추가한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** `material_is_chat_eligible`+`exclusion_reason`(소유자·모드·활성·승인·보관 완료·AI 분석 제외), `library_visible`과 구분, 질문 때 다시 읽는 `refresh_and_filter`, AI로 보내는 필드는 사용자 입력과 접수일만(`ai_payload`), 제외 자료는 메타데이터도 보내지 않음.

## Phase 06. 숫자 기록·요약·표본 데이터

**범위:** MVP. **선행:** Phase 02~03, 실제 휴지통 통합은 Phase 05. **종료 조건:** `data` CRUD가 표본 Summary에 반영되고 실제 자료 집계와 혼합되지 않는다.

### T06.01 숫자 기록 CRUD와 입력 검증

- **파일:** 생성 `server/app/features/data/schemas.py`, `server/app/features/data/routes.py`, `server/app/features/data/service.py`, `server/tests/test_data_crud.py`.
- **작업:** `date/value/memo/metric_type/origin/mode/version`을 갖는 수기·표본 기록을 만들고 CRUD한다. 값은 0 이상 정수, 날짜는 유효 날짜로 제한한다. 실제 자료 집계값을 수정 가능한 `data` 행으로 생성하지 않는다.
- **산출/연결:** PRD의 POST/GET/PUT/DELETE `/api/data` 및 상세 API. `/summary`를 동적 ID보다 먼저/명확히 등록한다.
- **완료/검증:** 추가·조회·수정·삭제, 음수·소수·잘못된 날짜 422, 버전 충돌 409, 다른 모드 접근, 중복 재전송을 확인한다. A15의 CRUD 부분에 대응한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 출처는 모드에서(개인 manual·표본 sample, 요청으로 못 보냄), 값 0~1,000,000 엄격 정수·실제 날짜·메모 500자, 같은 날짜 여러 건 허용(요약에서 합계), 목록은 날짜 최신순·필터·커서, 삭제는 버전 확인과 한 트랜잭션.

### T06.02 실제·수기·표본 Summary와 추세 계산

- **파일:** 생성 `server/app/features/data/summary.py`, `server/tests/test_data_summary.py`.
- **작업:** 개인 기본값은 `actual + kept_count`, 표본 기본값은 `sample + kept_count`다. 실제 접수 수는 접수 기록, 실제 보관 수는 현재 승인·보관 완료·활성 자료를 승인일별로 집계한다. 수기/표본은 `data`만 읽는다. 지표·출처·모드를 섞지 않는다.
- **산출/연결:** `summarize_data`와 `GET /api/data/summary`. 관측 이후 빈 날은 0, 전체 데이터 없음은 합계 0 및 기간/평균/최소/최대/추세 null. 개인 기준일은 현재 한국 날짜, 표본은 최신 표본 날짜다.
- **완료/검증:** 14일 중 앞 7일이 매일 2건, 뒤 7일이 매일 3건이면 합계 35·평균 2.5·최소 2·최대 3·증가율 50%가 나오는지 독립 계산과 대조한다. 14일 미만, 이전 기간 0, 양쪽 0, ±10% 경계, UTC/한국 날짜 경계도 검증한다. 휴지통/복원/영구 삭제 후 재계산한다. A15에 대응한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 허용 출처는 개인 actual·manual, 표본 sample·actual(그 밖 422), 실제 접수 = 접수 기록·실제 보관 = 현재 보관 자료의 승인일(서울), 관측 시작 이후 빈 날 0, 기준일은 개인 오늘·표본 최신 날짜, 최근·이전 7일 합계 비교와 ±10% 경계, `metric_type=all`은 지표별 결과.

### T06.03 숫자 표본 100건 이상과 채팅 평가 자료

- **파일:** 생성 `server/scripts/seed_sample.py`, `server/tests/fixtures/sample_materials.json`, `server/tests/fixtures/chat_cases.json`, `server/tests/test_sample_seed.py`.
- **작업:** 60일×2개 지표=120개 숫자 표본을 고정 seed로 생성한다. 채팅 근거용 URL·텍스트 표본은 별도로 생성하고 명시적 표본·승인·보관 완료·활성 상태를 둔다. 숫자 표본을 실제 자료 수와 동기화하지 않는다. 평가 자료에 정답 자료를 가진 질문 10개와 근거 없는 질문 3개를 고정한다.
- **산출/연결:** 반복 가능한 seed 명령과 검색 평가 세트. 재실행 시 기존 ID는 건너뛰거나 동일 초기 항목만 검증하여 사용자 CRUD를 덮어쓰지 않는다.
- **완료/검증:** `.\.venv\Scripts\python.exe server/scripts/seed_sample.py`를 두 번 실행해 중복 증가와 개인 자료 변경이 없는지 확인한다. 이후 숫자 CRUD가 유지되고 표본 PC 작업은 생성되지 않아야 한다. C17·A15·A14 준비에 대응한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 고정 날짜(2026-08-02~09-30)·고정 seed 숫자 120건, 표본 자료 20건 픽스처(접수 기록·URL 예약 포함), 완료 표시 후 재실행은 확인만(사용자 CRUD를 되돌리거나 다시 만들지 않음), 평가 세트는 형식·핵심어 검색만 검증하고 채점은 T07.04, 표본 라벨 '가상 보관/접수 기록', 실제 표본 모드의 이전 시험 자료 51건 삭제(승인).

### T06.04 활동 기록·요약 화면과 변경 반영

- **파일:** 생성 `web/js/views/activity.js`; 수정 `knowledge.js`, `today.js`.
- **작업:** 활동 기록 탭에 숫자 CRUD와 기간·지표·출처 선택을 제공한다. `현재 보관 자료 수 / 사용자 입력 보관 기록 / 가상 보관 기록`을 구분한다. 변경 뒤 같은 조건으로 Summary를 다시 조회한다. 합계·평균·최소·최대·추세와 비교 부족 상태를 보여준다.
- **산출/연결:** S03 활동 기록, S01 숫자 요약. S05 채팅 화면의 요약 패널(T07.04)도 동일 API 결과를 사용한다.
- **완료/검증:** 표본 값 수정/삭제가 다음 요약에 반영되고 개인 모드 수기 수정은 실제 자료 수를 바꾸지 않는지 확인한다. 화면 캐시가 이전 값을 보여주지 않아야 한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 지식 보관함 '활동 기록' 탭(요약 + 기록 CRUD), 출처 선택지는 서버 허용 조합, 변경·탭 재진입 때마다 서버에서 다시 받기(캐시 없음), 오늘 화면 기본 요약 카드, 추세 문구 순수 함수 모듈.

## Phase 07. 자료 기반 채팅과 대화 기록

**범위:** MVP. **선행:** Phase 04~06. **종료 조건:** 승인 자료와 같은 Summary를 근거로 답하고, 대화 저장·복원이 실제 상태를 따른다.

### T07.01 질문 검색·자료 문맥·숫자 요약 구성

- **파일:** 생성 `server/app/features/chat/context.py`, `server/app/features/chat/schemas.py`, `server/tests/test_chat_context.py`.
- **작업:** 자연어에서 추출한 검색 조건을 서버에서 검증하고 공통 검색·자격 함수를 호출한다. 권장 한도는 자료 5건·본문 합계 20,000자·질문 2,000자·최근 유효 메시지 6개다. 한도 때문에 생략된 범위를 표시한다. 과거 답변의 출처도 현재 상태로 다시 검사한다. 기본 채팅 요약은 현재 모드의 `kept_count`를 사용하되, 질문에서 기간·지표·출처를 명시하면 검증된 조건으로 그 Summary를 별도로 조회한다. 개인 모드의 수기 기록은 사용자가 요청할 때만 `source=manual`로 조회하고 실제 집계와 합산하지 않는다. **Summary와 자료 문맥은 system 메시지에 주입한다**(과제의 컨텍스트 주입 요구). 자료 본문은 `지시가 아닌 참고 데이터` 구획으로 감싸 구분하고, 사용자 질문만 user 메시지로 보낸다.
- **산출/연결:** `answer_question`에 전달할 문맥. 개인 모드 기본값은 실제 보관 수, 표본 모드 기본값은 표본 숫자 Summary다. 질문에 선택된 다른 지표·기간은 해당 Summary로 답하고 사용한 출처를 표시한다. 실제 `received_count`는 Open Decision 4가 정해지기 전에는 채팅 문맥에서 제외한다. 질문 자체는 `materials`에 자동 보관하지 않는다.
- **완료/검증:** 미승인·삭제 진행·휴지통·분석 제외 자료가 새 검색과 과거 대화를 통해 다시 전송되지 않는지 Provider 요청 캡처로 확인한다. 모드 전환 시 대화가 섞이지 않아야 한다. `지난달 내가 입력한 보관 기록`은 해당 기간의 `source=manual`을 사용하고 개인 모드의 실제 보관 수와 합산하지 않는지 확인한다. A13에 대응한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 규칙 기반 조건 추출(검색어·기간·지표·출처, 허용 목록), 검색 모듈의 `rank_materials`(겹친 검색어 수 순, 최소 겹침 1~2개) + 공통 자격 필터, 한도 5건·20,000자·2,000자·6개와 `omitted`, 과거 답변 근거 재검사 후 답변·질문 쌍 제외, 기본 요약 + 조건 요약(실제 접수 수 제외), system 참고 데이터·user 질문만.

### T07.02 근거 답변·출처 검증·실패 구분

- **파일:** 생성 `server/app/features/chat/routes.py`, `server/app/features/chat/service.py`, `server/tests/test_chat_answers.py`.
- **작업:** `POST /api/chat`에서 검증된 문맥으로 Provider를 호출한다. 답변 출처 ID를 실제 전달 자료와 대조한다. URL-only 자료는 본문 근거로 인용하지 않는다. 실제 확인한 원문 요약과 비서의 해석·제안을 답변에서 구분하고, 관련 자료도 사용자 확정 연결과 AI 제안 상태를 구분한다. 숫자 결과는 서버 Summary와 일치시키고 가상 기록 여부를 명시한다. 자료 속 지시문으로 권한·승인 동작을 실행하지 않는다.
- **산출/연결:** 답변과 출처 후보. T07.03의 저장이 끝나야 성공 응답을 반환한다.
- **완료/검증:** 없는 출처 ID, 검색 결과 없음, 검색 자체 실패, Provider 실패, 악성 지시문이 포함된 본문을 각각 검사한다. 요약과 해석이 구분되고 제안 관계가 사용자 확정 관계처럼 표시되지 않는지 확인한다. 근거가 없으면 한계를 표시하며 새로운 출처를 만들어내지 않는다. A14에 대응한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** 모델은 JSON(`from_materials`·`interpretation`·`sources`(자료 번호)·`related_suggestions`·`limitations`)으로 답하고 정의 밖 필드는 버림, 번호를 전달 자료 ID로 바꾸고 없는 번호는 `rejected_source_numbers`, URL만 있는 자료는 `basis: link_only`와 한계, 확정 연결 `user_confirmed`·나머지 `ai_suggested`, 숫자는 서버 Summary + `virtual`·확인 안 된 숫자 표시, 실패 구분 503 `search_failed`·429 `quota_exceeded`·502 `provider_failed`(`kind`), 대화는 `conversations` 문서에 저장한 뒤 성공(목록·삭제·저장 실패 재시도는 T07.03).

### T07.03 대화 자동 저장·불러오기·삭제

- **파일:** 생성 `server/app/features/conversations/routes.py`, `server/app/features/conversations/service.py`, `server/tests/test_conversations.py`.
- **작업:** 대화·사용자 질문·AI 답변·검증 출처·당시 숫자 요약·request_id를 저장한다. 저장 실패 상태와 재시도를 제공하고 재시도 시 불필요한 AI 재호출·중복 메시지를 막는다. 클라이언트가 임의 AI 답변·출처를 공식 응답으로 저장하지 못하게 한다.
- **산출/연결:** PRD의 대화 생성·목록·상세·삭제 API. 삭제는 하위 메시지까지 처리한다. 대화에 표시된 출처가 나중에 삭제되었으면 현재 상태를 함께 보여준다.
- **완료/검증:** 응답 저장 중 실패·응답 유실·같은 request_id 재전송·대화 삭제·다른 모드/소유자 조회를 검사한다. A17 대화 범위에 대응한다.
- **착수 전 결정(2026-10-02, `docs/decisions.md`):** `conversations` 문서의 `messages[]` 유지(삭제 시 메시지 함께 원자적 삭제), 덧붙이기는 트랜잭션·같은 메시지 ID 재저장 무시, 저장 실패 시 검증된 질문·답을 `chat_pending`에 보관하고 503 `save_failed`(답 본문·`pending_id`) — 같은 키 재전송은 재생, 재저장은 `POST /api/conversations {pending_id}`(클라이언트 답·출처 입력 불가, 원래 대화가 없으면 새 대화), 목록은 생성 최신순 + 저장 대기 답변(새 복합 색인 배포), 상세는 출처마다 `current_status`, 삭제는 대화·대기 답변·요청 기록의 응답 본문 가림.

### T07.04 채팅 화면과 검색 품질 평가

- **파일:** 생성 `web/js/views/ask.js`, `web/js/views/conversations.js`, `server/tests/test_chat_evaluation.py`; 수정 평가 결과 문서.
- **작업:** 질문·로딩·근거 카드·숫자 출처·새 대화·기록 불러오기·삭제를 연결한다. 채팅 화면에는 현재 모드의 기본 Summary(기간·개수·합계·평균·최소·최대·추세, 출처 표시)를 항상 보이게 하고, 질문이 다른 지표·기간·출처를 선택하면 답변에 사용한 별도 Summary의 조건도 표시한다(PRD S05, 과제 제출 화면 `데이터 요약이 보이는 채팅 화면`). 표본 10개 정답 질문과 3개 무근거 질문의 입력 자료·질문·정답 ID를 고정한다. 품질 평가는 실제 `search_materials`를 실행하여 찾은 자료를 채점하며, Provider 응답만 가짜로 대체해 테스트를 재현한다. 실제 AI 답변 검증 결과는 따로 기록한다.
- **산출/연결:** S05 채팅·요약 패널, S06, 평가 질문별 기대 자료/실제 자료/실패 원인.
- **완료/검증:** 고정 입력 자료에서 실제 검색 결과를 채점해 정답 질문 10개 중 8개 이상에서 기대 자료를 찾고, 무근거 질문 3개에서 한계를 표시하며 존재하지 않는 출처 ID는 0건이어야 한다. `표본 CRUD → Summary → 같은 질문 답변 변화`와 `개인 자료 보관/휴지통 → 실제 보관 수 변화`를 확인한다. 기본 요약 패널과 질문별 요약의 출처·기간·지표가 구분되는지도 검사한다. A14·A24에 대응한다.
- **착수 전 결정(2026-10-03, `docs/decisions.md`):** 평가는 실제 채팅 경로(검색 모듈 순위·자격 필터·출처 대조)에 가짜 Provider(받은 자료 전부 + 없는 번호 99 인용)로 채점하고 `search_materials` 핵심어 결과를 함께 표기, 결과는 `docs/chat-evaluation.md`, 실제 AI는 3문항(q01·q10·n03)만 따로 기록, 응답 `numbers`에 `role: default|question`, 화면은 S05(기본 요약 패널·답변 카드·저장 실패 시 다시 저장)·S06(목록·열기·삭제 확인·저장 대기 답변).

## Phase 08. MVP 통합 검증과 배포

**범위:** MVP 완료. **선행:** Phase 01~07. **종료 조건:** 아래 MVP 인수 기준을 실제 서비스에서 확인하고 다음 세션/다른 PC에서 README로 재현할 수 있다.

### T08.01 MVP 인수 기준과 보안·실패 흐름 검증

- **파일:** 생성 `server/tests/test_mvp_flow.py`; 수정 `docs/verification.md`.
- **작업:** URL 접수→분석 동의→검토→보관→검색→질문→대화 복원→휴지통→복원→영구 삭제 흐름을 확인한다. 숫자 CRUD/요약 시연은 표본 모드에서 수행한다. 인증 우회, 모드 혼합, 오래된 승인, 분석 제외 우회, 입력 HTML 실행을 검사한다.
- **완료/검증:** `python -m pytest server/tests -q` 결과와 A01·A02·A13·A14·A15·A16(웹)·A17(웹)·A18·A19·A23·A24·A25·A26의 증거를 남긴다. A25는 실제 호출 증거가 필요하다. UI 및 배포 항목은 T08.03까지 완료된 뒤 최종 통과로 표시한다.

### T08.02 Render API·Vercel 웹 배포

- **파일:** 생성 `render.yaml`, `web/vercel.json`, `docs/deployment.md`, `server/app/hermes_relay.py`, `server/scripts/run_hermes_relay.py`; 수정 T02.03에서 만든 `web/scripts/build-config.mjs`, 서버 CORS 설정, Provider 연결 설정.
- **작업:** 배포 전 실제 호스팅 설정과 과금 여부를 확인한다. 저장소 루트가 `ia-codyssey`이므로 Vercel Root Directory는 `assignments/M1-2/web`, Render Root Directory는 `assignments/M1-2/server`로 지정하고 `vercel.json`은 지정한 Vercel 프로젝트 루트인 `web/` 안에 둔다. Render Blueprint가 하위 폴더의 `render.yaml`을 읽을 수 있는지 확인하고, 불가하면 대시보드 설정으로 대신하고 그 절차를 `docs/deployment.md`에 기록한다. Render에 비밀 설정, Vercel에 공개 API 주소·공개 인증 설정을 구분한다. 빌드 시 공개 값만 `web/js/config.js`로 생성하며 브라우저가 서버 환경변수를 읽는다고 가정하지 않는다. 허용 Origin을 실제 도메인으로 제한한다.
- **Hermes 배포 선행 조건:** 로컬 `127.0.0.1:8642`는 Render에서 접근할 수 없다. 선택한 외부 경로는 Tailscale Funnel이다. Funnel에는 Hermes 포트가 아니라 별도 loopback 중계 서버(`127.0.0.1:8766`)를 연결하고, 전용 Bearer 토큰과 두 경로 allowlist를 적용한다. PC·Hermes·Tailscale이 켜져 있어야 동작한다. Render에서 실제 호출을 확인하기 전에는 배포 완료로 체크하지 않는다.
- **현재 확인:** `docs/deployment.md`에 Funnel 경로와 비밀 설정·운영 순서를 기록했다. 중계 서버 로컬 구현·검증을 통과했고 공개 HTTPS에서 무인증 401을 확인했다. Render 왕복은 미검증이다.
- **산출/연결:** 실제 웹 주소·API 주소·Swagger 주소, 배포 재현 절차. 기본 경로와 정적 파일 경로를 배포 설정에 맞춘다.
- **완료/검증:** HTTPS 웹에서 인증된 API와 Swagger가 동작하고 잘못된 Origin 요청을 허용하지 않는지 확인한다. 접근권한/설정이 없어 배포하지 못하면 배포 미완료로 기록한다. A17에 대응한다.

### T08.03 실제 배포 환경과 모바일 시연 검증

- **파일:** 수정 `docs/verification.md`; 생성 `docs/evidence/` 안의 필요한 시연 화면.
- **작업:** 실제 배포 주소에서 로그인·모드 전환·URL-only·묶음 검토·숫자 CRUD·채팅·대화 복원·휴지통을 시연한다. 커밋할 `docs/evidence/` 화면은 **표본 모드로 캡처**하고 개인 자료 제목·URL·계정 정보가 보이지 않는지 확인한다. 모바일 메뉴·긴 답변·키보드 입력·오류 메시지를 확인한다. 서버 콜드스타트와 연결 실패 시 재시도가 중복 등록/호출을 만들지 않는지 확인한다.
- **완료/검증:** 화면에 목업의 가짜 연결 상태나 읽지 않은 자막/본문 설명이 남아 있지 않다. S08·S09는 확장 예정 표시다. 실제 배포 검증 전 로컬 통과만으로 A17·A24 전체를 체크하지 않는다.

### T08.04 README·제출 화면·MVP 완료 기록

- **파일:** 수정 `README.md`, `docs/verification.md`, `task.md`.
- **작업:** 서비스 소개·구조·설치/실행·환경변수·표본 생성·배포 주소·휴지통·현재 한계를 README에 작성한다. 과제 요구 API와 구현 위치·Swagger·시연 화면을 대응시킨다. `/api/chat`의 컨텍스트 주입 흐름(요약 조회 → system 메시지 삽입 → GPT 호출 → 대화 자동 저장)과 실제 system 메시지 구조 예시(키·개인 자료 제외)를 README에 설명한다. `git ls-files`로 실제 키/서비스 계정 원본이 추적되지 않는지 확인한다.
- **완료/검증:** README만 따라 새로운 환경에서 서버/웹을 실행할 수 있고 제출 시연 자료를 찾을 수 있다. Phase 01~08과 MVP 인수 기준이 완료됐을 때만 `MVP 완료`로 기록한다. PC 정리 기능은 확장 단계로 표시한다.

## Phase 09. Windows 연결과 파일 분석

**범위:** 확장 단계. **선행:** Phase 08 완료. **종료 조건:** 허용 폴더를 수동 확인하고 다섯 파일 그룹의 확인 범위·분류·검토 상태를 보여준다. 이 Phase만으로 실제 파일 삭제를 허용하지 않는다.

### T09.01 장치 연결·인증·허용 폴더 등록

- **파일:** 생성 `connector/requirements.txt`, `connector/app/main.py`, `connector/app/auth.py`, `connector/app/roots.py`, `server/app/features/devices/routes.py`, `server/app/features/devices/service.py`, `connector/tests/test_device_auth.py`.
- **작업:** 일회용 짧은 연결 코드로 Windows PC 한 대를 연결한다. 자격증명은 OS 보안 저장소에 두고 해제 시 폐기한다. 로컬에서 읽기 폴더·쓰기 폴더·하위 폴더 포함 여부와 폴더별 `AI 분석 제외`를 등록한다. 제외 폴더의 파일은 기본적으로 메타데이터만 확인하도록 설정을 보존한다. HTTPS로 작업을 가져오고 PC에 공개 수신 포트를 열지 않는다.
- **산출/연결:** 장치 ID·허용 root ID·연결 상태. 장치 API는 이 Task의 개념 검증 결과로 `docs/api-contract.md`에 확정한다. Firebase 관리자 키·공용 AI 키를 연결 프로그램에 넣지 않는다.
- **완료/검증:** 연결 코드 재사용·만료, 연결 해제, 다른 장치 위장, 웹에서 임의 폴더 권한 추가를 거부한다. 폴더별 제외 설정을 재연결 후에도 읽을 수 있어야 한다. 60초 무응답은 초기 가설인 `연결 확인 필요`로 표시하고 원인을 단정하지 않는다. A08·A16 확장 범위에 대응한다.

### T09.02 수동 폴더 확인·파일 식별·상태 보고

- **파일:** 생성 `connector/app/scan.py`, `connector/app/file_identity.py`, `server/app/features/scans/routes.py`, `server/app/features/scans/service.py`, `connector/tests/test_scan.py`.
- **작업:** 버튼 요청으로만 스캔한다. 파일명·확장자·크기·mtime·해시·파일 버전·허용 root 내 상대 경로를 저장한다. 다운로드 중·잠김·권한 부족을 건너뛰고 이유를 표시한다. 같은 파일/버전은 갱신하며 변경·식별 불확실성을 숨기지 않는다. 폴더별 제외 설정을 파일에 상속하고 개별 파일의 `AI 분석 제외` 선택을 내용 추출 전에 저장한다. 폴더 제외를 파일별로 해제하려면 사용자의 명시적 변경을 요구한다.
- **산출/연결:** `/api/scans` 요청/상태 API와 자료에 연결할 파일 목록·파일별 유효 제외 상태. 목록 200개·분석 묶음 20개는 조정 가능한 초깃값으로 둔다.
- **완료/검증:** 같은 폴더 재확인으로 자료·AI 호출이 증가하지 않고 명시적 버튼 없이 감시가 시작되지 않아야 한다. 접합점·심볼릭 링크를 통한 허용 범위 이탈을 거부한다. 폴더/파일의 제외 상태가 내용 처리보다 먼저 확정되고 반복 확인에도 유지되는지 검증한다. A03·A21 준비에 대응한다.

### T09.03 PDF·Office·텍스트·설치/압축 형식 처리

- **파일:** 생성 `connector/app/parsers/pdf.py`, `office.py`, `text.py`, `metadata.py`, `connector/tests/test_parsers.py`.
- **작업:** 파일별 유효 `AI 분석 제외` 상태를 먼저 확인하고 제외 대상은 메타데이터만 읽는다. 허용된 파일은 실제 표본으로 라이브러리를 선택하고 검증된 버전을 기록한다. DOCX 본문/표, PPTX 텍스트/노트, XLSX 시트/셀/수식 문자열/저장 결과, PDF 텍스트, TXT/Markdown/코드를 처리한다. EXE/MSI/ZIP/7Z는 메타데이터만 읽는다. 실행·매크로·압축 해제·수식 재계산을 하지 않는다.
- **산출/연결:** 추출 텍스트·페이지/시트/범위·부분 확인/변환 필요/암호/인코딩/한도 상태. 20MB·PDF 20쪽·슬라이드 30장·Excel 5시트×200행×20열·총 20,000자 한도를 설정으로 관리한다.
- **완료/검증:** 정상·암호·손상·구형 DOC/PPT/XLS·한도 초과·인코딩 실패 표본에서 실제 확인 범위를 표시한다. 제외 대상에서 본문 추출과 AI 전송용 임시 파일 생성이 발생하지 않는지 확인한다. DOC/PPT/XLS 완전 지원을 검증 전 주장하지 않는다. A04·A05·A21에 대응한다.

### T09.04 이미지·스캔 PDF와 OCR 대체 경로 검증

- **파일:** 생성 `connector/app/parsers/images.py`, `connector/app/parsers/ocr.py`, `connector/tests/test_image_scope.py`; 수정 분석 Adapter·검증 기록.
- **작업:** T09.01~02의 폴더·파일별 유효 `AI 분석 제외` 상태를 이미지 읽기·OCR·임시 업로드·Provider 전송 전에 다시 검사하고 제외 대상은 메타데이터만 확인한다. 허용 대상에 한해 Provider 이미지 입력 가능 여부를 실제로 확인한다. 지원하면 승인 범위의 이미지 요청을 검증하고, 미지원이면 로컬 OCR 텍스트만 전송하는 경로를 검증한다. 이 경우 `텍스트만 분석 · 화면 구성 미분석`을 표시한다. 흐림·가림·판독 실패는 판단 보류/부분 확인으로 남긴다.
- **산출/연결:** 이미지·스캔 PDF의 분석 범위와 A27 증거. 전체 OCR을 Render 무료 인스턴스가 수행한다고 가정하지 않는다.
- **완료/검증:** OCR과 이미지 경로에서 실제 전송 데이터를 확인한다. AI 분석 제외 이미지가 임시 업로드에도 포함되지 않아야 한다. 지원 이미지 또는 대체 경로의 실제 성공 증거로 A27을 판정한다. A04·A05·A21에도 대응한다.

### T09.05 스크린샷·Downloads 분류와 검토 화면

- **파일:** 생성 `web/js/views/screenshots.js`, `web/js/views/downloads.js`, `server/app/features/files/proposals.py`, `server/tests/test_file_proposals.py`.
- **작업:** 스크린샷은 작업용/정보성/판단 보류로 분류하고 작업 종료·일부 선택을 자료 ID·버전에 결합한다. Downloads는 이름 정리/프로젝트 이동/참고자료/중복/임시/판단 보류로 제안한다. 정확한 해시 중복과 내용 유사도를 구분한다. T09.01~02에서 저장한 폴더별·파일별 `AI 분석 제외` 상태를 화면에 표시하고 변경한다. 변경 후에는 다음 내용 처리/전송 전 유효 상태를 다시 계산한다.
- **산출/연결:** Phase 10 승인에 필요한 수정된 이름·목적지·선택 파일·종료 확인. Open Decision 3의 모바일 썸네일 선택을 반영하고 현재 파일 수와 행동 수를 구분한다.
- **완료/검증:** `아직 작업 중`·제외 파일은 삭제 승인 대상이 아니고 내용 미확인 파일에 지어낸 이름을 제안하지 않는다. 폴더 분석 제외를 파일 설정이 자동 해제하지 않는다. A21·A22에 대응한다.

## Phase 10. 승인된 파일 정리와 연결 삭제

**범위:** 확장 단계 완료. **선행:** Phase 09. **종료 조건:** 실제 파일 변경·원본 사본·연동 삭제·부분 실패 복구를 전용 표본으로 검증하고 확장 인수 기준을 통과한다.

### T10.01 작업 승인·영속 큐·실행 임대·취소

- **파일:** 생성 `server/app/features/operations/routes.py`, `server/app/features/operations/service.py`, `connector/app/worker.py`, `connector/app/journal.py`, `server/tests/test_operations.py`.
- **작업:** 승인 스냅샷에 사용자·시간·파일 ID/버전/해시·동작·이전/새 경로·제안 버전을 기록한다. 서버 영속 큐와 PC 로컬 실행 기록, claim/report·임대를 사용한다. 202/작업 ID는 접수로 표시한다. 시작 전 취소, 오프라인, 승인 만료를 구분한다.
- **산출/연결:** 검증된 구조화 작업만 실행하는 worker. AI 출력의 명령 문자열을 shell/PowerShell에 넘기지 않는다. 승인 후 연결이 끊긴 미시작 작업의 10분 만료는 초기 가설로 검증한다.
- **완료/검증:** 무승인·오래된 버전·해제 장치·중복 claim·응답 유실·취소 후 실행을 거부한다. 상태 조회/재시도 API가 성공 단계를 다시 실행하지 않아야 한다. A08·A11·A16 확장 범위에 대응한다.

### T10.02 이름 변경·이동·새 폴더·되돌리기

- **파일:** 생성 `connector/app/operations/rename_move.py`, `connector/app/path_policy.py`, `connector/tests/test_rename_move.py`; 수정 작업 내역 화면.
- **작업:** 확장자·Windows 예약 이름/금지 문자/경로 길이·등록한 쓰기 root를 검증한다. 실경로를 확인해 링크 우회를 차단하고 대상 파일을 덮어쓰지 않는다. 다른 볼륨은 복사 후 크기/해시 검증이 끝나야 원본을 제거한다. 새 폴더 생성도 승인된 목적지 안에서만 수행한다.
- **산출/연결:** 이전 이름/경로·완료 직후 버전·결과 기록. 되돌리기는 새 역방향 승인 작업이며 현재 상태·경로·충돌을 다시 확인한다. 내용이 같고 경로만 바뀌면 기존 자료/사본 연결을 유지한다.
- **완료/검증:** 실제 테스트 파일로 동명 충돌·허용 밖 경로·복사 검증 실패·승인 후 변경·역방향 충돌을 확인한다. 원본 손상이나 무승인 변경은 출시 차단이다. A06·A07·A08·A20에 대응한다.

### T10.03 승인 원본 사본 보관과 인증 다운로드

- **파일:** 생성 `server/app/features/artifacts/routes.py`, `server/app/features/artifacts/service.py`, `connector/app/upload.py`, `server/tests/test_artifacts.py`.
- **작업:** Storage 요금제·지역·예상 용량/전송량을 실제 확인하고 설정한다. 보관 승인 후에만 지속 사본을 업로드하고 버전·크기·해시를 대조한다. 100MB 사본 한도와 20MB 분석 한도를 구분한다. 임시 분석 파일과 지속 사본을 구분하고 고아 임시 파일 정리를 검증한다.
- **산출/연결:** artifact ID와 자료/파일 버전 연결, 업로드 대기/실패/완료 상태. 소유권·활성·보관 완료를 확인한 원본 다운로드 API. 공개 영구 URL을 만들지 않는다.
- **완료/검증:** 승인 전 지속 사본 없음, 업로드 실패 시 보관 완료 아님, PC를 끈 상태의 다운로드, 휴지통/다른 소유자 다운로드 차단을 확인한다. A09에 대응한다.

### T10.04 Windows 휴지통과 클라우드 연결 삭제

- **파일:** 생성 `connector/app/operations/recycle.py`, `server/app/features/operations/delete_flow.py`, `connector/tests/test_recycle.py`, `server/tests/test_linked_delete.py`.
- **작업:** 사본 없음은 경고 후 PC만 휴지통, 업로드 대기/중은 완료 또는 취소 확정 전 차단, 업로드 실패는 임시 조각 정리 후 경고, 완료 사본은 연결 삭제로 처리한다. 서버 삭제 진행→PC 버전 재확인/휴지통→클라우드 휴지통 확정 순서를 지킨다.
- **산출/연결:** PC/클라우드 단계별 결과와 검색 제외 상태. 사본이 있는 경우 PC만 삭제하고 사본을 남기는 선택은 제공하지 않는다. 다른 이름/해시 유사 자료는 연결 ID가 다르면 영향받지 않는다.
- **완료/검증:** 실제 Windows 휴지통 복원 가능성을 확인한다. 휴지통 실패를 영구 삭제로 대체하지 않는다. 연결 사본 유무·업로드 상태별 승인 문구와 결과를 검증한다. A06·A10에 대응한다.

### T10.05 부분 실패·재시작·복원·영구 삭제

- **파일:** 생성 `server/app/features/operations/reconcile.py`, `server/tests/test_operation_recovery.py`, `connector/tests/test_restart_recovery.py`; 수정 휴지통 서비스·작업 내역 화면.
- **작업:** PC 성공/서버 실패는 서버 단계만 재시도하고 PC 실패 확정은 동시 변경을 확인한 뒤 이전 클라우드 상태로 복구한다. PC 결과 불명은 삭제 진행을 유지하고 실행 기록을 대조한다. 연결 복원은 클라우드와 PC를 각각 안내하고 PC 복원으로 클라우드를 자동 복원하지 않는다.
- **산출/연결:** 실패 단계별 복구 경로, 재시작 후 대조 결과, 파일 사본 영구 삭제 절차. 영구 삭제는 원본 객체·추출/검색 데이터·접수 기록 제거를 모두 확인한다.
- **완료/검증:** 응답 유실·서버/PC 재시작·중복 요청·부분 배치 실패·원본 객체 제거 실패를 재현한다. 재시도로 파일이 두 번 이동/삭제되지 않고 불명 상태가 성공으로 바뀌지 않아야 한다. A11·A12에 대응한다.

### T10.06 확장 단계 인수 검증·설치 안내·완료 기록

- **파일:** 수정 `README.md`, `docs/deployment.md`, `docs/verification.md`, `task.md`; 생성 `connector/README.md`, `connector/packaging/`의 설치 패키지 구성 파일.
- **작업:** 연결 프로그램의 실행 방식에 맞는 Windows 설치 패키지(EXE 또는 MSI)를 생성한다. Windows 설치/연결/해제/실행, 허용 폴더, 형식별 한계, PC/클라우드 휴지통 차이, 되돌리기, 실패 복구를 문서화한다. 모바일에서 켜진 PC의 테스트 파일을 검토·승인·실행한다. 표본 모드에서 실제 PC 변경이 발생하지 않는지도 확인한다.
- **완료/검증:** 새 Windows 환경에서 Python 개발 환경을 수동으로 설치하지 않고 패키지를 설치·실행·연결한 뒤 제거한다. 제거·연결 해제 뒤 장치 자격증명이 폐기되는지 확인한다. A03~A12·A20~A22·A27과 A16·A17의 확장 범위를 검증한다. MVP의 인증·검색·채팅·웹 휴지통을 영향 범위에 맞춰 다시 확인한다. 모두 통과한 뒤 Phase 09~10과 확장 완료를 체크한다. 설치나 OCR이 검증되지 않았으면 해당 한계를 명시하고 전체 완료로 표시하지 않는다.

## 4. 인수 기준과 Task 대응표

| PRD 기준 | 단계 | 구현·검증 Task |
|---|---|---|
| A01 URL-only 상태 | MVP | T03.01, T08.01 |
| A02 분석 시작·일괄 검토·사용자 중요도 유지 | MVP | T03.03, T04.01~04, T08.01 |
| A03 수동 확인·중복 방지 | 확장 | T09.02 |
| A04 파일 형식 분석 | 확장 | T09.03~04 |
| A05 불완전 파일과 확인 범위 | 확장 | T09.03~04 |
| A06 모바일 승인·실제 파일 변경 | 확장 | T10.02, T10.04, T10.06 |
| A07 새 폴더·충돌 방지 | 확장 | T10.02 |
| A08 무승인·경로·버전·해제 장치 차단 | 확장 | T09.01, T10.01~02 |
| A09 승인 사본·오프라인 다운로드 | 확장 | T10.03 |
| A10 사본 상태별 연결 삭제 | 확장 | T10.04 |
| A11 부분 실패·재시작·중복 방지 | 확장 | T10.01, T10.05 |
| A12 PC/클라우드 복원·사본 영구 삭제 | 확장 | T10.05 |
| A13 부적격 자료의 AI 문맥 제외 | MVP/파일 확장 | T05.04, T07.01, T08.01, T10.06 |
| A14 검색 품질·근거 부족·출처 검증 | MVP | T07.02, T07.04 |
| A15 100건 숫자 CRUD·독립 집계 검증 | MVP | T06.01~04, T08.01 |
| A16 인증·장치 상태·승인 만료 | MVP/확장 | T02.01, T09.01, T10.01 |
| A17 배포·대화·재현 안내 | MVP/확장 | T07.03, T08.02~04, T10.06 |
| A18 같은 URL 선택 | MVP | T03.02 |
| A19 관련 자료·사용자 연결 | MVP | T05.02 |
| A20 이름 변경/이동 되돌리기 | 확장 | T10.02 |
| A21 분석 제외 전송 금지 | 파일 검증은 확장, 웹 원칙은 MVP부터 적용 | T03.04, T05.04, T09.01~05 |
| A22 스크린샷 작업 종료·일부 선택 | 확장 | T09.05, T10.01 |
| A23 실제 AI 요청량·한도 대기 | MVP | T04.03 |
| A24 과제 API·표본 CRUD→요약→답변·모바일 | MVP | T06.04, T07.04, T08.01~04 |
| A25 GPT 텍스트 SDK 스모크 테스트 | MVP | T01.04 (T01.03은 과거 Codyssey 기록) |
| A26 웹 휴지통·복원·영구 삭제 | MVP | T05.03, T06.02, T08.01 |
| A27 이미지 입력 또는 OCR 대체 경로 | 확장 | T09.04 |

## 5. 세션 종료 기록과 다음 시작점

2026-10-01 AI 경로 변경: T01.04에서 Hermes 로컬 API의 `openai-codex` / `gpt-6-luna` 텍스트 응답을 확인하고 서버 `.env`를 전환했다. T04.01의 Adapter에는 텍스트 호출과 도구 비활성 검사만 먼저 들어갔다. 자료 분석·채팅 기능은 아직 구현되지 않았다. 원격 Hermes 배포 경로도 미검증이므로 T08.02 완료 조건으로 남는다. 과거 T01.03 Codyssey 성공 기록은 이력으로 유지한다.

2026-10-01 원격 Hermes 연결: 사용자가 Tailscale Funnel을 선택했다. Funnel 공개 대상은 Hermes 포트가 아니라 전용 인증 중계 서버로 제한한다. 로컬 relay(`127.0.0.1:8766`)로 도구 세트 비활성(29개), 잘못된 토큰 401, 경로·쿼리 거부, 합성 텍스트 응답(`gpt-6-luna`, 1,023토큰)을 확인했다. 공개 HTTPS 443의 로컬 중계 연결과 무인증 요청 401도 확인했다. 상세는 `docs/verification.md`. Render 원격 경로는 미검증이다. 설계와 계획은 `docs/superpowers/specs/2026-10-01-tailscale-funnel-hermes-relay-design.md`, `docs/superpowers/plans/2026-10-01-tailscale-funnel-hermes-relay.md`에 있다.

Phase 01(T01.01~T01.04)과 Phase 02(T02.01~T02.04)를 완료했다. Firestore는 실제 프로젝트에서 저장소·중복 요청·규칙/색인 배포·클라이언트 직접 접근 거부(REST·웹 SDK)까지 검증했고, 프로젝트·설정 API와 설정 화면은 `docs/verification.md`에 기록했다. T03.01 자료 API와 화면도 검증했다. 배포·Windows 파일 작업은 아직 검증하지 않았다. T02.04의 동시 프로젝트 생성과 기본 프로젝트 해제는 실제 Firestore와 메모리 저장소에서 확인했고, 동시 이름 변경은 메모리 저장소 회귀 테스트로 검증했다.

| 항목 | 현재 기록 |
|---|---|
| 마지막 완료 Task | T07.04 — S05 채팅·요약 패널, S06 대화 기록, 검색 품질 평가 10/10·3/3·없는 출처 0건, 실제 AI 3문항(과거 대화 형식 문제 수정) |
| 다음 Task | T08.01 — MVP 인수 기준과 보안·실패 흐름 검증 |
| 작업 기준 | PRD v1.11 / `m1-2` 브랜치. 초기 기준 커밋 `c324ede9`, T01.01·T01.02 `424961b8`, T01.03 준비 `94af8d50` |
| 검증 보완 파일 | `server/scripts/smoke_ai.py`, `server/tests/test_smoke_ai.py`, `docs/verification.md` |
| 실제 실행 결과 | T01.02: Python 3.11.9, `pytest server/tests -q` 7 passed, `/health`·`/docs` HTTP 200, 비밀값 미노출·Git 제외 확인. T01.03: Codyssey `gpt-5-mini` 실제 호출 성공, 응답 모델 `gpt-5-mini`, OpenAI SDK `3.22.1`, 비어 있지 않은 텍스트 응답, `finish_reason=stop`. Phase 01 연결 검증 보충에서 `max_completion_tokens=1500` 호출도 성공했고 usage는 `completion=74`, `prompt=14`, `total=88`이었다. 서버 `.env`는 Codyssey로 전환했고 Hermes는 `.env.hermes`로 보존했다. `finish_reason=stop` 성공 판정과 잘린 응답 실패 판정을 모의 응답으로 검증했다. T02.01: `pytest server/tests -q` 27 passed(401 6종·인증 전 모드 확인 안 함·403·OWNER_UID 누락 503·422 4종·소유자 통과·Firebase 미설정 503·서비스 계정 내용 미노출), 실제 서버에서 토큰 없음 401·Firebase 미설정 시 503 확인. 실제 Google 로그인 후 `/api/me` 200·로그아웃 후 401 확인(`docs/verification.md`). 리뷰 보완: 인증서 조회 실패 503, `apiFetch` 모드 필수 |
| 결정 확인이 필요한 항목 | Open Decisions 1·2는 해당 입력/저장 구조 확정 전에 확인. 3은 확장 단계, 4·5는 보수적인 기존 규칙 적용 |
| 외부 준비 확인 | T01.02~03에서 Python 환경과 실제 AI 설정, T02.01~02에서 Firebase 프로젝트·인증 접근 가능 여부 확인 |

다음 세션 시작 순서:

1. 실제 작업 경로·브랜치·`git status`·최신 PRD 버전을 확인한다.
2. 상단에서 선택한 Task와 관련 PRD 절, 이 문서의 공통 계약을 읽는다.
3. 기존 파일과 최근 변경을 확인하고 그 Task의 구현 및 필요한 검증을 진행한다.
4. 실제 결과를 `docs/verification.md`에 기록하고 완료 조건을 충족한 Task만 체크한다.
5. 위 세션 기록을 마지막 완료/다음 Task·변경 파일·검증 결과·남은 결정으로 갱신한다. 커밋했다면 해시를 적고, 커밋하지 않았다면 변경 상태를 그대로 적는다.

사용할 지시 예시: **“task.md의 T01.01부터 진행해 줘. 완료한 Task를 체크하고 다음 세션 기록도 갱신해 줘.”**
