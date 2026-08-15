# LAPIS 향 큐레이터

기분과 상황을 입력하면 어울리는 향의 3층 구성(Top / Heart / Base)과 브랜드 톤의 카피를 생성하는 AI 큐레이션 웹 서비스.

**배포 URL**: https://lapis-curator.vercel.app

---

## 서비스 소개

LAPIS는 프리미엄 오 드 퍼퓸 브랜드다. 향수는 맡아보기 전에는 고르기 어려운데, 온라인에서는 그 시도조차 할 수 없다. 이 서비스는 방문자가 자기 언어로 향을 탐색해 볼 수 있는 AI 큐레이터를 브랜드 원페이지에 더한 것이다.

전체 기획은 [서비스기획서](docs/서비스기획서.md) 참고.

## 페이지 구성

7개 섹션의 원페이지. 상단 내비게이션·모바일 메뉴·푸터에서 각 섹션 앵커로 이동한다.

| # | 섹션 | 내용 |
|---|---|---|
| 01 | Hero | 브랜드명, 태그라인, CTA |
| 02 | Brand Story | 브랜드 서사 + 아코디언 |
| 03 | Notes | Top / Heart / Base 3카드 |
| 04 | **Curator** | **AI 향 큐레이션** |
| 05 | Collection | LAPIS / LUNA 라인업 |
| 06 | Philosophy | 헤리티지·장인정신·지속가능성 |
| 07 | Contact | 뉴스레터 구독 + 푸터 |

## 기술 스택

| 영역 | 사용 |
|---|---|
| 프론트엔드 | 바닐라 HTML / CSS / JavaScript (프레임워크 없음) |
| 백엔드 | Vercel Serverless Functions (Python) |
| AI | Google Gemini (`google-genai`) |
| 테스트 | pytest |
| 스크린샷 | Playwright (`playwright-core` + 시스템 Edge) |
| 배포 | Vercel |

## 프로젝트 구조

```text
.
├── index.html          # 7섹션 마크업
├── css/
│   ├── tokens.css      # 디자인 토큰
│   └── style.css       # 섹션 스타일
├── js/
│   ├── main.js         # 내비게이션, 스크롤 리빌, 기존 인터랙션
│   └── curator.js      # 큐레이터 — 검증, fetch, 상태 전환, 렌더
├── api/
│   └── curate.py       # 서버리스 함수 (검증 · 재시도 · Gemini 호출)
├── images/             # WebP 자산
│   └── shots/          # 제출 증빙 스크린샷
├── scripts/            # 이미지 변환, 스크린샷 캡처
├── tests/              # 단위 테스트
├── docs/서비스기획서.md
├── requirements.txt        # 배포용
├── requirements-dev.txt    # 테스트용
├── vercel.json
└── .vercelignore
```

## 환경 변수 설정

이 서비스는 API 키를 **환경 변수에서만** 읽는다. 코드에 키를 직접 쓰지 않는다.

| 이름 | 발급처 |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio → API 키 만들기 |

### 로컬

```bash
cp .env.example .env
```

`.env` 에 발급받은 값을 넣는다. `.env*` 는 `.gitignore` 에 등록되어 있다.

```env
GEMINI_API_KEY=발급받은_키
```

커밋 전에 실제로 제외되는지 확인한다.

```bash
git status --ignored
```

결과의 Ignored files 목록에 `.env` 가 있어야 한다.

### 배포

Vercel 프로젝트 Settings → Environment Variables 에 등록한다. CLI로는 환경을 하나씩 지정한다.

```bash
vercel env add GEMINI_API_KEY production
```

**Production · Preview 모두에 등록해야 한다.** Production만 넣으면 브랜치 push로 생기는 Preview 배포에서 AI 기능이 `SERVICE_UNAVAILABLE` 로 죽는다.

> **로컬 `.env` 파일은 배포에 아무 영향이 없다.** 그 파일은 내 컴퓨터에서 실행할 때만 읽히고, 배포된 함수는 Vercel이 주입하는 환경 변수만 본다. 저장소에 키를 올리지 않으면서 배포 환경에도 값을 전달하려면 두 곳에 각각 설정해야 한다.

