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
# run_daily.cmd 가 적는 실행 기록. 파이썬이 죽어도 «exit 1» 이 남는다 —
# quota_log 에 닿기 전에 죽는 실패를 알 수 있는 유일한 자리다.
RUN_LOG = DATA_RAW / "run_log.txt"

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

# 관측이 이만큼 벌어져야 «하루치» 라고 부를 수 있다.
#
# MIN_GAIN_HOURS(6) 는 «계산해도 되는가» 의 하한이고, 이것은 «추세라고
# 불러도 되는가» 의 선이다. 둘은 다른 질문이다.
#
# 실측 (2026-09-03): gain 202건이 **전부 간격 8.41시간** 하나였다(표준편차 0).
# 24시간 이상은 0건. 8.4시간을 하루로 환산하면 2.85배가 되는데, 조회수는
# 게시 직후에 몰리므로 그 구간을 선형으로 늘리면 과대평가된다.
#
# 순위는 왜곡되지 않는다 — 모든 영상이 같은 배율을 받기 때문이다.
# 왜곡되는 것은 절대값과 «하루» 라는 이름이다. 그래서 지우지 않고
# «초기 신호» 로 이름을 바꿔 부른다.
FULL_DAY_HOURS = 24

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

# ── 할당량 — 버킷이 둘이다 (2026-06-01 개편) ──────────────────────
# YouTube 가 세분화된 할당량 체계로 바꿨다. search.list 는 **자기 버킷**을 쓴다.
#
#   Revision History 2026-06-01
#     "API calls for the videos.insert and search.list methods are billed to
#      their respective quota buckets" — 그 외 메서드는 기존 버킷 그대로.
#     기본 배정: search.list 100회 · videos.insert 100회 ·
#                그 외 전부 합쳐 하루 10,000 units
#   https://developers.google.com/youtube/v3/revision_history
#
# ⚠️ Quota Calculator 페이지는 아직 옛 내용(search.list = 100 units)이다.
#    두 공식 문서가 어긋나 있으므로 Revision History 를 기준으로 삼는다.
#
# 옛 계산(search 100 units × 하루 10,000)과 **검색 쪽 결론은 우연히 같다** —
# 어느 쪽이든 하루 100회다. 달라진 것은 그 외 호출이다. 예전에는 검색과
# 예산을 나눠 썼지만 이제는 별개다. 스냅샷 하루치가 18 units 이니
# 일반 버킷은 사실상 비어 있다(0.2%). 조여 둘 이유가 없어졌다.
SEARCH_CALLS_DAILY_BUDGET = 100   # search.list 전용 버킷. 호출 1회 = 1 unit
GENERAL_DAILY_UNITS = 10_000      # videos.list · channels.list · 댓글 등 전부
CHEAP_COST = 1                    # 일반 메서드 1회당 units
SEARCH_WARN_AT = 60               # 한 번 실행에 검색이 이 이상이면 경고


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


# ── Opportunity Zone — 어디서 소재를 발굴할 것인가 ────────────────────
# 이 프로그램은 «큰 채널의 인기 영상» 을 찾는 도구가 아니다.
# **작은 채널에서 구독자에 비해 유난히 크게 반응한 소재** 를 찾는 도구다.
#
# 그래서 구독자 규모로 셋으로 나눈다. 자르는 것이 아니라 «먼저 보는 순서» 다.
# 어느 군도 데이터에서 지우지 않는다 — C 군은 제목·구성·길이의 참고 자료다.
#
# 근거 (2026-09-03 · 777건, 구독자 확인 632건)
#
#   구독자 대비 조회수(중앙값)가 규모가 커질수록 무너진다.
#     ~1만    297건  1.4배        10~30만   79건  0.6배
#     1~5만    92건  0.9배        30~100만  46건  0.3배
#     5~10만   50건  0.6배        100~300만 28건  0.1배
#                                 300만+    18건  0.0배
#   300만+ 의 조회수는 «영상이 잘된 것» 이 아니라 «채널이 커서 나온 것» 이다.
#   그 안에 우리가 따라할 기법은 없다.
#
#   5만 이하가 411건(52.9%)이라 발굴군으로 삼아도 표본이 모자라지 않는다.
#   1만 이하로 좁히면 297건이 남지만 Video Score 중앙값이 32.4 로 전 구간
#   최저다 — 작은 채널 영상 대부분은 그냥 안 된 영상이다. 그래서 규모만으로
#   고르지 않고 아래 «배수» 를 반드시 함께 본다.
#
#   5~10만을 버리지 않는 이유는 실제 사례가 있어서다.
#     トレイダーズ証券   53,400명 / 875,415회 = 16.4배  (Video Score 97.2)
#     超夢の推しシネマ   69,000명 / 589,867회 =  8.5배  (95.1)
#   5만이라는 선에 자연법칙은 없다. 건수는 적고 품질은 최상이라 보조군으로 둔다.
OPPORTUNITY_ZONE_MAX_SUBSCRIBERS = 50_000     # A군 — 핵심 발굴
SECONDARY_ZONE_MAX_SUBSCRIBERS  = 100_000     # B군 — 보조 관찰 (그 위는 C군)

