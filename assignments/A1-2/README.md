# 국내 여행지 추천 프로그램

여행 날짜와 일수를 입력하면 **Gemini가 국내 여행지 2곳을 추천**하고, **Kakao Local API로 각 지역의 맛집을 검색**한 뒤, **두 결과를 다시 Gemini에 전달해 최종 여행 리포트(Markdown)** 를 생성·저장하는 CLI 프로그램이다.

```text
-date 입력  →  [1/3] Gemini 추천 2곳(JSON)  →  [2/3] Kakao 맛집 검색(도시별 5곳)
            →  [3/3] Gemini 최종 리포트(Markdown)  →  results/ 저장
```

단일 API 호출이 아니라 **한 API의 출력을 다음 API의 입력으로 연결**하고, 서로 다른 API의 데이터를 결합해 새로운 결과물을 만드는 것이 이 프로그램의 핵심이다.

---

## 주요 기능

- **CLI 실행** — `argparse`로 여행 날짜(필수)와 여행 일수(선택)를 입력받는다
- **여행지 2곳 추천** — 서로 다른 매력을 가진 지역 2곳을 JSON으로 구조화해 받는다
- **일수별 일정 구성** — 당일(A안/B안 병렬 코스)과 1박 2일(DAY 1·DAY 2 연계 코스)의 일정 구성이 다르다
- **실제 맛집 데이터** — 맛집은 LLM이 지어내지 않고 Kakao Local 검색 결과만 사용한다
- **오류에 강한 실행** — 맛집 검색이 실패해도 "데이터 없음"으로 처리하고 리포트 생성을 계속한다
- **키 분리** — API 키는 코드에 넣지 않고 `.env`에서 읽는다

---

## 요구 사항

| 항목 | 버전 / 내용 |
|---|---|
| Python | 3.10 이상 (개발·검증: 3.11.9) |
| 실행 환경 | 터미널 (Windows PowerShell / macOS · Linux 셸) |
| LLM API | Google Gemini — `gemini-3.5-flash` |
| 장소 검색 API | Kakao Local — 키워드로 장소 검색 |

**의존 패키지** (`requirements.txt`)

```text
requests
python-dotenv
google-genai
```

---

## 설치

### 1. 가상환경 생성 및 활성화

Windows PowerShell

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux

```bash
python3 -m venv .venv && source .venv/bin/activate
```

> PowerShell에서 `Activate.ps1` 실행이 정책으로 차단되면, **현재 터미널 세션에만** 정책을 완화한 뒤 다시 활성화한다. 시스템 전체 설정은 변경되지 않는다.
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

프롬프트 앞에 `(.venv)`가 표시되는지, 그리고 설치가 완료되는지 확인한다.

---

## API 키 설정

이 프로그램은 API 키를 **환경변수 또는 `.env` 파일에서만** 읽는다. 코드에 키를 직접 작성하지 않는다.

### 1. 키 발급

| 키 | 발급 위치 | 비고 |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio → API 키 만들기 | |
| `KAKAO_REST_API_KEY` | Kakao Developers → 내 애플리케이션 → 앱 키 → **REST API 키** | 네이티브·JavaScript·Admin 키가 아니라 **REST API 키** |

Kakao Local 검색은 별도의 동의 항목 설정 없이 REST API 키만으로 호출할 수 있다.

### 2. `.env` 파일 작성

프로젝트 루트에 `.env`를 만들고 발급받은 값을 넣는다. 저장소에 포함된 `.env.example`을 복사해서 쓰면 된다.

```bash
cp .env.example .env
```

```env
GEMINI_API_KEY=발급받은_Gemini_키
KAKAO_REST_API_KEY=발급받은_Kakao_REST_API_키
```

### 3. 환경변수로 설정하는 방법 (선택)

`.env` 대신 터미널 세션에만 임시로 설정할 수도 있다.

Windows PowerShell

```powershell
$env:GEMINI_API_KEY="YOUR_KEY"; $env:KAKAO_REST_API_KEY="YOUR_KEY"
```

macOS / Linux

```bash
export GEMINI_API_KEY="YOUR_KEY" && export KAKAO_REST_API_KEY="YOUR_KEY"
```

