# -*- coding: utf-8 -*-
"""YouTube Data API 호출.

할당량을 직접 센다. search.list 는 videos.list 보다 100배 비싸고
실질 상한이 하루 약 100회라, 얼마나 썼는지 모르면 개발 중에 소진된다.

의존성을 늘리지 않으려고 표준 urllib 만 쓴다.
"""
import csv
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
    def units(self):
        return (self.search_calls * config.SEARCH_COST
                + self.cheap_calls * config.CHEAP_COST)

    def report(self):
        return (f"search {self.search_calls}회 · 그 외 {self.cheap_calls}회 "
                f"→ 약 {self.units} units")

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
                        self.cheap_calls, self.units, note])

    @classmethod
    def spent_today(cls, note=None):
        """이번 할당량 날짜에 쓴 units. note 를 주면 그 작업만 (예: "collector").

        수집은 한 번에 1,600 units 이 넘는다. 여섯 번이면 하루치가 없어져
        **그날은 더 못 모은다.** 조용히 바닥나지 않게 미리 세어 본다.

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
                    total += int(row.get("units") or 0)
                except ValueError:
                    pass
        return total

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
            except urllib.error.URLError as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"네트워크 오류: {e.reason}") from e

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


_DURATION = re.compile(r'^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$')


def parse_duration(iso):
    """ISO8601 (PT1H2M3S) 를 초로. 형식이 이상하면 0 을 준다."""
    m = _DURATION.match(iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s
