# 결정 기록

## T01.01 확인 결과 — 2026-10-01

- 작업 경로: `C:\ia-codyssey-m1-2\assignments\M1-2`, 브랜치 `m1-2`, HEAD `465e6728`(= `origin/main`). 확인 시 작업 트리 변경 없음.
- PRD: v1.10, 기준 커밋 `c324ede9`.
- MVP 경계(PRD §3·§16): MVP = Milestone A(URL·텍스트 입력, 분석·검토·보관, 검색·채팅·대화, `data` CRUD·Summary, 웹 휴지통, 배포). 확장 단계 = Milestone B(PC 연결·파일 분석·실제 파일 정리·클라우드 사본·연동 삭제).
- 화면 키(PRD §5): `today`, `inbox`, `knowledge`, `trends`, `ask`, `conversations`, `review`, `screenshots`, `downloads`, `settings`.
- `task.md` Phase 01~08 대조: 파일 업로드·PC 작업은 제외 문구로만 등장하며 작업 항목으로 포함되지 않음.

## Open Decisions 결정 시점

| 항목 | 결정 시점 | 결정 전 기준 |
|---|---|---|
| 1. 한 자료와 여러 프로젝트의 관계 | T02.04 데이터 구조 확정 전 | 현재 주 프로젝트 표시 유지, 복수 관계 UI 미확정 |
| 2. 저장 이유와 메모 분리 | T03.01 입력 구조 확정 전 | 사용자 입력 보존, 저장 이유를 버리거나 합쳐 덮어쓰지 않음 |

## 과제 원문 위치

과제 원문은 `main`에 포함하지 않는다. `automaker` 브랜치의 `assignments/M1-2/m1-2.md`에서 읽는다(`git show automaker:assignments/M1-2/m1-2.md`). PRD만으로 새 과제 조건을 만들어내지 않는다.

## T02.01 인증 결정 — 2026-10-01

- 로그인: Firebase Authentication **Google 로그인**. 비밀번호 관리가 필요 없다.
- 응답 코드: 토큰 없음·무효 401, 인증됐지만 `OWNER_UID`가 아닌 계정 403. 다른 소유자 자료를 숨기는 404 검증은 T02.02로 옮긴다.
- 확인용 API: `GET /api/me`(PRD 외 추가, `docs/api-contract.md`에 기록).
- 범위: T02.01은 최소 로그인 페이지와 서버 인증, 웹 화면 통합은 T02.03.
- 로그아웃: 브라우저가 토큰을 보내지 않아 401이 되는지 검증한다. ID 토큰은 최대 1시간 유효하며 MVP는 토큰 폐기를 요구하지 않는다.
- 요청 헤더: `X-Data-Mode: personal|sample`(없거나 허용 밖이면 422), 중복 요청 식별 `Idempotency-Key`.
- 서비스 계정: `FIREBASE_SERVICE_ACCOUNT_JSON`에 JSON 문자열로 `.env`와 배포 환경변수에 넣는다.
- `OWNER_UID`: Firebase에서 Google 로그인을 켠 뒤 첫 로그인으로 UID를 확인해 설정한다. Spark 요금제 무료 한도로 Auth·Firestore를 시험한다.
