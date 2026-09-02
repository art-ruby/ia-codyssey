# TECH.md — Python + Streamlit + CSV (로컬 단일 사용자)

**최종 수정일**: 2026-09-02
**용도**: Japanese Long-form Opportunity Radar

⚠️ **Python CLI + Streamlit + CSV 전용 가이드. 웹 프레임워크·DB·서버 없음.**

---

## 🚨 이 가이드의 범위

- ✅ **Python 3.11+** 표준 라이브러리 우선
- ✅ **Streamlit** 단일 화면 (읽기 전용)
- ✅ **CSV 파일** 저장 (`data/raw`, `data/processed`)
- ✅ **외부 API** — YouTube Data API v3, 번역 LLM(교체 가능), `yt-dlp`
- ❌ **DB 없음** (SQLite·Postgres·Firestore 전부)
- ❌ **로그인·다중 사용자 없음** (사용자 1명)
- ❌ **서버 배포 없음** (로컬 PC 전용)
- ❌ **React·Firebase·Node 코드 혼입 금지**

> **언제 이 가이드를 쓰나**: 본인 PC 에서 본인만 쓰는 데이터 수집·분석 도구.
> 다중 사용자·실시간 협업이 필요해지면 이 문서 전체를 다시 써야 한다.

---

## 🎯 핵심 원칙

### 1. 조용한 실패를 막는 것이 최우선

이 프로젝트의 실패는 **에러를 내지 않는다.** 형식이 어긋나면 «0개» 로
인식되고, 계산이 틀리면 **그럴듯한 숫자**가 나온다. 실제로 여러 번 걸렸다(§10).

> **에러가 없다는 것은 동작한다는 뜻이 아니다. 숫자를 확인한다.**

### 2. 값은 한 곳에만 둔다

임계값·가중치·경로·모델 이름을 코드 곳곳에 흩으면 나중에 무엇을 바꿨는지
알 수 없다. **전부 `src/config.py`.**

### 3. 기존 함수 우선

새 함수를 쓰기 전에 `src/` 에 같은 일을 하는 것이 있는지 본다.
특히 CSV 읽기·쓰기(`storage.py`)와 지표 계산(`analysis.py`)은 **반드시 재사용**한다.

### 4. 외부 호출은 갈아탈 수 있게

API 제공자는 몇 달이면 가격·모델·한도가 바뀐다. 호출 코드를 여기저기 두면
갈아타는 일이 큰 공사가 된다. **제공자별 함수를 한 파일에 모으고
`config` 한 줄로 고른다.**

---

## 🔥 기술 스택

### 실행

| | |
|---|---|
| 언어 | Python 3.11+ |
| 화면 | Streamlit |
| 저장 | CSV (`csv` 표준 모듈 · 분석은 pandas) |
| 그래프 | matplotlib |

### 외부

| 대상 | 도구 | 비고 |
|---|---|---|
| 영상·채널 데이터 | YouTube Data API v3 | 표준 `urllib` 로 직접 호출. SDK 안 씀 |
| 자막 | `yt-dlp` | 무료·키 불필요. `--sub-format json3` |
| 번역 | **OpenAI** (교체 가능) | §7 |

### 의존성 원칙

**수집은 표준 라이브러리만 쓴다.** 의존성이 적을수록 덜 깨진다.
`pandas` · `matplotlib` · `streamlit` 은 분석·화면 단계에서만 쓴다.

---

## 📁 폴더 구조

