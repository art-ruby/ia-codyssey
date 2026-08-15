# 🧳 Python 응용: API 활용 국내 여행지 추천 프로그램 개발

> **분야:** AI 활용 학습  
> **구분:** AI 활용  
> **학습시간:** 40시간  
> **개발환경:** Python 3.10 이상 / CLI 기반  
> **LLM API:** Google Gemini  
> **장소 검색 API:** NAVER API HUB 지역 검색

---

## 1. 미션 소개

이번 프로젝트는 Python에서 하나의 API만 호출하는 수준을 넘어, **LLM API와 국내 장소 검색 API를 연결하여 하나의 완성된 데이터 흐름을 만드는 것**을 목표로 한다.

사용자가 여행 날짜를 입력하면 Gemini가 해당 시기에 여행하기 좋은 국내 지역을 추천하고, 추천 결과를 JSON으로 구조화한다. 이후 JSON의 `recommended_city` 값을 네이버 지역 검색 API의 검색어로 사용하여 해당 지역의 맛집 정보를 검색한다.

마지막으로 1차 여행지 추천 정보와 네이버 맛집 검색 결과를 다시 Gemini에 전달하여 최종 여행 리포트를 Markdown 형식으로 생성하고, 원본 데이터와 함께 `results/` 폴더에 저장한다.

이 프로젝트는 과제 제출로 끝내지 않고 실제 여행 추천 앱으로 확장할 수 있도록 설계한다. 앱에서는 질문을 많이 늘리지 않고 **여행 기간, 출발 지역, 여행 스타일** 세 가지 조건만 먼저 받아 여행지를 간단히 추천하고, 사용자가 여행지를 선택한 뒤 **가족/단체, 이동 방법**만 추가로 받아 여행 일정을 생성하는 구조로 확장한다.

### 과제 필수 처리 흐름

```text
사용자 여행 날짜 입력
        ↓
Gemini API
        ↓
여행지 추천 JSON 생성
        ↓
recommended_city 추출
        ↓
NAVER API HUB 지역 검색
        ↓
추천 지역 맛집 5곳 검색
        ↓
1차 추천 JSON + 맛집 목록 결합
        ↓
Gemini API
        ↓
최종 Markdown 여행 리포트 생성
        ↓
results/
├─ 원본 JSON
└─ 최종 Markdown
```

이번 미션의 핵심은 단순히 AI에게 여행지를 추천받는 것이 아니라,

> **한 API의 출력값을 다음 API의 입력값으로 사용하고, 서로 다른 API에서 얻은 데이터를 다시 조합하여 새로운 결과물을 만드는 API 파이프라인을 구현하는 것**이다.

---

## 2. 과제 요구사항 분석

| 구분 | 필수 요구사항 | 구현 방향 |
|---|---|---|
| CLI 프로그램 | `-date "YYYY-MM-DD"` 필수 | `argparse` 사용 |
| 날짜 검증 | 잘못된 형식이면 종료 | `datetime.strptime()` |
| LLM API | OpenAI 또는 Gemini | Gemini 선택 |
| 장소 검색 API | Kakao 또는 Naver | NAVER 지역 검색 선택 |
| 1차 추천 | JSON 구조화 | Gemini 구조화 출력 |
| 지역 연결 | `recommended_city` 사용 | 네이버 검색어 생성 |
| 맛집 검색 | 권장 5곳 | `display=5` |
| 오류 처리 | API/파싱 오류 대응 | `try-except` |
| JSON 파싱 실패 | 최대 1회 재시도 | 재요청 함수 |
| 검색 결과 0건 | 프로그램 계속 실행 | 빈 리스트 처리 |
| 원본 데이터 | JSON 저장 | `results/` |
| 최종 리포트 | Markdown 저장 | `results/` |
| API 키 보안 | 코드 직접 입력 금지 | `.env` |
| 오류 기록 | `errors` 배열 | JSON + 리포트 반영 |

---

## 2-1. 실제 앱으로 확장하는 설계

과제의 필수 기능은 CLI로 먼저 완성하고, 같은 추천 로직을 이후 웹앱에서도 그대로 재사용할 수 있도록 구성한다.

### 앱 설계 원칙

- 첫 화면에서 많은 질문을 하지 않는다.
- 처음에는 **3개 항목만 입력**받는다.
- 여행지는 **3곳 정도를 간단히 추천**한다.
- 사용자가 여행지를 선택한 뒤 추가 정보는 **가족/단체, 이동 방법** 두 가지만 받는다.
- 인원수는 세분화하지 않는다.
- 실제 식당과 장소 정보는 Gemini가 임의로 만들지 않고 NAVER 검색 결과를 사용한다.