키가 하나라도 설정되어 있지 않으면 프로그램은 **API를 호출하기 전에** 아래 메시지를 출력하고 즉시 종료한다.

```text
오류: KAKAO_REST_API_KEY가 설정되지 않았습니다.
.env 파일을 확인하세요.
```

---

## 실행 방법

### 핵심 명령 5개

```powershell
# 1. 가상환경 활성화
.\.venv\Scripts\Activate.ps1

# 2. 기본 실행 (여행 날짜만 입력)
python travel_planner.py -date "2026-10-15"

# 3. 당일 여행
python travel_planner.py -date "2026-10-15" --days 1

# 4. 1박 2일
python travel_planner.py -date "2026-10-15" --days 2

# 5. 날짜 형식 오류 확인
python travel_planner.py -date "2026/10/15"
```

`--days`의 기본값은 `1`이므로 **2번과 3번은 동일하게 동작한다.** 즉 여행 날짜만 입력해도 그대로 실행된다.

### 옵션

| 옵션 | 필수 | 값 | 설명 |
|---|---|---|---|
| `-date`, `--date` | **필수** | `YYYY-MM-DD` | 여행 날짜. 형식이 다르면 사용법을 출력하고 종료한다 |
| `--days` | 선택 | `1` 또는 `2` (기본값 `1`) | `1` = 당일, `2` = 1박 2일. 허용값 외 입력은 argparse가 차단한다 |

### 일수에 따른 차이

| `--days` | 추천 조건 | 일정 구성 | 저장 파일명 |
|---|---|---|---|
| `1` | 당일 여행 | **A안 / B안** — 두 도시를 각각 독립된 당일 코스로 제안 | `..._1d.json` / `..._1d.md` |
| `2` | 1박 2일 여행 | **DAY 1 / DAY 2** — 두 도시를 이어지는 연계 코스로 제안 | `..._2d.json` / `..._2d.md` |

### 실행 예시

```text
$ python travel_planner.py -date "2026-10-15" --days 1

국내 여행지 추천 프로그램
여행 날짜: 2026-10-15
여행 일수: 1일 (당일)
API 키 설정 확인 완료

[1/3] Gemini 여행지 추천 생성 중...
  - JSON 응답 수신 완료
  - 추천 지역 1: 경주시
  - 추천 지역 2: 가평군

[2/3] Kakao 맛집 검색 중...
  - [1/2] 검색어: "경주시 맛집"
    → 5곳 검색 완료
  - [2/2] 검색어: "가평군 맛집"
    → 5곳 검색 완료

[3/3] Gemini 최종 리포트 생성 중...
  - 최종 리포트 생성 완료

결과 저장 완료
  - results/data_2026-10-15_1d.json
  - results/report_2026-10-15_1d.md

완료!
```

> `[1/3]` 아래에 `google-genai` 라이브러리의 AFC 권고 메시지가 한 줄 출력될 수 있다. 오류가 아니며 동작에 영향이 없다.
>
> 같은 명령을 다시 실행하면 추천 지역이 달라질 수 있다. LLM은 같은 입력에도 매번 다른 응답을 생성하므로 정상 동작이다. 프로그램은 특정 도시명을 가정하지 않고 응답 **구조**만 검증한다.

---

### 입력값 검증 명령

| 명령 | 기대 동작 |
|---|---|
| `python travel_planner.py -date "2026/10/15"` | 날짜 형식 오류 → 사용법 출력 후 종료 (API 호출 없음) |
| `python travel_planner.py -date "2026-10-15" --days 3` | `choices=[1, 2]`에 의해 argparse가 실행 전 차단 |
| `python travel_planner.py` | 필수 인자 `-date` 누락 안내 후 종료 |

---

## 결과물 확인

실행이 끝나면 `results/` 폴더가 자동으로 생성되고 파일 두 개가 저장된다. 경로는 실행 로그 마지막에 출력된다.

```powershell
dir .\results
```

```text
results/
├── data_2026-10-15_1d.json    # 원본 데이터
└── report_2026-10-15_1d.md    # 최종 여행 리포트
```

파일명에 날짜와 일수가 모두 들어가므로, 같은 날짜라도 일수가 다르면 기존 결과가 덮어써지지 않는다.

### 원본 데이터 JSON