# 배수가 높아도 조회수가 작으면 수요의 증거가 못 된다.
#
#   A군에서 «3배 이상» 이 135건인데, 조회수 2만 하한을 걸면 75건으로 준다.
#   빠지는 60건(44%)은 구독 1,200명에 4,000회 같은 것들이다.
#   분모 방어(MIN_SUBSCRIBERS_FOR_RATIO)만으로는 이걸 못 거른다 —
#   그쪽은 «분모가 작은 것», 이쪽은 «분자가 작은 것» 을 막는다.
OPPORTUNITY_MIN_VIEWS = 20_000

# 배수 등급. subscriber_view_ratio 를 그대로 쓴다 —
# 그 열은 이미 구독자 하한(1,000)·비공개·매크 방어를 다 통과한 값이다.
# 여기서 다시 나누면 그 방어를 우회하게 된다.
#
#   같은 A군에서 등급이 실제로 갈린다 (조회수 2만·매크 방어 적용 후, 73건)
#     10배 이상 34건 · 5~10배 22건 · 3~5배 17건
#
# 하한을 3배로 둔 이유: 2배까지 내리면 «채널 평균보다 조금 나은 영상» 이
# 섞여 들어와 목록이 평범해진다. 3배는 눈에 띄게 다른 것만 남긴다.
OPPORTUNITY_RATIO_WATCH       = 3     # 🟡 관찰
OPPORTUNITY_RATIO_STRONG      = 5     # 🟠 주목
OPPORTUNITY_RATIO_VERY_STRONG = 10    # 🔥 강력

# ── 참여율 하한 — 매크(사서 본 조회수) 방어 ──────────────────────────
# 근거: github.com/shkuratovdesigner/yuben-app (2026-09 벤치마킹, docs/benchmark.md).
# 「조회수 1,000회당 좋아요 1.5개 미만이면 매크로 본다」는 문턱을 그대로
# 가져오되, 우리 데이터로 다시 확인했다 (2026-09-02 · 623건, likes 있는 것만).
#
#   참여율 중앙 9.15 · 25% 5.05 · 75% 17.33
#   1.5 미만  67건 (10.6%)
#
# 1.5 는 우리 분포에서도 뚜렷한 하위 극단이라 그대로 쓴다.
# 지금 이 순간 데이터에는 「1.5 미만 & 구독대비 5배 이상」이 0건이라 매크가
# 이상치 목록을 오염시키고 있다는 증거는 아직 없다. 다만 롱테일 검색어가
# 늘면서 구독자가 아주 적은 채널이 많이 들어오고 있어(§9 참고), 방어선을
# 미리 깔아 둔다 — 걸리고 나서 고치면 그 사이 뽑은 후보가 이미 오염된다.
#
# «없다» 와 «못 잰다» 를 가른다 — likes 가 없는 영상(9건)은 매크로 몰지
# 않는다. 모르는 것을 나쁜 것으로 취급하면 안 된다.
MIN_ENGAGEMENT_PER_1K = 1.5

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


# ── 화면 ─────────────────────────────────────────────────────────
# 「오늘 볼 것」 카드 개수.
#
# 표는 전부를 보여 주고 카드는 «먼저 볼 것» 만 보여 준다. 많이 띄우면
# 표와 다를 게 없어진다 — 아침에 5분 안에 정하는 것이 목적이므로
# 스크롤 없이 훑을 수 있는 수로 둔다.
CARD_TOP = 5