### 1단계 — 처음 받는 3개 정보

#### 1. 여행 기간

```text
[ 당일 ] [ 1박 2일 ] [ 2박 3일 ] [ 3박 4일 ]
```

과제에서는 `-date "YYYY-MM-DD"` 입력을 필수로 유지하고, 앱에서는 여행 길이를 `duration`으로 추가한다.

예:

```json
{
  "date": "2026-10-15",
  "duration": "1박 2일"
}
```

#### 2. 출발 지역

```text
[ 창원 ]
```

출발 지역은 이동 부담을 고려하여 여행지를 추천하는 데 사용한다.

#### 3. 여행 스타일

클릭 가능한 태그 형태로 제공한다.

```text
[ 힐링 ] [ 맛집 ] [ 바다 ] [ 역사 ]
[ 자연 ] [ 카페 ] [ 사진 ] [ 축제 ]
[ 산책 ] [ 문화 ] [ 액티비티 ] [ 온천 ]
```

2~3개 정도 복수 선택할 수 있도록 한다.

예:

```json
{
  "travel_styles": ["힐링", "맛집", "바다"]
}
```

### 2단계 — 여행지 추천

세 가지 조건을 바탕으로 Gemini가 **국내 여행지 3곳을 간단히 추천**한다.

예:

```text
1. 통영
바다 · 힐링 · 맛집
창원에서 접근성이 좋고 1박 2일 여행에 적합합니다.

2. 거제
바다 · 자연
해안 풍경과 자연 중심 여행에 적합합니다.

3. 남해
힐링 · 자연
조용하고 여유로운 여행에 적합합니다.
```

이 단계에서는 상세 일정과 식당을 모두 만들지 않고, 먼저 여행지만 추천한다.

### 3단계 — 여행지 선택 후 추가 정보

사용자가 여행지를 선택하면 두 가지만 추가로 입력한다.

#### 여행 형태

```text
[ 가족 ] [ 단체 ]
```

세부 인원수는 묻지 않는다.

`가족`과 `단체` 선택값은 NAVER 맛집 검색 키워드와 Gemini 일정 생성 프롬프트에 반영한다.

#### 이동 방법

```text
[ 자가용 ] [ 대중교통 ]
```

이동 방법은 일정의 이동 범위와 장소 배치에 반영한다.

### 최종 앱 흐름

```text
여행 기간
   ↓
출발 지역
   ↓
여행 스타일
   ↓
[ 여행지 추천 ]
   ↓
추천 여행지 3곳
   ↓
사용자가 여행지 선택
   ↓
가족 / 단체
   ↓
자가용 / 대중교통
   ↓
NAVER 장소·맛집 검색
   ↓
Gemini 일정 생성
   ↓
최종 여행 일정
```

### 앱에서 사용할 입력 데이터 예시

```json
{
  "date": "2026-10-15",
  "duration": "1박 2일",
  "departure": "창원",
  "travel_styles": ["힐링", "맛집", "바다"],
  "selected_city": "통영",
  "travel_group": "가족",
  "transport": "자가용"
}
```

질문 수는 적지만 여행지 추천과 식당 검색, 일정 생성에 필요한 핵심 조건은 확보할 수 있다.

### 과제와 앱의 연결

```text
과제 CLI
-date 입력
   ↓
Gemini 추천
   ↓
NAVER 맛집
   ↓
Markdown + JSON
```

과제 완료 후에는 핵심 API 함수는 그대로 두고 사용자 입력 화면만 앱으로 확장한다.

```text
웹앱
여행 기간 + 출발 지역 + 여행 스타일
   ↓
추천 여행지 3곳
   ↓
가족/단체 + 이동 방법
   ↓
기존 Gemini/NAVER 로직 재사용
   ↓
여행 일정
```

즉 과제용 프로그램과 앱을 따로 만드는 것이 아니라, **같은 추천 로직을 CLI와 앱에서 함께 사용하는 구조**를 목표로 한다.

---

## 3. 사용 기술 및 개발 환경

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.10 이상 |
| 실행 방식 | CLI / 터미널 |
| LLM | Google Gemini API |
| 장소 검색 | NAVER API HUB 지역 검색 |
| HTTP 요청 | `requests` |
| 환경변수 | `python-dotenv` |
| CLI 인자 | `argparse` |
| 데이터 형식 | JSON |
| 최종 문서 | Markdown |
| 결과 저장 | `results/` 폴더 |

---

## 4. API 선택

### 4.1 LLM API — Google Gemini

Gemini는 본 프로젝트에서 두 번 사용한다.