```json
{
  "date": "2026-10-15",
  "days": 1,
  "recommendation": {
    "recommended_city": "경주시",
    "weather": "...",
    "events": ["신라문화제", "경주 문화유산 야행"],
    "reason": "...",
    "recommended_cities": [ { "city": "경주시", "highlight": "..." }, { "city": "가평군", "highlight": "..." } ]
  },
  "restaurants_by_city": {
    "경주시": [
      { "name": "소향몽 경주본점", "address": "경북 경주시 사정로57번길 16",
        "category": "음식점 > 한식", "url": "http://place.map.kakao.com/1335858493",
        "phone": "054-701-0010", "lng": 129.209369266517, "lat": 35.8378369520616 }
    ],
    "가평군": [ "..." ]
  },
  "errors": []
}
```

### 최종 리포트 Markdown

Markdown 미리보기로 열면 렌더링된 상태로 확인할 수 있다. (VS Code에서 `Ctrl+Shift+V`)

```markdown
# 2026-10-15 국내 여행 추천 리포트
## 추천 지역
## 추천 이유
## 날씨 요약
## 행사/축제
## 맛집 추천        ← 도시별로 구분, 검색 결과가 없으면 "데이터 없음"
## 일정 제안        ← --days 1: A안/B안  ·  --days 2: DAY 1/DAY 2
## 오류 요약        ← 오류가 없으면 "오류 없음"
```

리포트에 등장하는 식당은 모두 Kakao 검색 결과에 실제로 존재하는 장소다. 프롬프트에서 검색 결과에 없는 식당을 만들어내지 못하도록 제한했다.

---

## 오류 상황별 동작

| 상황 | 동작 |
|---|---|
| 날짜 형식 오류 | 사용법 출력 후 종료 (API 호출 없음) |
| `--days` 허용값 외 입력 | argparse가 실행 전 차단 |
| API 키 미설정 | 설정 안내 출력 후 즉시 종료 |
| Gemini JSON 파싱·구조 검증 실패 | **최대 1회** 재요청 → 그래도 실패하면 오류 기록 후 종료 |
| Kakao 검색 결과 0건 | 해당 도시를 "데이터 없음"으로 처리하고 **계속 진행** |
| Kakao 인증(401·403)·네트워크 오류 | `errors`에 기록하고 **계속 진행** — 리포트는 생성된다 |
| 좌표 값 없음 | `lat` / `lng`를 `None`으로 저장하고 계속 진행 |

모든 오류는 원본 JSON의 `errors` 배열과 리포트의 "오류 요약" 섹션에 남는다.

```json
{ "step": "place_search", "city": "가평군",
  "type": "EMPTY_RESULT", "message": "0 results for query=가평군 맛집" }
```

---

## ⚠️ API 키 보안 주의사항

**이 저장소에 실제 API 키를 절대 커밋하지 않는다.**

- `.env`는 `.gitignore` 첫 줄에 등록되어 있다. 저장소에는 값이 비어 있는 `.env.example`만 포함한다.
- 커밋 전 `.env`가 실제로 제외되는지 확인한다. `.gitignore` 파일명에 오타(`.gitnore` 등)가 있으면 무시 규칙이 **전혀 동작하지 않는다.**

  ```bash
  git status --ignored
  ```

  결과의 **Ignored files** 목록에 `.env`가 있어야 한다.

- **화면 캡처에 `.env` 파일을 띄우지 않는다.** 키 값을 색으로 덮어 가려도 편집기의 **미니맵·탭 미리보기·스크롤바 썸네일**에 원본이 축소 렌더링되어 남을 수 있다. 환경변수 설정을 증빙해야 한다면 `.env.example`과 `.gitignore`를 대신 캡처한다.
- 터미널에 `echo $env:GEMINI_API_KEY` 같은 명령으로 키를 출력하지 않는다. 스크롤백에 남는다.
- 실수로 키를 커밋·업로드했다면 **파일을 지우는 것만으로는 복구되지 않는다.** 커밋 기록에 남으므로 해당 키를 발급처에서 **즉시 폐기하고 새로 발급**한다.

---

## 프로젝트 구조