> **주의**: 화면 캡처에 `.env` 파일을 띄우지 않는다. 값을 색으로 덮어도 편집기의 미니맵·탭 미리보기에 축소 렌더링되어 남을 수 있다. 실수로 키를 커밋했다면 파일을 지워도 커밋 기록에 남으므로, 발급처에서 즉시 폐기하고 재발급한다.

## 실행 방법

### 테스트

```bash
python -m venv .venv
```

Windows PowerShell 은 `.\.venv\Scripts\Activate.ps1`, macOS · Linux 는 `source .venv/bin/activate` 로 활성화한다.

```bash
pip install -r requirements-dev.txt
```

```bash
pytest tests/ -v
```

40개 테스트가 Gemini 호출 없이 돈다. 검증·재시도·백오프 로직이 모델 상태와 무관하게 검증된다 — 이 서비스가 부르는 모델은 실제로 503을 자주 돌려준다.

### 스크린샷 캡처

```bash
npm install
```

```bash
node scripts/capture.cjs https://lapis-curator.vercel.app
```

`images/shots/` 에 18장이 저장된다 (1440px·375px 각 7섹션 + AI 동작 4단계).

### 이미지 변환 (자산을 새로 추가할 때만)

```bash
python scripts/convert_images.py
```

## AI 기능 동작 방식

```text
[칩 3개 선택 + 자유입력 1줄]
        │  curator.js — 빈 입력이면 요청을 보내지 않고 즉시 안내
        ▼
POST /api/curate   { season, time, mood, moment }
        │  AbortController 30초
        ▼
api/curate.py  — 서버 재검증 → Gemini 호출 → 응답 스키마 검증
        │  실패 시 총 25초 예산 안에서 최대 3회 재시도
        │  2회차부터 빠른 대체 모델로 전환
        ▼
200 { name, name_kr, copy, notes{top,heart,base}, scene, attempts }
        ▼
curator.js — textContent로 렌더 (innerHTML 미사용)
```

### 실패 처리

| 상황 | 사용자에게 보이는 것 |
|---|---|
| 빈 입력 | 밑줄이 에러 색으로 바뀌고 인라인 안내. **요청을 보내지 않는다** |
| 대기 6초 / 15초 | 로딩 문구가 단계적으로 교체된다 |
| 모델 과부하 3회 실패 | 안내 + 다시 시도 버튼. 입력값은 보존된다 |
| 키 오류 | 안내만. **재시도 버튼을 보여주지 않는다** — 눌러도 결과가 같다 |

응답의 `attempts` 는 성공까지 걸린 시도 횟수다. 배포본의 실호출이 `attempts: 2` 로 돌아온다 — 1회차 기본 모델이 실패하고 2회차 대체 모델이 성공한 것으로, 재시도가 없었다면 그 요청은 실패했다.

### 시도당 데드라인 하한

Gemini는 10초 미만의 데드라인을 `400 INVALID_ARGUMENT` 로 거부한다.

```
Manually set deadline 8s is too short. Minimum allowed deadline is 10s.
```

400은 재시도 대상이 아니므로(우리 요청이 잘못됐다는 신호다), 상한을 이보다 낮게 잡으면 **재시도가 도는 대신 첫 호출부터 즉시 실패한다.** 남은 예산이 10초 미만이면 호출을 걸지 않고 종료한다. `tests/test_curate.py::test_never_requests_a_deadline_below_the_api_minimum` 이 이를 지킨다.

## 배포 설정

| 항목 | 값 |
|---|---|
| 연동 저장소 | `art-ruby/ia-codyssey` |
| 프로젝트 | `lapis-curator` |
| 함수 `maxDuration` | 30초 |

`vercel.json` 에서 `builds` 로 빌드 대상을 명시한다. 자동 감지에 맡기면 루트의 `requirements.txt` 때문에 Vercel이 이 프로젝트를 **Python 애플리케이션**으로 분류해 단일 진입점을 요구하고, 정적 파일 서빙이 깨진다.

`builds` 를 쓰면 zero-config의 확장자 제거 규칙이 적용되지 않아 함수가 `/api/curate.py` 로 노출된다. `routes` 로 `/api/curate` → `/api/curate.py` 를 매핑해 API 경로를 유지한다.

`.vercelignore` 로 `tests/`·`scripts/`·`docs/` 는 배포에서 제외한다.

## 라이선스 / 출처

브랜드 자산(디자인 시스템, 이미지, 카피)은 B1-2 과제에서 제작한 것을 재사용했다.