**첫 번째 호출**에서는 사용자가 입력한 날짜를 기준으로 여행지를 추천하고 다음 JSON을 생성한다.

```json
{
  "recommended_city": "string",
  "weather": "string",
  "events": ["string"],
  "reason": "string"
}
```

**두 번째 호출**에서는 다음 데이터를 받아 최종 Markdown 여행 리포트를 생성한다.

```text
1차 여행 추천 JSON
+
NAVER 맛집 검색 결과
+
errors
```

### 4.2 장소 검색 API — NAVER API HUB 지역 검색

맛집 검색은 네이버 지역 검색 API를 사용한다.

검색어는 다음과 같이 만든다.

```text
추천도시 + " 맛집"
```

예:

```text
강릉 맛집
경주 맛집
전주 맛집
부산 맛집
```

본 과제에서는 지역 검색 결과를 최대 5건 사용한다.

### 요청 방식

```text
HTTP Method : GET
기능        : 네이버 지역 서비스 업체·기관 검색
검색 결과   : JSON
검색 개수   : 5
```

### 주요 요청 파라미터

```text
query   = "추천도시 맛집"
display = 5
start   = 1
sort    = comment
format  = json
```

`sort=comment`는 업체·기관에 대한 카페·블로그 리뷰 수를 기준으로 정렬할 때 사용할 수 있다.

---

## 5. NAVER API HUB 사용 기준

본 프로젝트는 신규 구현 기준으로 **NAVER API HUB** 방식으로 작성한다.

### API 요청 주소

```text
https://naverapihub.apigw.ntruss.com/search/v1/local
```

### 인증 헤더

```text
X-NCP-APIGW-API-KEY-ID
X-NCP-APIGW-API-KEY
```

실제 인증 값은 코드에 직접 작성하지 않고 `.env`에서 읽어온다.

---

## 6. 프로젝트 폴더 구조

```text
travel_recommender/
│
├── main.py                  # 과제용 CLI
├── app.py                   # 앱 확장 시 추가
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
│
└── results/
```

실행 후:

```text
travel_recommender/
│
├── main.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
│
└── results/
    ├── data_2026-10-15.json
    └── report_2026-10-15.md
```

| 파일 | 역할 |
|---|---|
| `main.py` | 프로그램 전체 실행 |
| `requirements.txt` | Python 패키지 목록 |
| `.env` | 실제 API 인증 정보 |
| `.env.example` | 환경변수 이름 예시 |
| `.gitignore` | `.env` 등 Git 제외 |
| `README.md` | 과제 수행 보고서 |
| `results/` | 실행 결과 저장 |

---

## 7. STEP 1 — 개발환경 준비

필요 패키지:

```text
requests
python-dotenv
google-genai
```

`requirements.txt` 예시:

```text
requests
python-dotenv
google-genai
```

설치:

```bash
pip install -r requirements.txt
```

---

## 8. STEP 2 — API 키 설정

프로젝트 루트에 `.env` 파일을 만든다.

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
NAVER_CLIENT_ID=YOUR_NAVER_CLIENT_ID
NAVER_CLIENT_SECRET=YOUR_NAVER_CLIENT_SECRET
```

실제 키는 README나 GitHub에 작성하지 않는다.

### `.env.example`

```env
GEMINI_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
```

### `.gitignore`

```gitignore
.env
__pycache__/
*.pyc
.venv/
venv/
.vscode/
```

가장 중요한 항목은 `.env`이다.

---

## 9. STEP 3 — CLI 날짜 입력 구현

과제에서는 `argparse`로 날짜를 입력받는다.

```bash
python main.py -date "2026-10-15"
```

편의를 위해 `--date`도 함께 지원할 수 있다.

```bash
python main.py --date "2026-10-15"
```

예시:

```python
import argparse

parser = argparse.ArgumentParser(
    description="국내 여행지 추천 프로그램"
)

parser.add_argument(
    "-date",
    "--date",
    required=True,
    help='여행 날짜 (YYYY-MM-DD)'
)

args = parser.parse_args()
```

---

## 10. STEP 4 — 날짜 형식 검증

입력값은 반드시 `YYYY-MM-DD` 형식이어야 한다.

정상:

```text
2026-10-15
```

오류:

```text
2026/10/15
10-15-2026
20261015
```

검증 예시:

```python
from datetime import datetime

def validate_date(date_string):
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False
```

잘못된 날짜가 입력되면 API 호출 전에 종료한다.

```text
오류: 날짜 형식이 올바르지 않습니다.