```
Japanese-Longform-Opportunity-Radar/
├── src/
│   ├── config.py              ⭐ 모든 값이 여기 한 곳
│   ├── storage.py             ⭐ CSV 읽기·쓰기는 여기만
│   ├── analysis.py            ⭐ 지표 계산은 여기만
│   ├── youtube.py             YouTube API + 할당량 계산
│   ├── translate.py           번역 (제공자 교체 가능)
│   ├── language.py            일본어 판정
│   ├── seeds.py               ⭐ 검색어 목록·후보는 여기만
│   ├── channels.py            ⭐ 채널 프로필은 여기만
│   ├── channel_fit.py         이 소재를 우리 채널에서 만들 가치가 있나
│   ├── comments.py            댓글 수집 + 분석
│   ├── production_brief.py    브리프 조립 + 대본용 자료
│   ├── subtitles.py           자막 발췌 (yt-dlp)
│   ├── export.py              내보내기 한 장
│   ├── collector.py           1단계 수집
│   ├── snapshot_collector.py  매일 스냅샷
│   └── channel_analyzer.py    Phase B 채널 검증
├── tests/                     API 없이 도는 검증
├── prompts/                   channel_fit.md · comment_analyzer.md
│                              script_writer.md — 긴 프롬프트는 코드에 안 박는다
├── docs/                      specs/ · automaker-contract.md
├── tools/                     backfill_titles.py · setup_translate.py
├── mockup/                    화면 목업 (동작하지 않는다) + build.py
├── data/
│   ├── config/                channels.json — 채널 정체성
│   ├── raw/                   videos.csv · video_snapshots.csv · quota_log.csv
│   │                          seeds.json · subs/ · comments/
│   ├── processed/             channels.csv · channel_fit.csv · comments/
│   ├── briefs/{channel_id}/   Production Brief
│   └── scripts/{channel_id}/  Claude 대본 (사람이 저장)
├── images/                    그래프 3개
├── analysis.py                과제용 그래프 + 인사이트
├── app.py                     Streamlit 화면
├── run_daily.cmd              작업 스케줄러가 부르는 것
├── .env                       API 키 (git 제외)
├── prd.md · task.md · tech.md · REPORT.md · README.md
└── requirements.txt
```

---

## ⭐ 1. 설정 — `src/config.py`

**값을 바꾸려면 여기만 고친다.** 코드에 숫자를 직접 쓰지 않는다.

```python
# 경로
DATA_RAW = ROOT / "data" / "raw"
VIDEOS_CSV = DATA_RAW / "videos.csv"
SNAPSHOTS_CSV = DATA_RAW / "video_snapshots.csv"

# 수집
SEEDS = ["老後", "お金", ...]          # 상한 15개
SEARCH_ORDERS = ["relevance", "date"]
REGION_CODE = "JP"                     # 검색 조건일 뿐 — 언어 판정에 쓰지 않는다
SEARCH_DAYS = 90

# 필터
LONGFORM_MIN_SECONDS = 600
JAPANESE_MIN_RATIO = 0.10

# Watchlist
WATCHLIST_MAX = 500
GRADUATE_AFTER_DAYS = 60
MIN_GAIN_HOURS = 6                     # 이보다 짧은 간격은 Gain 을 재지 않는다

# 점수 가중치
W_AGE_ADJUSTED = 0.6
W_SUBSCRIBER_RATIO = 0.4

# 할당량
SEARCH_COST = 100
DAILY_QUOTA = 10000
```

### ❌ 금지

```python
if duration < 600:                     # 매직 넘버
df[df["age_days"] <= 30]               # 임계값을 코드에 박음
path = "data/raw/videos.csv"           # 경로 직접 입력
score = a * 0.6 + b * 0.4              # 가중치를 코드에 박음
```

### ✅ 올바름

```python
from . import config

if secs < config.LONGFORM_MIN_SECONDS: ...
score = a * config.W_AGE_ADJUSTED + b * config.W_SUBSCRIBER_RATIO
open(config.VIDEOS_CSV, encoding="utf-8")
```

---

## ⭐ 2. 저장 — `src/storage.py`

**CSV 를 여는 코드는 이 파일에만 있다.** 다른 곳에서 `open(...csv)` 하지 않는다.

```python
read_videos()              # videos.csv 전부
known_video_ids()          # 중복 판정용 집합
append_videos(rows)        # 이미 있는 video_id 는 건너뜀
read_snapshots()
append_snapshots(rows)
snapshot_history()         # video_id → 스냅샷 목록 (시각 오름차순)
last_snapshot_by_video()   # video_id → 직전 관측
```

### 고정 정보와 변하는 정보를 나눈다

```
videos.csv           video_id · title · title_ko · published_at
                     duration_seconds · seed · found_at
video_snapshots.csv  collected_at · video_id · views · channel_subscribers
                     channel_video_count · watch_status
```

합치면 **고정 정보를 매일 다시 저장하게 된다.** 파일이 며칠 만에 몇 배가 된다.

### 🚨 열을 늘릴 때 — 헤더를 먼저 맞춘다

`csv.DictWriter` 는 **파일이 새로 만들어질 때만 헤더를 쓴다.** 그래서
`SNAPSHOT_FIELDS` 에 필드만 늘리면 헤더는 옛 칸 수 그대로인데 새 행은
칸이 늘어 붙어 **값이 한 칸씩 밀린다.**

에러가 나지 않는다. `watch_status` 자리에 엉뚱한 값이 들어앉을 뿐이다.

