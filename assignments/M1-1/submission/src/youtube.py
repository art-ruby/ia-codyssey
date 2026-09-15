# -*- coding: utf-8 -*-
"""YouTube Data API 호출.

할당량을 직접 센다. search.list 는 videos.list 보다 100배 비싸고
실질 상한이 하루 약 100회라, 얼마나 썼는지 모르면 개발 중에 소진된다.

의존성을 늘리지 않으려고 표준 urllib 만 쓴다.
"""
import csv
import http.client
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

from . import config

BASE = "https://www.googleapis.com/youtube/v3"


class QuotaError(RuntimeError):
    """할당량 소진. 다음날까지 기다려야 한다."""


class CommentsDisabled(RuntimeError):
    """이 영상은 댓글을 꺼 두었다. 다시 받아도 소용없다."""


class VideoNotFound(RuntimeError):
    """삭제·비공개. 다시 받아도 소용없다."""


class Client:
    def __init__(self, key=None):
        # None 은 «설정에서 찾아라», 빈 문자열은 «키가 없다» 다. `or` 로
        # 뭉뜽그리면 Client(key="") 가 조용히 .env 의 키를 쓴다 —
        # 키 없는 상황을 시험할 수가 없다.
        self.key = config.api_key() if key is None else key
        if not self.key:
            raise RuntimeError(
                "YOUTUBE_API_KEY 가 없습니다.\n"
                "  .env 파일을 만들고 다음 한 줄을 넣으세요:\n"
                "    YOUTUBE_API_KEY=발급받은키\n"
                "  발급: Google Cloud Console → YouTube Data API v3 사용 설정 → API 키"
            )
        self.search_calls = 0
        self.cheap_calls = 0

    @property
    def general_units(self):
        """일반 버킷(10,000/일)에서 쓴 units.

        **search.list 는 여기 들어가지 않는다.** 2026-06-01 부터 자기 버킷을
        쓴다(config 주석 참고). 검색은 `search_calls` 로 따로 센다 — 둘을
        더하면 «검색 24회 = 2,400 units» 처럼 있지도 않은 소비가 만들어진다.
        """
        return self.cheap_calls * config.CHEAP_COST

    def report(self):
        return (f"search {self.search_calls}/{config.SEARCH_CALLS_DAILY_BUDGET}회 "
                f"· 그 외 {self.cheap_calls}회 = {self.general_units} units"
                f"/{config.GENERAL_DAILY_UNITS:,}")

    @staticmethod
    def quota_day():
        """지금이 속한 «할당량 날짜».

        **한국 날짜가 아니다.** YouTube 할당량은 태평양시 자정에 리셋된다 —
        UTC 07:00, 한국시간 16:00 이다. 한국 날짜로 세면 두 가지가 어긋난다.

            한국 00:00 ~ 16:00   우리는 «새 날» 인데 YouTube 는 아직 어제 →
                                 이미 쓴 양을 0 으로 보고 더 써서 **초과**한다
            한국 16:00 이후      YouTube 는 리셋됐는데 우리는 «아직 오늘» →
                                 남았는데도 **못 쓰게 막는다**

        전자가 위험하다. 초과하면 그날 남은 시간 동안 아무것도 못 받고
        스냅샷도 못 남겨 시계열에 구멍이 난다.
        """
        return (datetime.now(timezone.utc) - timedelta(hours=7)).date().isoformat()

    def log_quota(self, note=""):
        """쓴 양을 파일에 남긴다. 하루에 몇 번 돌렸는지 나중에 알 수 있다."""
        config.DATA_RAW.mkdir(parents=True, exist_ok=True)
        new = not config.QUOTA_LOG.exists()
        with open(config.QUOTA_LOG, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["date", "search_calls", "cheap_calls", "units", "note"])
            w.writerow([self.quota_day(), self.search_calls,
                        self.cheap_calls, self.general_units, note])

    @classmethod
    def _sum_today(cls, column, note=None):
        """이번 할당량 날짜의 한 열을 더한다.

        2026-09-02 이전 기록은 한국 날짜로 적혀 있었다. 그대로 두면 전날 쓴
        양이 오늘로 잡혀 **남았는데도 막는다.** 스냅샷 타임스탬프로 실제 실행
        시각을 확인해 태평양시 날짜로 한 번 정정했다(`quota_log.bak_*` 에 원본).
        """
        if not config.QUOTA_LOG.exists():
            return 0
        today, total = cls.quota_day(), 0
        with open(config.QUOTA_LOG, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("date") != today:
                    continue
                if note and note not in (row.get("note") or ""):
                    continue
                try:
                    total += int(row.get(column) or 0)
                except ValueError:
                    pass
        return total

    @classmethod
    def searches_today(cls, note=None):
        """이번 할당량 날짜에 쓴 **검색 횟수.** 하루 100회가 실질 상한이다.

        예전에는 units 하나로 셌다. 그러면 스냅샷·채널검증 같은 싼 호출이
        검색 예산을 갉아먹는 것처럼 계산돼, 남았는데도 수집을 막았다.
        버킷이 갈렸으니 세는 것도 갈라야 한다.
        """
        return cls._sum_today("search_calls", note)

    @classmethod
    def general_units_today(cls, note=None):
        """이번 할당량 날짜에 일반 버킷(10,000)에서 쓴 units.

        `units` 열은 2026-09-03 에 «일반 버킷 units» 로 의미를 바꾸고 옛 줄도
        같이 고쳤다(원본은 `quota_log.bak_*`). 옛 값은 검색×100 을 포함하고
        있어 그대로 두면 한 열에 두 뜻이 섞인다.
        """
        return cls._sum_today("units", note)

    def _get(self, path, params, cost_is_search=False):
        params = {k: v for k, v in params.items() if v not in (None, "")}
        params["key"] = self.key
        url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)

        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    data = json.load(r)
                if cost_is_search:
                    self.search_calls += 1
                else:
                    self.cheap_calls += 1
                return data
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                if e.code == 403 and "quota" in body.lower():
                    raise QuotaError(
                        "할당량을 다 썼습니다. 태평양시 자정에 초기화됩니다.\n"
                        "  이미 받아 둔 data/raw 의 CSV 로 분석은 계속할 수 있습니다."
                    ) from e
                if e.code in (500, 503) and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"HTTP {e.code}: {body[:300]}") from e
            # urllib.error.URLError 만 잡으면 **가장 흔한 오류가 빠진다.**
            #
            # http.client.RemoteDisconnected("Remote end closed connection
            # without response") 는 URLError 가 아니라 HTTPException 이자
            # ConnectionResetError 다. urllib 이 감싸 주지 않아 이 재시도를
            # 그대로 통과해 프로세스를 죽인다.
            #
            # 2026-09-03 08:57 의 자동 실행이 정확히 이것으로 죽었다.
            # 그날 스냅샷이 0건이 됐고 화면에는 아무 표시도 없었다
            # (`data/raw/run_log.txt`). 재시도가 있는데도 없는 것과 같았다.
            except (urllib.error.URLError, http.client.HTTPException,
                    ConnectionError, TimeoutError) as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                why = getattr(e, "reason", None) or f"{type(e).__name__}: {e}"
                raise RuntimeError(f"네트워크 오류: {why}") from e

    def search(self, q, order="relevance", published_after=None,
               video_duration="any", max_results=50, page_token=None):
        """search.list — 100 units. 아껴 쓴다."""
        return self._get("search", {
            "part": "snippet", "type": "video", "q": q, "order": order,
            "regionCode": config.REGION_CODE,
            "relevanceLanguage": config.RELEVANCE_LANGUAGE,
            "videoDuration": video_duration,
            "publishedAfter": published_after,
            "maxResults": max_results, "pageToken": page_token,
        }, cost_is_search=True)

    def videos(self, video_ids):
        """videos.list — 50개까지 묶어 1 unit.

        요청한 id 가 응답에 없으면 삭제·비공개다. 에러가 아니라 조용히 빠진다.
        호출부가 그 차이를 알 수 있도록 dict 로 돌려준다.
        """
        out = {}
        ids = list(video_ids)
        for i in range(0, len(ids), 50):
            chunk = ids[i:i + 50]
            data = self._get("videos", {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(chunk), "maxResults": 50,
            })
            for item in data.get("items", []):
                out[item["id"]] = item
        return out

    def channels(self, channel_ids):
        out = {}
        ids = list(channel_ids)
        for i in range(0, len(ids), 50):
            chunk = ids[i:i + 50]
            data = self._get("channels", {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(chunk), "maxResults": 50,
            })
            for item in data.get("items", []):
                out[item["id"]] = item
        return out

    def resolve_channel(self, text):
        """URL·핸들·UC아이디를 UC 채널 id 로 바꾼다. 못 풀면 None.

        · UC 아이디      → 그대로 (검증은 collect 가 한다). 호출 0
        · @handle        → channels.list(forHandle)   1 unit
        · /user/name     → channels.list(forUsername) 1 unit
        · /c/name·검색어 → search.list(type=channel)   100 units (최후의 수단)

        검색은 100배 비싸므로 되도록 안 탄다 — 붙여 넣는 것이 대개 핸들 URL 이다.
        """
        kind, value = parse_channel_ref(text)
        if kind == "id":
            return value
        if kind == "handle":
            data = self._get("channels", {"part": "id", "forHandle": value})
            items = data.get("items", [])
            return items[0]["id"] if items else None
        if kind == "username":
            data = self._get("channels", {"part": "id", "forUsername": value})
            items = data.get("items", [])
            return items[0]["id"] if items else None

        # query — 커스텀(/c/) 이나 맨 이름. 검색으로 찾는다(비싸다).
        if not value:
            return None
        data = self._get("search", {
            "part": "id", "type": "channel", "q": value, "maxResults": 1,
        }, cost_is_search=True)
        for item in data.get("items", []):
            cid = item.get("id", {}).get("channelId")
            if cid:
                return cid
        return None

    def comment_threads(self, video_id, max_results=50, order="relevance"):
        """commentThreads.list — 1 unit.

        댓글이 꺼져 있으면 403 을 준다. 이것은 **오류가 아니라 상태**다 —
        «일시 오류» 와 뭉뜽그리면 나중에 다시 받아야 할 것을 «댓글 없음» 으로
        적어 두게 된다. 그래서 여기서 예외를 사유별로 다시 던진다.
        """
        try:
            return self._get("commentThreads", {
                "part": "snippet", "videoId": video_id,
                "maxResults": min(max_results, 100), "order": order,
                "textFormat": "plainText",
            })
        except RuntimeError as e:
            body = str(e).lower()
            if "disabled comments" in body or "commentsdisabled" in body:
                raise CommentsDisabled(video_id) from e
            if "http 404" in body or "videonotfound" in body:
                raise VideoNotFound(video_id) from e
            raise

    def playlist_items(self, playlist_id, max_results=50):
        data = self._get("playlistItems", {
            "part": "contentDetails", "playlistId": playlist_id,
            "maxResults": max_results,
        })
        return [i["contentDetails"]["videoId"] for i in data.get("items", [])]


