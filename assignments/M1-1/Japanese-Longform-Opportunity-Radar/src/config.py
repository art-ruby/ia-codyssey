# -*- coding: utf-8 -*-
"""설정을 한 곳에 모은다.

값을 바꾸려면 여기만 고친다. 코드 곳곳에 숫자를 흩어 놓으면
나중에 무엇을 바꿨는지 알 수 없다.

근거: docs v5 개발확정본
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

VIDEOS_CSV = DATA_RAW / "videos.csv"
SNAPSHOTS_CSV = DATA_RAW / "video_snapshots.csv"
QUOTA_LOG = DATA_RAW / "quota_log.csv"

# ── 검색 ──────────────────────────────────────────────────────────
# Seed 5~8개. 늘리면 검색 횟수가 배로 늘어 하루 상한(약 100회)에 닿는다.
#
# 이 리스트는 data/raw/seeds.json 이 아예 없을 때(신규 설치)의 기본값일
# 뿐이다 — 실제 운영 중인 검색어는 seeds.json 에 있고, 그 파일은 로컬
# 데이터라 git 대상이 아니다(.gitignore). 채널별 실제 검색 전략(어떤
# 문제형 검색어를 쓰는지, 어느 채널에 태깅했는지)은 여기 코드가 아니라
# 그 로컬 파일에만 있다 — src/seeds.py 의 add()/remove()/records() 로
# 화면에서 채워 넣는다.
SEEDS = ["老後", "お金", "仕事", "孤独", "AI", "人生", "SNS", "住宅"]

SEARCH_ORDERS = ["relevance", "date"]

# 그래프 라벨용 한글 이름.
#
# 윈도우에 한글과 일본 한자를 동시에 가진 폰트가 없다(실측).
#   Malgun · Gulim · Batang   한글 O · 独 X
#   MS Gothic · Yu Gothic     한글 X · 独 O
# 그래서 matplotlib 그래프에서 「孤独」이 「孤」로 잘린다. 폰트를 섞어 봐도
# 라벨 위치가 틀어지거나 사라졌다.
#
# 그림에서는 한글로 쓰고, 일본어 원문은 CSV 와 웹화면에 그대로 둔다.
# 웹은 브라우저가 그리므로 글자가 깨지지 않는다.
SEED_LABELS = {
    "老後": "노후", "お金": "돈", "仕事": "일", "孤独": "고독",
    "AI": "AI", "人生": "인생", "SNS": "SNS", "住宅": "주택",
}

# regionCode·relevanceLanguage 는 «검색 조건» 일 뿐이다.
# 응답의 영상 속성이 아니므로 언어 판정에 쓰지 않는다. (v5 §2)
REGION_CODE = "JP"
RELEVANCE_LANGUAGE = "ja"

# 첫 수집은 any 로 시작한다. 롱폼 확보율을 실측한 뒤 medium+long 으로
# 바꿀지 정한다 — 문서로 미리 정하지 않는다. (v5 §12)
VIDEO_DURATION = "any"

SEARCH_DAYS = 90          # 최근 며칠 안에 게시된 영상만
MAX_PAGES_PER_QUERY = 1   # 1페이지 = 50건. 늘리면 검색 비용도 는다

# ── 필터 ──────────────────────────────────────────────────────────
LONGFORM_MIN_SECONDS = 600        # 10분
JAPANESE_MIN_RATIO = 0.10         # 제목+설명에서 일본 문자 비율

# ── Watchlist ────────────────────────────────────────────────────
WATCHLIST_REGISTER_TOP = 100      # Video Score 상위 몇 개를 등록하나
WATCHLIST_MAX = 500               # 상한. 넘으면 우선순위 낮은 것부터 졸업
GRADUATE_AFTER_DAYS = 60          # 게시 후 이만큼 지나면 졸업 후보
MIN_SNAPSHOTS_FOR_GAIN_GRADUATION = 7   # 관측이 이만큼 쌓여야 Gain 으로 판정

# Gain 을 계산할 최소 관측 간격(시간).
#
# Gain = 조회수차 ÷ 날짜차 인데, 같은 날 두 번 돌리면 날짜차가 0.007일 같은
# 값이 되어 어떤 변화든 하루치로 환산하면 터무니없이 부풀어 오른다.
# 조회수는 몇 분 사이에도 몇 건씩 늘기 때문에 그 잡음이 그대로 증폭된다.
# 간격이 이보다 짧으면 «아직 못 잰다» 로 두고 계산하지 않는다.
MIN_GAIN_HOURS = 6

PRIORITY_A_TOP = 30               # TOP 30 = Priority A

# ── Age Bucket ───────────────────────────────────────────────────
# (이름, 최소일, 최대일)
AGE_BUCKETS = [
    ("0-3", 0, 3),
    ("4-7", 4, 7),
    ("8-14", 8, 14),
    ("15-30", 15, 30),
    ("31-90", 31, 90),
]
MIN_BUCKET_N = 20                 # 이보다 적으면 인접 버킷과 병합

# ── 점수 가중치 (v4 §21 유지) ────────────────────────────────────
W_AGE_ADJUSTED = 0.6
W_SUBSCRIBER_RATIO = 0.4
W_CHANNEL_BASELINE = 0.6
W_CHANNEL_MOMENTUM = 0.4

# ── 번역 ─────────────────────────────────────────────────────────
#
# 제공자는 몇 달이면 가격·모델·한도가 바뀐다. 갈아타는 일이 큰 공사가 되지
# 않도록 «어디를 고치면 되는지» 를 이 네 줄로 못 박는다.
# 새 제공자를 붙이는 일 = translate.py 에 함수 1개 + PROVIDERS 한 줄.
# PROVIDER 는 «말하는 규격» 이고 MODEL 은 «누구에게 시키나» 다. 서로 다른 축이다.
# 지금은 Codyssey 프록시가 OpenAI 규격으로 Gemini·Claude·GPT 를 모두 열어 준다.
# 그래서 규격은 openai 인데 모델은 gemini 일 수 있다.
#
# 모델 이름은 추측하지 않는다. 바뀌면 아래 한 줄로 다시 맞춘다.
#   python tools/setup_translate.py https://copa.codyssey.kr/v1
TRANSLATE_ENABLED = True
TRANSLATE_PROVIDER = "openai"                       # 규격: openai · gemini · claude
TRANSLATE_MODEL = "gemini-3-flash"                  # 모델
TRANSLATE_BASE_URL = "https://copa.codyssey.kr/v1"  # 비우면 제공자 기본 주소
TRANSLATE_BATCH = 60                   # 한 번에 묶어 보낼 제목 수.
                                       # 낱개로 부르면 분당 요청 한도에 걸린다
TRANSLATE_TIMEOUT = 60

# ── 할당량 ───────────────────────────────────────────────────────
# search.list 는 videos.list 보다 100배 비싸다. 실질 상한은 하루 약 100회.
SEARCH_COST = 100
CHEAP_COST = 1
DAILY_QUOTA = 10000
SEARCH_WARN_AT = 60               # 한 번 실행에 이 이상이면 경고

# 하루 실질 검색(Search Queries) 상한 — DAILY_QUOTA 를 SEARCH_COST 로 나눈 값.
# 사람에게 보여줄 때는 "units/10000" 보다 "호출 N/100회 = N%" 가 더 직관적이라
# collector·migrate_seeds 의 화면 출력이 이 상수를 기준으로 % 를 계산한다.
SEARCH_CALLS_DAILY_BUDGET = DAILY_QUOTA // SEARCH_COST   # = 100


# ── 작은 채널 기준 ───────────────────────────────────────────────
# 우리가 찾는 것은 «구독자에 비해 유난히 잘 된 영상» 이다. 그 선을
# 하드코딩하지 않고 실제 분포를 보고 정했다 (2026-09-02 · 632건).
#
#   구독자 중앙 10,000 · 25% 1,270 · 75% 107,000
#
#   1만 이하   319건 중 구독대비 5배 이상 79건 (25%)
#   5만 이하   411건 중                93건 (23%)
#   10만 이하  461건 중                96건 (21%)
#
# 이상치 밀도가 가장 높은 구간이자 수집분의 중앙값이라 1만으로 둔다.
# 분포는 수집이 쌓이면 달라진다. 바뀌면 여기만 고친다.
SMALL_CHANNEL_MAX_SUBSCRIBERS = 10_000

# 구독자가 이보다 적으면 «구독 대비 조회수» 를 계산하지 않는다.
#
# 분모가 작으면 비율이 잡음이 된다. 구독 6명 채널이 1,461회를 받으면
# 244배가 되어 이상치 1위로 올라오는데, 이것은 «유난히 잘 됐다» 가 아니라
# «구독자가 거의 없다» 는 말일 뿐이다. 조회수 1,461회는 수요의 증거가 못 된다.
#
# 롱테일 검색어를 넣은 뒤 구독 100명 미만 영상이 82건 들어왔다(2026-09-02).
# 넓은 낱말로 모을 때는 2건뿐이었다 — 검색어가 좁을수록 이 잡음이 늘어난다.
#
# 0 으로 채우지 않고 결측으로 둔다. «비율이 0» 과 «비율을 못 잰다» 는 다르다.
MIN_SUBSCRIBERS_FOR_RATIO = 1_000

# ── 댓글 ─────────────────────────────────────────────────────────
# 전체 영상에서 받지 않는다. **고른 제작 후보만.** (지시서 §31·§58)
# commentThreads.list 는 1 unit 이지만, 수백 건을 자동으로 받으면
# 그것대로 쌓이고 무엇보다 읽지도 않을 것을 받게 된다.
COMMENTS_MAX_COUNT = 50

# ── Channel Fit ──────────────────────────────────────────────────
# LLM 판정이라 전체에 돌리지 않는다. Video Score 상위 후보만. (§23)
CHANNEL_FIT_TOP_N = 20

# ── LLM 에 넣는 양 ───────────────────────────────────────────────
# raw 자막·댓글을 통째로 넣지 않는다. 요약본만 넣는다. (§37·§38)
TRANSCRIPT_DIGEST_MAX_CHARS = 1500
COMMENT_ANALYSIS_MAX_CHARS = 2500
PRODUCTION_BRIEF_MAX_CHARS = 8000


def api_key(name="YOUTUBE_API_KEY"):
    """환경변수 → .env 순으로 키를 찾는다. 코드에 절대 적지 않는다.

    키를 읽는 곳은 이 함수 하나다. 여기저기서 .env 를 파싱하면
    제공자를 갈아탈 때 고칠 자리를 다 찾아야 한다.
    """
    key = os.environ.get(name, "").strip()
    if key:
        return key

    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            found, _, value = line.partition("=")
            if found.strip() == name:
                return value.strip().strip('"').strip("'")
    return ""