```python
_append()  →  _migrate_header(path, fields)  먼저 부른다
```

헤더가 다르면 파일을 새 헤더로 다시 쓴다. **옛 행의 새 칸은 빈 값**으로 둔다 —
0 으로 채우면 «영상 0개» 라는 거짓말이 된다.

필드를 늘릴 때 따로 할 일은 없다. `_append` 가 알아서 맞춘다.

### 인코딩

```python
open(path, encoding="utf-8", newline="")      # 항상 명시
```

윈도우 기본은 cp949 다. 안 적으면 일본어에서 죽는다.

---

## ⭐ 3. 지표 — `src/analysis.py`

**계산식은 여기에만 있다.** 화면(`app.py`)과 리포트(`analysis.py` 루트)가
같은 함수를 부른다. 따로 두면 화면 숫자와 리포트 숫자가 갈린다.

```python
build()     # 수집 → 지표 → 백분위 → 점수. 이것 하나만 부르면 된다
gains()     # 직전 관측 대비 하루치 증가
```

### 계산 규칙 — 어기면 조용히 틀린다

```python
# ADViews — 당일 영상은 0.5일로 하한. 안 두면 0 으로 나눈다
adviews = views / max(age_days, 0.5)

# Gain — «전날» 이 아니라 «직전 관측». 실제 경과일로 나눈다
gain = (views - prev_views) / (now - prev_at).days

# 간격이 너무 짧으면 재지 않는다
if elapsed < config.MIN_GAIN_HOURS / 24: skip

# 구독자 비공개는 0 이 아니라 결측
svr = views / subs if not hidden else None
```

### Age Bucket 은 매번 다시 정한다

영상은 매일 나이를 먹어 버킷이 바뀐다. **수집 시점에 고정하지 않는다.**
표본이 20건 미만이면 인접 버킷과 병합하고, 그래도 부족하면 전체 중앙값 대비로
물러선다. `age_bucket_n` 을 **반드시 함께 저장**해 신뢰도를 볼 수 있게 한다.

---

## ⭐ 4. YouTube 호출 — `src/youtube.py`

**API 를 부르는 코드는 이 파일에만 있다.**

```python
client = Client()                    # 키 없으면 안내와 함께 즉시 실패
client.search(q, order=...)          # 100 units — 아껴 쓴다
client.videos(ids)                   # 50개 묶어 1 unit
client.channels(ids)
client.playlist_items(playlist_id)
client.report()                      # "search 16회 · 그 외 15회 → 약 1615 units"
client.log_quota(note)               # quota_log.csv 에 기록
```

### 할당량 — 이 프로젝트의 유일한 하드 제약

```
search.list   100 units · 하루 실질 상한 약 100회
videos.list     1 unit  · 50개를 묶어 1회
하루 총량    10,000 units
```

| 규칙 | 이유 |
|---|---|
| 수집은 하루 1~2회 | 검색 16회 = 1,615 units |
| **분석은 CSV 만 읽는다** | 코드를 고칠 때마다 API 를 부르면 하루가 날아간다 |
| 화면은 API 를 부르지 않는다 | 필터를 만질 때마다 호출되면 몇 번에 소진 |
| 쓴 양을 `quota_log.csv` 에 기록 | 하루에 몇 번 돌렸는지 나중에 알 수 있다 |

### 같은 날 두 번 수집하지 않는다

수집 한 번이 **1,615 units** 이다. 여섯 번이면 하루치가 사라지고
**그날은 스냅샷도 못 남긴다** — 시계열에 구멍이 나는데
**지나간 날의 조회수는 다시 받을 수 없다.**

```python
Client.spent_today()             # 오늘 쓴 units
Client.spent_today("collector")  # 그중 수집 몫
```

`collector.py` 는 오늘 이미 수집했으면 **API 를 부르기 전에** 멈춘다.
정말 다시 돌려야 하면 `--force`.

실제로 개발 중 하루 5번을 돌려 8,075 units(81%)를 쓴 날이 있었다.

### 삭제된 영상은 에러가 아니다

`videos.list` 는 삭제·비공개 영상을 **조용히 빼고** 준다. 요청한 id 가 응답에
없으면 `watch_status = unavailable` 로 기록한다. 안 그러면 추적이 왜 끊겼는지
알 수 없다.

---

## ⭐ 5. 번역 — `src/translate.py` (제공자 교체 가능)

### 왜 이 구조인가