_UC_ID = re.compile(r'(UC[0-9A-Za-z_\-]{22})')
_HANDLE = re.compile(r'[0-9A-Za-z_.\-]+')


def parse_channel_ref(text):
    """손으로 넣은 채널 표시를 «무엇인지» 로 나눈다. **네트워크를 쓰지 않는다.**

    돌려주는 것은 (kind, value):
      ("id", "UC…")          채널 id 나 /channel/UC… 주소
      ("handle", "@name")    @핸들 이나 /@name 주소 (@ 를 붙여 준다)
      ("username", "name")   옛날 /user/name 주소
      ("query", "…")         /c/커스텀·맨 이름·빈값 — 검색으로만 풀린다

    실제로 붙여 넣는 것은 대개 `youtube.com/@handle` 이다.
    """
    s = (text or "").strip()
    if not s:
        return ("query", "")

    m = re.search(r'/channel/(UC[0-9A-Za-z_\-]{22})', s)
    if m:
        return ("id", m.group(1))
    if _UC_ID.fullmatch(s):
        return ("id", s)

    m = re.search(r'/@([0-9A-Za-z_.\-]+)', s)
    if m:
        return ("handle", "@" + m.group(1))
    if s.startswith("@") and _HANDLE.fullmatch(s[1:]):
        return ("handle", s)

    m = re.search(r'/user/([0-9A-Za-z_.\-]+)', s)
    if m:
        return ("username", m.group(1))

    m = re.search(r'/c/([^/?#]+)', s)
    if m:
        return ("query", urllib.parse.unquote(m.group(1)))

    return ("query", s)


_DURATION = re.compile(r'^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$')


def parse_duration(iso):
    """ISO8601 (PT1H2M3S) 를 초로. 형식이 이상하면 0 을 준다."""
    m = _DURATION.match(iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s