사용법:
python main.py -date "YYYY-MM-DD"
```

---

## 11. STEP 5 — API 키 존재 여부 확인

```python
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
```

필수 키가 없으면 즉시 종료한다.

```text
오류: NAVER_CLIENT_ID가 설정되지 않았습니다.
.env 파일을 확인하세요.
```

---

## 12. STEP 6 — Gemini 1차 여행지 추천

사용자가 입력한 날짜를 Gemini에 전달한다.

예:

```text
2026-10-15
```

Gemini는 반드시 JSON으로 파싱 가능한 결과를 반환해야 한다.

### 필수 JSON 구조

```json
{
  "recommended_city": "경주",
  "weather": "10월 중순은 비교적 선선하여 야외 관광에 적합한 시기입니다.",
  "events": [
    "가을 지역 문화 행사",
    "역사 문화 프로그램"
  ],
  "reason": "가을의 경주는 역사 유적과 계절 풍경을 함께 즐기기 좋습니다. 야외 이동이 많은 여행에도 비교적 적합한 시기입니다."
}
```

### 필수 스키마

| 키 | 타입 | 설명 |
|---|---|---|
| `recommended_city` | string | 추천 국내 여행지역 |
| `weather` | string | 해당 시기 일반적 날씨 |
| `events` | array[string] | 행사·축제 후보 1~3개 |
| `reason` | string | 추천 이유 2~4문장 |

---

## 13. STEP 7 — JSON 구조화 프롬프트 설계

```text
여행 날짜: 2026-10-15

이 날짜에 여행하기 좋은 대한민국 국내 여행지 1곳을 추천하세요.

반드시 다음 JSON 구조로만 응답하세요.

{
  "recommended_city": "string",
  "weather": "string",
  "events": ["string"],
  "reason": "string"
}

조건:
- recommended_city는 대한민국 도시 또는 여행지역 1곳
- weather는 해당 시기의 일반적인 날씨 설명
- events는 행사 또는 축제 후보 1~3개
- reason은 추천 이유 2~4문장
- JSON 이외의 설명 문장은 출력하지 말 것
- Markdown 코드블록을 사용하지 말 것
```

가능하면 Gemini의 구조화 출력 기능을 사용하여 JSON 스키마를 지정한다.

---

## 14. STEP 8 — JSON 파싱 및 다음 API로 연결

```python
import json

data = json.loads(response_text)
recommended_city = data["recommended_city"]
```

예:

```text
recommended_city = "경주"
```

이 값이 네이버 API의 검색어로 이어진다.

```text
Gemini 출력
recommended_city = "경주"
        ↓
NAVER 검색어
"경주 맛집"
```

이 연결 구조가 이번 미션의 핵심이다.

---

## 15. STEP 9 — Gemini JSON 파싱 실패 처리

LLM이 JSON 외 문장을 함께 출력하면 파싱 오류가 발생할 수 있다.

이 경우 무한 재시도하지 않고 **최대 1회만 다시 요청**한다.

```text
Gemini 호출
    ↓
JSON 파싱
    │
    ├─ 성공 → 다음 단계
    │
    └─ 실패
         ↓
     재요청 1회
         ↓
     JSON 재파싱
         │
         ├─ 성공 → 다음 단계
         └─ 실패 → 오류 처리
```

재요청 예시:

```text
이전 응답은 JSON 파싱에 실패했습니다.

설명 문장과 Markdown을 모두 제거하고,
다음 네 개의 필수 키만 포함한 유효한 JSON 객체 하나만 출력하세요.

recommended_city
weather
events
reason
```

---

## 16. STEP 10 — NAVER 지역 검색 API 호출

추천 지역을 이용해 맛집을 검색한다.

```python
import requests

url = "https://naverapihub.apigw.ntruss.com/search/v1/local"

headers = {
    "X-NCP-APIGW-API-KEY-ID": NAVER_CLIENT_ID,
    "X-NCP-APIGW-API-KEY": NAVER_CLIENT_SECRET,
}

params = {
    "query": f"{recommended_city} 맛집",
    "display": 5,
    "start": 1,
    "sort": "comment",
    "format": "json",
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=10
)