API 제공자는 몇 달이면 가격·모델·한도가 바뀐다. 같은 프로젝트군의
`automaker` 는 호출 코드가 **66곳에 흩어져** 있어 엔진 하나 바꾸는 것이
큰 공사였다. 여기서는 처음부터 한 곳에 모은다.

### 갈아타는 방법 — `config.py` 한 줄

```python
TRANSLATE_PROVIDER = "openai"        # ← 여기만 바꾼다
TRANSLATE_MODEL = "..."              # 모델 이름도 한 곳
TRANSLATE_ENABLED = True             # 끄면 원문만 보여준다
```

### 구조

```python
# src/translate.py

def _call_openai(prompt, key, model): ...
def _call_gemini(prompt, key, model): ...
def _call_claude(prompt, key, model): ...

PROVIDERS = {
    "openai": (_call_openai, "OPENAI_API_KEY"),
    "gemini": (_call_gemini, "GEMINI_API_KEY"),
    "claude": (_call_claude, "ANTHROPIC_API_KEY"),
}

def translate_titles(titles: list[str]) -> list[str]:
    """제목을 한글 한 줄로. 실패하면 빈 문자열을 돌려준다 — 죽지 않는다."""

def suggest_search_terms(korean: str) -> list[dict]:
    """한글 뜻 → 일본인이 실제로 칠 법한 검색어 후보 + 각각의 한글 뜻."""
```

**새 제공자를 붙이는 일 = 함수 하나 + `PROVIDERS` 한 줄 + `.env` 에 키 한 줄.**
호출하는 쪽(`collector.py` 등)은 손대지 않는다.

### 규칙

| | |
|---|---|
| **배치로 부른다** | 제목 60개를 한 번에. 60번 부르면 분당 한도에 걸린다 |
| **수집 시점에 한 번** | 결과를 `videos.csv` 의 `title_ko` 에 저장. 화면은 읽기만 |
| **실패해도 죽지 않는다** | 키가 없거나 한도를 넘으면 `title_ko` 를 비우고 원문만 표시 |
| **원문을 반드시 같이 보여준다** | 번역이 틀릴 수 있고, 복사해 넘길 때 원문이 필요하다 |
| **번역은 편의 기능이다** | 없어도 프로그램 전체가 돌아야 한다 |

### ⚠️ 제목과 낱말은 다른 함수로

```python
translate_titles(titles)   제목 → 무슨 내용인지 알 수 있는 한 줄
translate_terms(terms)     낱말 → 12자 이내의 «뜻»
```

`注文住宅` 의 뜻을 `translate_titles` 로 물었더니
**「나만의 맞춤형 주문주택 짓기 노하우」** 가 나왔다. 그 프롬프트는 «제목» 을
시키기 때문이다. **오류가 아니라 없는 제목을 지어낸 것**이라, 일본어를 모르면
그대로 낱말 뜻으로 믿는다.

### ⚠️ 단순 번역은 검색어로 쓸 수 없다

```
status anxiety  →  地位不安        사전적 번역. 아무도 이렇게 안 친다
실제 검색어      →  他人と比べる · 承認欲求 · 年収 比較 · SNS 疲れ
```

`suggest_search_terms` 는 **번역기가 아니라 «현지 검색어 후보 생성기»** 다.
프롬프트에 그렇게 지시하고, **각 후보에 한글 뜻을 붙여** 사람이 고를 수 있게 한다.

만든 검색어가 실제로 결과를 내는지는 검색해 봐야 아는데 **1회에 100 units** 다.
후보를 넣고 **다음 수집 결과로 판단**한다 — 성과가 없으면 뺀다.

### 모델 이름

`config.TRANSLATE_MODEL` 한 곳에 둔다. **모델은 사라지거나 이름이 바뀐다.**
호출이 «모델을 찾을 수 없음» 으로 실패하면 그 사실과 **어디를 고쳐야 하는지**를
메시지에 담는다.

```
번역 모델 '...' 을 쓸 수 없습니다.
  src/config.py 의 TRANSLATE_MODEL 을 확인하세요.
  번역 없이도 수집은 계속됩니다.
```

---

## ⭐ 6. 화면이 쓰는 것들 — `seeds` · `subtitles` · `export`

### `src/seeds.py` — 검색어

검색어는 **바뀌는 값이라 코드가 아니라 데이터**로 둔다.

```
data/raw/seeds.json     지금 쓰는 검색어 + 무시 목록
config.SEEDS            파일이 없을 때의 기본값
```

