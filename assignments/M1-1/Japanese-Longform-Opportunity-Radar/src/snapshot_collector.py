# -*- coding: utf-8 -*-
"""매일 도는 스냅샷 — 추적 목록의 조회수를 하루 한 줄씩 쌓는다.

    python -m src.snapshot_collector

이것이 이 프로젝트의 «진짜 시계열» 을 만든다. 영상 하나의 스냅샷 한 장으로는
그 영상이 처음부터 잘 됐는지 지금 막 터지는지 알 수 없다.

싸다. videos.list 는 50개를 묶어 1 unit 이라 500개를 추적해도 하루 10 units 다.
늦게 시작해서 잃는 것만 있고, 일찍 시작해서 잃는 것은 없다.
"""
import sys
from datetime import datetime, timezone

if __package__ in (None, ""):
    sys.exit("python -m src.snapshot_collector 로 실행하세요")

from . import config, storage
from .youtube import Client, QuotaError


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _days_since(iso):
    try:
        t = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        return max((datetime.now(timezone.utc) - t).total_seconds() / 86400, 0.0)
    except Exception:
        return 0.0


def _num(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def build_watchlist(videos, history):
    """무엇을 추적할지 정한다.

    v5 §5 의 규칙을 그대로 옮긴다.

      졸업   게시 후 60일 초과
             또는 스냅샷 7회 이상 쌓였는데 최근 Gain 이 계속 0에 가까움
      상한   500개. 넘으면 Video Score 가 없는 지금은 최신 발견 순으로 남긴다
    """
    active, graduated = [], []
    for v in videos:
        vid = v.get("video_id")
        if not vid:
            continue

        age = _days_since(v.get("published_at"))
        rows = history.get(vid, [])

        if age > config.GRADUATE_AFTER_DAYS:
            graduated.append((vid, "60일 초과"))
            continue

        # Gain 기준 졸업은 관측이 충분히 쌓인 뒤에만 본다.
        # 갓 등록한 영상은 관측이 2~3회뿐이라 판정 자체가 불가능하다.
        if len(rows) >= config.MIN_SNAPSHOTS_FOR_GAIN_GRADUATION:
            recent = rows[-config.MIN_SNAPSHOTS_FOR_GAIN_GRADUATION:]
            gain = _num(recent[-1].get("views")) - _num(recent[0].get("views"))
            if gain <= 0:
                graduated.append((vid, "증가 없음"))
                continue

        active.append(v)

    # 상한 초과 시 무엇을 먼저 빼는가. Video Score 가 아직 없는 단계에서는
    # 최근에 발견된 것을 남긴다 — 오래 추적한 것일수록 이미 자료가 있다.
    over = []
    if len(active) > config.WATCHLIST_MAX:
        active.sort(key=lambda v: v.get("found_at", ""), reverse=True)
        over = [(v["video_id"], "상한 초과") for v in active[config.WATCHLIST_MAX:]]
        active = active[:config.WATCHLIST_MAX]

    return active, graduated + over


def snapshot(client, watchlist):
    """조회수를 받아 한 줄씩 만든다. 응답에 없는 id 는 unavailable."""
    ids = [v["video_id"] for v in watchlist]
    if not ids:
        return [], []

    details = client.videos(ids)

    # 채널 구독자는 영상 응답에 없다. 채널을 따로 부른다 (50개당 1 unit).
    ch_ids = {item.get("snippet", {}).get("channelId")
              for item in details.values()}
    ch_ids.discard(None)
    channels = client.channels(ch_ids) if ch_ids else {}

    now = datetime.now(timezone.utc).isoformat()
    rows, missing = [], []

    for vid in ids:
        item = details.get(vid)
        if item is None:
            # 삭제·비공개. videos.list 는 에러가 아니라 조용히 빼고 준다.
            missing.append(vid)
            rows.append({"collected_at": now, "video_id": vid, "views": "",
                         "likes": "", "comments": "", "channel_subscribers": "",
                         "channel_video_count": "", "hidden_subscriber_count": "",
                         "watch_status": "unavailable"})
            continue

        stats = item.get("statistics", {})
        ch = channels.get(item.get("snippet", {}).get("channelId"), {})
        ch_stats = ch.get("statistics", {})
        hidden = str(ch_stats.get("hiddenSubscriberCount", "")).lower() == "true"

        rows.append({
            "collected_at": now,
            "video_id": vid,
            "views": stats.get("viewCount", ""),
            "likes": stats.get("likeCount", ""),
            "comments": stats.get("commentCount", ""),
            # 구독자를 숨긴 채널은 값을 비운다. 0 으로 채우면 Ratio 가 무한이 된다.
            "channel_subscribers": "" if hidden else ch_stats.get("subscriberCount", ""),
            # channels.list 를 이미 statistics 로 부르고 있어 videoCount 는
            # 응답에 함께 온다. 저장해도 할당량이 더 들지 않는다.
            "channel_video_count": ch_stats.get("videoCount", ""),
            "hidden_subscriber_count": "true" if hidden else "false",
            "watch_status": "active",
        })
    return rows, missing


def report_gain(history, new_rows):
    """직전 관측과 견줘 하루치 증가를 보여준다.

    «전날» 이 아니라 «직전 관측» 이다. 하루를 빠뜨렸을 때 2일치를 1일치로
    읽으면 값이 2배가 된다. 실제 경과 일수로 나눈다.
    """
    out = []
    for row in new_rows:
        if row["watch_status"] != "active":
            continue
        prev_rows = history.get(row["video_id"], [])
        if not prev_rows:
            continue
        prev = prev_rows[-1]
        try:
            t0 = datetime.fromisoformat(prev["collected_at"])
            t1 = datetime.fromisoformat(row["collected_at"])
            days = (t1 - t0).total_seconds() / 86400
        except Exception:
            continue
        # 간격이 너무 짧으면 재지 않는다. 같은 날 두 번 돌리면 0.007일 같은
        # 값으로 나누게 되어 몇 건의 잡음이 하루치로 수만 건이 된다.
        if days < (config.MIN_GAIN_HOURS / 24):
            continue
        delta = _num(row["views"]) - _num(prev.get("views"))
        out.append((row["video_id"], delta / days, days))
    out.sort(key=lambda x: -x[1])
    return out


def main():
    _utf8()
    videos = storage.read_videos()
    if not videos:
        print("videos.csv 가 비어 있습니다. 먼저 수집하세요:")
        print("  python -m src.collector")
        return 1

    history = storage.snapshot_history()
    watchlist, dropped = build_watchlist(videos, history)

    print(f"videos.csv {len(videos)}건 → 추적 {len(watchlist)}건 "
          f"(졸업·제외 {len(dropped)}건)")
    if not watchlist:
        print("추적할 영상이 없습니다.")
        return 0

    try:
        client = Client()
    except RuntimeError as e:
        print(f"\n{e}")
        return 1

    try:
        rows, missing = snapshot(client, watchlist)
    except QuotaError as e:
        print(f"\n{e}")
        client.log_quota("quota exceeded")
        return 1

    gains = report_gain(history, rows)
    storage.append_snapshots(rows)
    client.log_quota("snapshot")

    print(f"  기록 {len(rows)}건 · {client.report()}")
    if missing:
        print(f"  삭제·비공개 {len(missing)}건 → unavailable 로 기록")

    if gains:
        print(f"\n  하루치 증가 상위 (직전 관측 대비)")
        titles = {v["video_id"]: v.get("title", "") for v in videos}
        for vid, per_day, days in gains[:5]:
            print(f"    {per_day:>10,.0f}/일  ({days:.1f}일 간격)  "
                  f"{titles.get(vid, '')[:34]}")
    else:
        print("\n  첫 수집입니다. 증가량은 다음 실행부터 나옵니다.")
        print("  내일 다시 한 번 돌리면 진짜 시계열이 시작됩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