response.raise_for_status()
data = response.json()
```

---

## 17. STEP 11 — NAVER 응답 구조 확인

네이버 지역 검색 결과는 `items` 배열 안에 들어온다.

```json
{
  "items": [
    {
      "title": "음식점 이름",
      "link": "https://...",
      "category": "한식",
      "description": "",
      "address": "지번 주소",
      "roadAddress": "도로명 주소",
      "mapx": "1269873882",
      "mapy": "375666103"
    }
  ]
}
```

---

## 18. STEP 12 — NAVER 데이터를 과제 스키마로 정규화

네이버 응답 필드와 과제 요구 필드명이 다르므로 프로그램 내부에서 변환한다.

| NAVER 응답 | 프로그램 내부 | 의미 |
|---|---|---|
| `title` | `name` | 음식점 이름 |
| `roadAddress` 또는 `address` | `address` | 주소 |
| `category` | `category` | 업종 |
| `link` | `url` | 관련 URL |
| `mapx` | `lng` | 경도 |
| `mapy` | `lat` | 위도 |

변환 예:

```json
{
  "name": "음식점 A",
  "address": "경상북도 경주시 ...",
  "category": "한식",
  "url": "https://...",
  "lat": 37.5666103,
  "lng": 126.9873882
}
```

---

## 19. STEP 13 — 좌표값 변환

`mapx`, `mapy`를 일반적인 소수 경·위도 값으로 사용하려면 다음처럼 변환한다.

```python
lng = float(item["mapx"]) / 10_000_000
lat = float(item["mapy"]) / 10_000_000
```

예:

```text
mapx = 1269873882
→ lng = 126.9873882

mapy = 375666103
→ lat = 37.5666103
```

좌표가 비어 있거나 변환할 수 없으면 `None` 처리한다.

---

## 20. STEP 14 — HTML 태그 제거

검색 결과의 `title`에는 강조용 HTML 태그가 포함될 수 있으므로 제거한다.

```python
import re

def remove_html_tags(text):
    return re.sub(r"<[^>]+>", "", text or "")
```

---

## 21. STEP 15 — 검색 결과 0건 처리

검색 결과가 없어도 프로그램을 중단하지 않는다.

```text
[2/3] NAVER 맛집 검색 중...
- 검색 결과 0건
- 맛집 데이터 없음 상태로 계속 진행합니다.
```

```json
"restaurants": []
```

오류 목록 예:

```json
{
  "step": "place_search",
  "type": "EMPTY_RESULT",
  "message": "검색 결과가 0건입니다."
}
```

최종 리포트:

```markdown
## 맛집 추천

- 데이터 없음
```

---

## 22. STEP 16 — NAVER API 오류 처리

대표적인 오류 상황:

- 인증 정보 오류
- 요청 형식 오류
- 네트워크 오류
- 호출 한도 문제
- 서버 오류
- JSON 파싱 오류

처리 흐름:

```text
NAVER API 오류
       ↓
errors에 오류 추가
       ↓
restaurants = []
       ↓
프로그램 계속 실행
       ↓
최종 리포트 생성
```

즉, **장소 검색 API가 실패해도 최종 여행 리포트는 생성한다.**

---

## 23. STEP 17 — 오류 목록 관리

```python
errors = []
```

예:

```json
{
  "step": "place_search",
  "type": "API_ERROR",
  "message": "NAVER 지역 검색 API 호출 실패"
}
```

---

## 24. STEP 18 — Gemini 최종 여행 리포트 생성

다음 데이터를 Gemini에 전달한다.

```text
1. 여행 날짜
2. 1차 추천 JSON
3. NAVER 맛집 검색 결과
4. errors
```

최종 리포트 필수 구조:

```markdown
# 2026-10-15 국내 여행 추천 리포트

## 추천 지역

## 추천 이유

## 날씨 요약

## 행사/축제

## 맛집 추천

## 1일 일정 제안

## 오류 요약
```

---

## 25. STEP 19 — 최종 리포트 프롬프트

```text
다음 데이터를 바탕으로 국내 여행 추천 리포트를 작성하세요.

여행 날짜:
2026-10-15

1차 추천 데이터:
{recommendation_json}

NAVER 지역 검색 맛집:
{restaurants_json}

오류:
{errors_json}

반드시 Markdown 형식으로 작성하세요.

포함할 항목:
# 여행 날짜 국내 여행 추천 리포트
## 추천 지역
## 추천 이유
## 날씨 요약
## 행사/축제
## 맛집 추천
## 1일 일정 제안
## 오류 요약

1일 일정은 오전 / 오후 / 저녁 수준으로 구성하세요.
맛집 목록이 비어 있으면 '데이터 없음'이라고 작성하세요.
```

---

## 26. STEP 20 — 결과 저장

`results/` 폴더가 없으면 자동 생성한다.

```python
from pathlib import Path

RESULT_DIR = Path("results")
RESULT_DIR.mkdir(exist_ok=True)
```

### 원본 JSON

```text
results/data_2026-10-15.json
```

최소 구조:

```json
{
  "date": "2026-10-15",
  "recommendation": {
    "recommended_city": "경주",
    "weather": "선선한 가을 날씨",
    "events": ["지역 가을 행사"],
    "reason": "가을 여행지로 추천합니다."
  },
  "restaurants": [],
  "errors": []
}
```

### 최종 Markdown

```text
results/report_2026-10-15.md
```

> 위 예시는 구조 설명용이며 실제 API 실행 결과가 아니다.

---

## 27. 전체 실행 로그 예시

```text
$ python main.py -date "2026-10-15"