화면에서 `config.py` 를 고쳐 쓰면 **쓰다 실패했을 때 프로그램이 아예 안 뜬다.**

읽는 곳은 두 개뿐이다. `config.SEEDS` 를 직접 읽지 않는다.

```python
seeds.terms()    ["老後", "お金", ...]
seeds.labels()   {"老後": "노후", ...}   그래프 라벨용
```

**성과는 이상치 수로 줄 세운다. 중앙 점수가 아니다.**
찾는 것은 «구독자에 비해 유난히 잘 된 영상» 이지 «평균이 높은 주제» 가 아니다.
`住宅` 은 중앙 점수가 꼴찌인데 이상치는 두 번째로 많다 — 중앙값으로 빼면
가장 잘 잡아내는 검색어를 버린다.

`weakest()` 는 «영상 15건 이상 모았는데 이상치 0건» 인 것만 짚는다.
영상이 적으면 «성과가 없는 것» 이 아니라 «아직 모르는 것» 이다.

### `src/subtitles.py` — 자막 발췌

`yt-dlp` 로 자동자막을 받아 **앞 3분 · 반복 낱말 · 마지막 1분**만 남긴다.
20분물이 약 6,900자라 전체를 넣으면 부담이고, «이 소재를 할까 말까» 를
정하는 데는 앞뒤면 충분하다. 실측 발췌량 828~1,725자.

받은 자막은 `data/raw/subs/` 에 남긴다. 자막은 변하지 않는다.

**`429`(요청 과다)와 «자막 없음» 을 반드시 가른다.** 뭉뜽그리면 자막이 있는
영상을 «없음» 으로 적어 두고 그 소재를 영영 안 보게 된다.

```python
digest(vid)["why"]      사람이 읽을 이유
retryable(why)          다시 부르면 될 수도 있는가
```

### `src/export.py` — 붙여넣을 한 장

`one_pager(video_id) -> str`. 약 2,750자.

**숫자를 다시 계산하지 않는다.** `analysis.build()` 가 낸 값을 가져다 쓴다 —
두 곳에서 따로 계산하면 화면과 한 장이 어긋난다. (§2)

**빈 값을 `nan` 으로 내보내지 않는다.** Channel Score 가 비는 것은
«점수가 낮다» 가 아니라 «모른다» 다. 이유까지 적는다.

```
Channel Score 판정 못 함
(이 채널에서 찾은 롱폼이 4편뿐이라 비교할 과거 영상이 모자랍니다)
```

일본어는 띄어쓰기가 없어 `textwrap` 이 못 접는다. `「。」` 뒤에서 끊는다 —
한 줄로 두면 화면에서 오른쪽이 잘려 보내기 전에 확인할 수가 없다.

---

## ⭐ 6-B. 2채널 — `channels` · `channel_fit` · `comments` · `production_brief`

### Radar 는 하나다

```
공통 수집 → 공통 Video/Channel Score → 채널별로 «걸러 보기»
```

**데이터 파이프라인을 두 개 만들지 않는다.** Video Score 를 채널별로 다시
계산하지 않는다. 채널은 «같은 시장 데이터를 어느 관점으로 읽나» 일 뿐이다.

### Video/Channel Score 와 Channel Fit 은 다른 질문

```
Video Score    이 영상이 같은 나이대보다 강한가      시장
Channel Score  이 채널이 실제로 오르고 있는가        시장
Channel Fit    우리가 만들 가치가 있는가            우리
```

앞의 둘은 숫자다. **Channel Fit 은 숫자로 만들지 않는다.**
HIGH/MEDIUM/LOW 와 근거 문장만 쓴다 — 0~100 은 없는 정밀도를 꾸며 낸다.

### LLM 을 부르는 곳은 세 군데뿐

```
translate.translate_titles()   제목 한글화     수집 때 자동
translate.translate_terms()    낱말 뜻         검색어 화면
translate.ask_json()           그 밖           channel_fit · comments.analyze
```

전부 `translate.py` 의 제공자 계층을 지난다. 호출 코드를 흩으면 제공자를
갈아탈 때 다 찾아다녀야 한다.

**전체 영상에 돌리지 않는다.** Channel Fit 은 상위 후보만, 댓글은 사람이
«이걸 만들자» 고 고른 것만. 결과는 전부 캐시한다.

### 브리프는 조립만 한다