```text
.
├── travel_planner.py     # 프로그램 전체 (CLI · API 호출 · 저장)
├── requirements.txt      # 의존 패키지
├── .env                  # 실제 API 키 (Git 제외)
├── .env.example          # 환경변수 이름 예시
├── .gitignore            # .env, __pycache__, .venv 제외
├── README.md
├── images/               # 보고서 캡처 이미지
└── results/              # 실행 시 자동 생성
    ├── data_YYYY-MM-DD_Nd.json
    └── report_YYYY-MM-DD_Nd.md
```

### 함수 구성

```text
main()
 ├─ parse_arguments()            # -date(필수) / --days(1|2, 기본 1)
 ├─ validate_date()              # YYYY-MM-DD 형식 검증
 ├─ load_config()                # .env에서 API 키 로드
 ├─ get_travel_recommendation()  # [1/3] Gemini 추천 2곳 + 검증 + 재요청 1회
 ├─ search_kakao_restaurants()   # [2/3] Kakao 검색 + 응답 정규화
 ├─ generate_final_report()      # [3/3] Gemini 최종 Markdown 리포트
 └─ save_results()               # results/ 폴더에 JSON · Markdown 저장
```

---

## API 사용 정보

### Gemini

| 항목 | 내용 |
|---|---|
| 모델 | `gemini-3.5-flash` |
| 호출 횟수 | 실행 1회당 **2번** — `[1/3]` 추천 생성, `[3/3]` 리포트 생성 |
| 인증 | `genai.Client(api_key=...)` — 키는 `os.getenv()`로만 읽음 |

### Kakao Local — 키워드로 장소 검색

| 항목 | 내용 |
|---|---|
| URL | `https://dapi.kakao.com/v2/local/search/keyword.json` |
| Method | `GET` |
| 인증 헤더 | `Authorization: KakaoAK {REST_API_KEY}` |
| 파라미터 | `query="{도시명} 맛집"`, `category_group_code=FD6`(음식점), `size=5`, `page=1`, `sort=accuracy` |
| 타임아웃 | `10`초 |

**응답 필드 정규화**

| Kakao 응답 | 프로그램 내부 |
|---|---|
| `place_name` | `name` |
| `road_address_name` (없으면 `address_name`) | `address` |
| `category_name` | `category` |
| `place_url` | `url` |
| `phone` | `phone` |
| `x` / `y` | `lng` / `lat` (`float` 변환) |

---

## 문제 해결

| 증상 | 원인 및 해결 |
|---|---|
| `python -m venv .venv` 실행 중 `ensurepip` 오류 | 가상환경이 미완성 상태로 남는다. 명령을 다시 실행한 뒤 `.venv/Scripts`(또는 `bin`)에 `pip`이 생성되었는지 확인한다 |
| `Activate.ps1` 실행이 차단됨 | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` 후 재시도 |
| `ERROR: Could not open requirements file` | `requirements.txt`가 있는 폴더에서 실행하는지 확인한다 |
| `pip install` 중 `getaddrinfo failed` | 일시적 네트워크·DNS 문제다. 이미 설치되어 있으면(`Requirement already satisfied`) 실행에는 지장이 없다 |
| Kakao 401 / 403 | `Authorization` 값의 `KakaoAK ` 접두어(뒤 공백 포함) 누락이 가장 흔하다. REST API 키를 쓰고 있는지도 확인한다 |
| 리포트 한글이 깨짐 | 저장 시 `encoding="utf-8"`을 사용한다. 파일을 여는 편집기의 인코딩 설정도 UTF-8인지 확인한다 |

---

## 개발 예정

- 결과 캐싱 — 같은 날짜·일수로 재실행하면 저장된 JSON을 재사용해 API 호출을 생략
- 맛집 검색 직후 원본 JSON 선저장 — 리포트 생성이 실패해도 수집한 데이터를 잃지 않도록
- Gemini 응답이 코드블록으로 감싸여 오는 경우의 제거 처리

---

## 관련 문서

| 문서 | 내용 |
|---|---|
| [과제 제출보고서](a1-2_국내여행지추천_과제_제출보고서.md) | 설계 근거, 실행 결과, 검증 내용, 수행 과정 이슈 8건 |
| [발표자료](a1-2_국내여행지추천_과제_발표자료.pptx) | 12장 요약 슬라이드 |