여행 날짜: 2026-10-15

[1/3] Gemini 여행지 추천 생성 중...
- JSON 응답 수신
- 추천 지역: 경주

[2/3] NAVER 맛집 검색 중...
- 검색어: 경주 맛집
- 맛집 5곳 검색 완료

[3/3] Gemini 최종 리포트 생성 중...
- Markdown 리포트 생성 완료

결과 저장 중...
- results/data_2026-10-15.json
- results/report_2026-10-15.md

완료!
```

> 실제 제출 시에는 프로그램 실행 후 실제 로그와 캡처로 교체한다.

---

## 28. REST API 요청/응답 이해

### Request

Python 프로그램이 외부 API에 요청을 보낸다.

```text
URL
HTTP Method
Headers
Query Parameters
Request Body
API 인증 정보
```

### Response

외부 API가 결과를 반환한다.

```text
HTTP Status Code
JSON Body
Error Message
```

---

## 29. GET과 POST 차이

| 구분 | GET | POST |
|---|---|---|
| 목적 | 데이터 조회 | 데이터 전송·생성 요청 |
| 주요 데이터 위치 | URL Query | Request Body |
| 본 프로젝트 | NAVER 지역 검색 | Gemini 요청 |
| 주요 응답 | JSON | JSON 또는 텍스트 |

프로젝트 적용:

```text
NAVER 지역 검색 → GET
Gemini 생성 요청 → POST 성격
```

---

## 30. HTTP 오류 이해

| 상태 | 의미 |
|---|---|
| 200 | 요청 성공 |
| 400 | 잘못된 요청 |
| 401 | 인증 문제 |
| 403 | 접근 권한 문제 |
| 404 | 잘못된 API 주소 또는 리소스 |
| 429 | 요청 제한 또는 호출 한도 |
| 500 | 서버 내부 오류 |

---

## 31. 프로그램 오류 처리 정책

| 오류 상황 | 처리 |
|---|---|
| 날짜 형식 오류 | 사용법 출력 후 종료 |
| Gemini API 키 없음 | 즉시 종료 |
| NAVER Client ID 없음 | 즉시 종료 |
| NAVER Client Secret 없음 | 즉시 종료 |
| Gemini 1차 API 실패 | 오류 안내 후 종료 |
| Gemini JSON 파싱 실패 | 최대 1회 재요청 |
| NAVER 검색 실패 | 맛집 없음 처리 후 계속 |
| NAVER 검색 0건 | 빈 리스트 후 계속 |
| 좌표 변환 실패 | `None` 처리 |
| 최종 리포트 생성 문제 | errors 기록 |
| 결과 파일 저장 실패 | 오류 메시지 출력 |

---

## 32. API 키 보안

API 키는 코드에 직접 작성하지 않는다.

잘못된 예:

```python
NAVER_CLIENT_SECRET = "실제_비밀키"
```

올바른 구조:

```text
Python 코드
   ↓
환경변수 읽기
   ↓
.env
   ↓
실제 API 키
```

이유:

1. GitHub 업로드 시 키 유출 방지
2. API 오남용 및 과금 사고 방지
3. 키 교체 시 코드 수정 불필요
4. 개발환경과 배포환경 분리 용이

---

## 33. 함수 단위 프로그램 설계

```text
parse_arguments()
validate_date()
load_config()

get_travel_recommendation()
parse_recommendation()

search_naver_restaurants()
normalize_naver_item()

generate_final_report()

save_json()
save_markdown()

# 앱 확장 시 재사용
recommend_destinations()
create_trip_plan()

main()
```

전체 관계:

```text
main()
 │
 ├─ parse_arguments()
 ├─ validate_date()
 ├─ load_config()
 ├─ get_travel_recommendation()
 │      ↓
 │   JSON 파싱
 │      ↓
 ├─ search_naver_restaurants()
 │      ↓
 │   NAVER 데이터 정규화
 │      ↓
 ├─ generate_final_report()
 ├─ save_json()
 └─ save_markdown()