`production_brief.build()` 는 **새로 LLM 을 부르지 않는다.**
판정은 `channel_fit`, 댓글 해석은 `comments.analyze` 가 이미 했고,
제목·구성은 `prompts/script_writer.md` 가 낸다. 같은 것을 두 번 물으면
돈만 들고 두 답이 어긋난다.

### raw 를 LLM 에 넣지 않는다

```
자막   6,900~13,000자  →  digest_text()      최대 1,500자
댓글   50건            →  analysis_text()    최대 2,500자
```

---

## 🔑 7. 키 관리

### `.env` — git 에 올리지 않는다

```env
YOUTUBE_API_KEY=
OPENAI_API_KEY=
# GEMINI_API_KEY=        나중에 갈아탈 때
```

### 읽는 곳은 `config.py` 하나

```python
def api_key(name="YOUTUBE_API_KEY"):
    """환경변수 → .env 순으로 찾는다. 코드에 키를 적지 않는다."""
```

### ❌ 절대 금지

```python
KEY = "sk-..."                                  # 코드에 키
requests.get(url + "?key=AIza...")              # URL 에 키
print(f"key={key}")                             # 로그에 키
```

`.gitignore` 에 `.env` 가 있는지 **커밋 전에 확인한다.**

---

## 🖥️ 8. 화면 — `app.py`

### 디자인은 `.streamlit/config.toml` 에 있다

색·글꼴·모서리·표 머리글·그래프 색을 전부 **공식 테마 옵션**으로 정한다.
`mockup/index.html` 에서 정한 팔레트를 그대로 옮긴 것이다.

```
주황 #C1501C   영상(Video Score) · 기본 버튼
청록 #1C6577   채널(Channel Score) · 링크
바탕 #EDF1F0   초록 쪽으로 살짝 기운 중립색
레일 #101A1C   사이드바만 어둡게 ([theme.sidebar])
```

**Streamlit 내부 CSS 클래스를 건드리지 않는다.** 클래스 이름은 버전마다
바뀌어서, 그렇게 만든 디자인은 업그레이드 한 번에 조용히 무너진다.
`app.py` 의 `st.markdown(<style>)` 은 **글꼴 로드와 tabular-nums 세 줄뿐**이다.

두 점수를 색으로도 갈라 둔 이유는 §6-B 와 같다 — 합치면 안 되는 값이다.

### 규칙

| | |
|---|---|
| **CSV 만 읽는다** | 화면 조작이 API 를 부르면 하루 한도가 몇 번에 날아간다 |
| `@st.cache_data(ttl=60)` | 필터를 만질 때마다 CSV 를 다시 읽지 않는다 |
| 계산은 `src/analysis.py` | 화면에서 새로 계산하지 않는다 |
| 로컬만 연다 | `--server.address 127.0.0.1`. 기본값은 같은 네트워크에 열린다 |

### 표에는 [열기] 를 맨 앞에 둔다

숫자만 보고는 «이게 진짜인가» 를 확인할 수 없다. 소재를 고르는 일은
영상을 한 번 열어 봐야 끝난다.

**맨 뒤에 두면 안 된다.** Streamlit 표는 가로로 넘쳐서 마지막 칸이 화면 밖으로
밀린다. 확인하려고 누르는 버튼이 숨어 있으면 없는 것과 같다.

큰 숫자는 `format="localized"` 로. `2117606` 보다 `2,117,606` 이 훑기 쉽다.

### 🚨 `src/` 를 고쳤으면 Streamlit 을 다시 띄운다

`app.py` 는 저장하면 알아서 다시 뜨지만 **`src/` 밑 모듈은 옛 코드가 그대로
돈다.** 고친 것이 화면에 안 나타나거나 `KeyError` 가 나면 대개 이것이다.

```bash
powershell -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*streamlit*' } | Stop-Process -Force"
```

`Stop-Process` 가 조용히 실패하기도 한다. 죽었는지 **포트로 확인**한다 —
안 죽었으면 새로 띄운 것이 포트를 못 잡고 그냥 사라져, 옛 프로세스가 계속
답한다. 그러면 «고쳤는데 안 바뀐다» 로 한참 헤맨다.

### 새 수집은 명령으로만

```bash
python -m src.collector            # 수집
python -m src.snapshot_collector   # 매일 1회 (작업 스케줄러)
streamlit run app.py --server.address 127.0.0.1
```

---

## 🪟 9. 윈도우에서 걸리는 것

### 인코딩

```python
open(path, encoding="utf-8")                 # 항상 명시. 기본은 cp949
sys.stdout.reconfigure(encoding="utf-8")     # 콘솔 출력 전에
```

환경변수로도 못 박는다: `PYTHONIOENCODING=utf-8` · `PYTHONUTF8=1`

### `.cmd` 파일

| 규칙 | 안 지키면 |
|---|---|
| **CRLF 줄바꿈** | `The syntax of the command is incorrect` |
| **ASCII 만** | 콘솔 코드페이지에 따라 파싱이 흔들린다 |
| `cd /d "%~dp0."` | 점 없이 쓰면 끝의 역슬래시가 따옴표를 이스케이프해 경로가 깨진다 |
| **로그는 절대 경로** | `cd` 가 실패하면 로그가 엉뚱한 곳에 생기거나 안 생겨 실패를 못 본다 |

### 그래프 폰트

윈도우에 **한글과 일본 한자를 동시에 가진 폰트가 없다**(실측).

```
Malgun · Gulim · Batang    한글 O · 独 X
MS Gothic · Yu Gothic      한글 X · 独 O
```

**그래프 라벨은 한글로 쓴다** (`config.SEED_LABELS`). 일본어 원문은 CSV 와
화면에 그대로 둔다 — 화면은 브라우저가 그리므로 깨지지 않는다.

---

## 🚨 10. 알려진 함정 — 실제로 걸린 것들

**셋 다 에러 없이 그럴듯한 숫자로 나왔다.**

### ① ADViews 로 기간을 비교하면 안 된다

검색어별 성장률을 나이 보정 없이 계산했더니 **`+16,162%`** 가 나왔다.
`ADViews = 조회수 ÷ 경과일` 인데 조회수는 초기에 몰리고 분모는 계속 는다.
어린 영상일수록 구조적으로 높다.

나이를 통제해 다시 재자 **그 검색어가 8개 중 꼴찌**가 됐다.

→ 기간 비교에는 **게시 수(공급량)** 와 **같은 나이대 안에서의 성과**만 쓴다.

### ② Channel Baseline 도 같은 함정에 빠졌다

ADViews 로 계산했더니 **`2,941배`**. 그 채널의 중앙 ADViews 가 `4.1/일` 이었다 —
오래된 영상들이 `2.2 · 4.5 · 7.0` 으로 0 에 수렴해 있었다.

→ **조회수로 비교하고, 비교 대상은 «대상보다 오래된 영상»** 으로 한다.
비교 대상이 시간을 더 가졌는데도 이겼다면 진짜다. 값은 과소평가다.

### ③ 같은 날 두 번 돌리면 Gain 이 터진다

`Gain = 조회수차 ÷ 날짜차` 인데 47분 간격이면 `0.03일` 로 나눈다.
**12건의 잡음이 하루치 86,400건**이 된다.

→ `MIN_GAIN_HOURS = 6`. 간격이 짧으면 «아직 못 잰다» 로 둔다.

### ④ 스케줄러가 조용히 실패한다

`.cmd` 를 LF 로 저장해 `LastTaskResult: 1` 이 났는데, 로그도 안 생겨
**실패했다는 사실 자체가 안 보였다.**

→ 로그를 절대 경로로 쓴다. 등록 후 **한 번 돌려 `LastTaskResult: 0` 을 확인**한다.

### ⑤ 낱말을 제목 번역기로 옮기면 없는 제목을 지어낸다

`注文住宅` 의 뜻을 물었더니 **「나만의 맞춤형 주문주택 짓기 노하우」** 가 나왔다.
제목용 프롬프트를 낱말에 썼기 때문이다. 오류가 아니라 그럴듯한 거짓말이라,
일본어를 모르면 그대로 믿는다. → `translate_terms()` 를 따로 쓴다.

### ⑥ 중앙 점수로 검색어 순위를 매기면 거꾸로 짚는다

«성과가 낮은 검색어» 를 중앙 점수로 골랐더니 `住宅` 이 나왔다.
그런데 `住宅` 은 **이상치가 두 번째로 많은 검색어**였다. 편차가 큰 주제가
오히려 사냥터로 좋다. → 이상치 수로 줄 세운다.

### ⑦ CSV 에 열을 늘리면 값이 한 칸씩 밀린다

`DictWriter` 는 파일이 새로 생길 때만 헤더를 쓴다. 헤더는 옛 칸 수인데
새 행만 칸이 늘어 붙는다. **에러가 안 난다.**
→ `storage._migrate_header()` 가 붙이기 전에 맞춘다. (§2)

---

## 🏷️ 11. 네이밍