```

---

## 34. 테스트 계획

### TEST 1 — 정상 실행

```bash
python main.py -date "2026-10-15"
```

확인:

- Gemini 호출
- 추천 도시 생성
- JSON 파싱
- NAVER 맛집 검색
- 최종 리포트 생성
- JSON 저장
- Markdown 저장

**증빙 위치:**

```text
[캡처 01] 정상 실행 터미널
```

### TEST 2 — 날짜 형식 오류

```bash
python main.py -date "2026/10/15"
```

예상:

```text
날짜 형식 오류
사용법 출력
프로그램 종료
```

```text
[캡처 02] 날짜 오류 화면
```

### TEST 3 — API 키 미설정

키 하나를 임시로 제거한 뒤 실행한다.

```text
[캡처 03] API 키 미설정 오류
```

> 캡처 시 실제 키가 보이지 않도록 한다.

### TEST 4 — NAVER 맛집 검색 성공

확인:

```text
추천 도시 + 맛집 검색
최대 5건 수집
name/address/category/url/lat/lng 변환
```

```text
[캡처 04] NAVER 맛집 검색 성공
```

### TEST 5 — 검색 실패 또는 0건

확인:

```text
restaurants = []
errors 기록
최종 리포트 계속 생성
```

```text
[캡처 05] 검색 실패 후 계속 실행되는 화면
```

### TEST 6 — 결과 파일 생성

```text
results/
├── data_2026-10-15.json
└── report_2026-10-15.md
```

```text
[캡처 06] results 폴더
```

### TEST 7 — 최종 Markdown

확인:

- 추천 지역
- 추천 이유
- 날씨
- 행사/축제
- 맛집
- 1일 일정
- 오류 요약

```text
[캡처 07] 최종 Markdown 리포트
```

---

## 35. 과제 목표와 구현 내용 연결

### 목표 1 — REST API 요청/응답 이해

NAVER 지역 검색 API를 GET으로 호출하고 JSON 응답을 처리한다.

### 목표 2 — LLM 결과 구조화

Gemini 결과를 JSON으로 받아 Python dictionary로 변환한다.

### 목표 3 — API 간 데이터 연결

```text
Gemini
 ↓
recommended_city
 ↓
NAVER 지역 검색
```

### 목표 4 — 여러 API 결과 결합

```text
Gemini 추천 JSON
+
NAVER 맛집 데이터
 ↓
Gemini
 ↓
최종 여행 리포트
```

### 목표 5 — 오류 대응

인증, 네트워크, 검색 결과 없음, JSON 파싱 문제를 상황별로 처리한다.

### 목표 6 — API 키 보안

`.env`로 실제 키와 소스 코드를 분리한다.

---

## 36. 보너스 과제 1 — 복수 지역 추천

기본:

```json
{
  "recommended_city": "경주"
}
```

확장:

```json
{
  "recommended_cities": [
    "경주",
    "강릉",
    "전주"
  ]
}
```

반복 처리:

```python
for city in recommended_cities:
    restaurants = search_naver_restaurants(city)
```

배움 포인트:

- 반복문
- 여러 API 호출
- 지역별 결과 구조
- API 요청량 관리

---

## 37. 보너스 과제 2 — 결과 캐싱

같은 날짜의 JSON이 이미 존재하면 API를 다시 호출하지 않고 기존 데이터를 사용할 수 있다.

```text
같은 날짜 재실행
     ↓
기존 JSON 존재 확인
     │
     ├─ 있음 → API 호출 생략
     └─ 없음 → API 호출