| 종류 | 규칙 | 예 |
|---|---|---|
| 모듈 | snake_case.py | `channel_analyzer.py` |
| 함수 | snake_case | `build_watchlist` · `report_gain` |
| 내부 전용 | `_` 접두 | `_age_days` · `_call_openai` |
| 상수 | UPPER_SNAKE | `LONGFORM_MIN_SECONDS` |
| CSV 열 | snake_case | `age_bucket_n` · `channel_baseline` |
| 지표 | 계산식 그대로 | `adviews` · `subscriber_view_ratio` |

---

## ✅ 12. 체크리스트

### 새 코드를 쓰기 전

- [ ] `src/storage.py` 에 같은 일을 하는 함수가 있는가?
- [ ] `src/analysis.py` 에 같은 계산이 있는가?
- [ ] 새로 쓰는 숫자가 `config.py` 에 있어야 할 값은 아닌가?

### 지표를 계산할 때

- [ ] 나이가 다른 것끼리 비교하고 있지 않은가? (§10-①②)
- [ ] 0 으로 나눌 수 있는가? 하한을 뒀는가?
- [ ] 결측을 0 으로 채우고 있지 않은가? (구독자 비공개 → 무한대)
- [ ] 표본 수를 같이 저장했는가?

### API 를 부를 때

- [ ] 검색을 몇 번 하는지 미리 세었는가?
- [ ] `--dry-run` 으로 비용을 먼저 볼 수 있는가?
- [ ] 응답에 빠진 id 를 처리했는가?
- [ ] `log_quota()` 를 불렀는가?

### 화면을 고쳤을 때

- [ ] `src/` 를 고쳤으면 Streamlit 을 **죽였다 다시 띄웠는가**
- [ ] 정말 죽었는지 포트로 확인했는가
- [ ] 새로 넣은 칸이 가로 스크롤에 가려 있지 않은가

### 돌린 뒤 — **가장 중요**

- [ ] **숫자를 눈으로 보고 «말이 되나» 따졌는가?**
- [ ] 몇 건 수집됐나 · 몇 건 통과했나 · 표본이 몇인가
- [ ] 이상하게 큰 값(수천 배·수만 %)이 있으면 **의심한다**
- [ ] 그래프는 실제로 그려서 본다. 라벨이 깨지지 않았는가?

### 커밋 전

- [ ] `.env` 가 `.gitignore` 에 있는가?
- [ ] 코드에 키가 없는가?
- [ ] `data/raw/*.csv` 를 올리려 하고 있지 않은가?

---

## ⛔ 13. 절대 금지

### 구조

- ❌ CSV 를 `storage.py` 밖에서 여는 것
- ❌ 임계값·가중치를 코드에 직접 쓰는 것
- ❌ 화면에서 API 를 부르는 것
- ❌ 지표를 화면과 리포트에서 각각 계산하는 것
- ❌ 외부 API 호출 코드를 `youtube.py` · `translate.py` 밖에 두는 것

### 데이터

- ❌ 나이가 다른 것을 ADViews 로 비교하는 것
- ❌ 결측을 0 으로 채우는 것
- ❌ 표본 수 없이 백분위만 보여주는 것
- ❌ 이상치를 제거하는 것 — **이 프로젝트에서 이상치는 찾는 대상이다**

### 그 밖

- ❌ 코드에 API 키
- ❌ `encoding=` 없이 파일 열기
- ❌ `.cmd` 를 LF 로 저장
- ❌ 검증 없이 «됐다» 고 말하는 것

---

## 🎯 요약 (한 줄씩)

1. **Python + Streamlit + CSV.** DB·서버·로그인 없음
2. **값은 전부 `config.py`** — 매직 넘버 금지
3. **CSV 는 `storage.py`, 지표는 `analysis.py`** 를 반드시 경유
4. **API 호출은 `youtube.py` · `translate.py`** 에만
5. **번역 제공자는 `config` 한 줄로 갈아탄다** — 새 제공자 = 함수 1개 + 목록 1줄
6. **번역이 실패해도 프로그램은 돈다** — 편의 기능이지 필수가 아니다
7. **할당량이 유일한 하드 제약** — 수집 하루 1~2회, 분석은 CSV 만
8. **나이가 다른 것을 비교하지 않는다** — 두 번 걸렸다
9. **윈도우: UTF-8 명시 · CRLF · 폰트는 한글로**
10. **에러가 없다는 것이 동작한다는 뜻이 아니다 — 숫자를 눈으로 본다**