```

효과:

- API 호출량 감소
- 실행 속도 개선
- LLM 사용 비용 절감
- 동일 데이터 재사용

---

## 38. 수행 과정에서 확인할 핵심 포인트

### 1. LLM 응답은 다음 단계에서 사용할 수 있어야 한다.

자연어 답변만 받는 것이 아니라 JSON으로 구조화한다.

### 2. API마다 필드명이 다르다.

NAVER의 `title`, `mapx`, `mapy`를 과제의 `name`, `lng`, `lat` 형태로 변환한다.

### 3. 외부 API 실패를 전체 프로그램 실패로 만들지 않는다.

NAVER 맛집 검색이 실패하더라도 여행지 추천 결과를 기반으로 최종 리포트를 계속 생성한다.

### 4. 실제 서비스에서는 오류 처리가 중요하다.

입력 오류, API 키 누락, 네트워크 장애, JSON 파싱 오류 등을 예상한다.

### 5. API 키와 코드는 분리한다.

`.env`와 `.gitignore`를 활용한다.

---

## 39. 최종 제출 체크리스트

### CLI

- [ ] Python 3.10 이상에서 실행된다.
- [ ] `argparse`를 사용한다.
- [ ] `-date "YYYY-MM-DD"`를 지원한다.
- [ ] 날짜 입력이 필수이다.
- [ ] 잘못된 날짜 형식을 검증한다.

### Gemini

- [ ] Gemini API를 호출한다.
- [ ] 날짜를 입력값으로 사용한다.
- [ ] 1차 결과를 JSON으로 받는다.
- [ ] `recommended_city`가 존재한다.
- [ ] `weather`가 존재한다.
- [ ] `events`가 배열이다.
- [ ] `reason`이 존재한다.
- [ ] JSON 파싱 실패 시 최대 1회 재시도한다.

### NAVER

- [ ] NAVER API HUB 지역 검색을 사용한다.
- [ ] `recommended_city`를 검색 입력으로 사용한다.
- [ ] `"도시명 맛집"` 형태로 검색한다.
- [ ] 최대 5개의 결과를 사용한다.
- [ ] `title → name`으로 변환한다.
- [ ] 주소를 저장한다.
- [ ] category를 저장한다.
- [ ] link를 url로 저장한다.
- [ ] mapx/mapy 좌표를 처리한다.
- [ ] 검색 0건이어도 프로그램이 중단되지 않는다.

### 오류 처리

- [ ] `try-except`를 적용한다.
- [ ] API 키 미설정 시 즉시 종료한다.
- [ ] NAVER API 실패 시 최종 리포트를 계속 만든다.
- [ ] 오류를 `errors`에 기록한다.
- [ ] 무한 재시도를 하지 않는다.

### 결과물

- [ ] `results/` 폴더가 자동 생성된다.
- [ ] 원본 JSON 파일이 생성된다.
- [ ] JSON에 추천 결과가 포함된다.
- [ ] JSON에 맛집 목록이 포함된다.
- [ ] JSON에 `errors`가 포함된다.
- [ ] Markdown 리포트가 생성된다.
- [ ] 최종 리포트에 1일 일정이 포함된다.

### 보안

- [ ] 실제 API 키를 코드에 넣지 않았다.
- [ ] `.env`를 사용한다.
- [ ] `.env`가 `.gitignore`에 있다.
- [ ] README에 실제 키가 없다.
- [ ] 캡처 화면에 실제 키가 없다.
- [ ] JSON 결과에 실제 키가 없다.

### 보고서 증빙

- [ ] 정상 실행 터미널 캡처
- [ ] 날짜 검증 캡처
- [ ] NAVER 검색 성공 캡처
- [ ] 오류 처리 캡처
- [ ] results 폴더 캡처
- [ ] 원본 JSON 캡처
- [ ] 최종 Markdown 캡처

---

## 40. 프로젝트 수행 결과 정리

이번 프로젝트의 최종 구조는 다음과 같다.

```text
여행 날짜
   ↓
Gemini 여행지 추천
   ↓
JSON 구조화
   ↓
recommended_city
   ↓
NAVER 지역 검색
   ↓
맛집 데이터 정규화
   ↓
Gemini 최종 리포트
   ↓
JSON + Markdown 저장
```

단일 API 호출을 넘어서 서로 다른 API의 데이터를 연결하고, 외부 API 응답을 프로그램 내부에서 사용하기 좋은 형태로 변환하며, 오류 상황에서도 가능한 범위까지 계속 실행되는 구조를 만드는 것이 이번 프로젝트의 핵심이다.

---

## 41. 최종 프로젝트 구조

```text
travel_recommender/
│
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
└── results/
    ├── data_YYYY-MM-DD.json
    └── report_YYYY-MM-DD.md
```

실제 `.env` 파일은 로컬에서만 사용하고 GitHub에는 올리지 않는다.

---

## 42. 과제 핵심 한 줄 요약

> **과제에서는 여행 날짜를 입력받아 Gemini가 국내 여행지를 추천하고 NAVER 지역 검색으로 맛집 정보를 수집한 뒤 Markdown 여행 리포트를 생성·저장한다. 이후 같은 핵심 로직을 활용하여 여행 기간·출발 지역·여행 스타일을 먼저 받고, 여행지 선택 후 가족/단체와 이동 방법만 추가로 받아 일정을 만드는 간단한 여행 추천 앱으로 확장한다.**

---

## 43. 실제 실행 후 교체해야 할 부분

현재 README의 실행 결과와 JSON, 리포트 내용은 **프로그램 구조를 설명하기 위한 예시**이다.

실제 제출 전에는 다음을 실제 실행 결과로 교체한다.

```text
1. 실제 추천 도시
2. 실제 Gemini 1차 JSON
3. 실제 NAVER 맛집 5곳
4. 실제 results JSON
5. 실제 최종 Markdown 리포트
6. 실제 터미널 실행 로그
7. 실제 오류 테스트 결과
8. 실제 캡처 이미지
```

실행하지 않은 결과를 실제 수행 결과처럼 작성하지 않는다.
