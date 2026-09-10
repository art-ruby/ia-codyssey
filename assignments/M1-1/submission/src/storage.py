# -*- coding: utf-8 -*-
"""CSV 읽기·쓰기.

videos.csv 는 변하지 않는 정보, video_snapshots.csv 는 시간에 따라 변하는
정보다. 나누지 않으면 고정 정보를 매일 다시 저장하게 된다.
"""
import csv
from pathlib import Path

from . import config

VIDEO_FIELDS = [
    "video_id", "title", "title_ko", "description", "channel_id", "channel_name",
    "published_at", "duration_seconds", "default_audio_language",
    "detected_language", "kana_ratio", "seed", "found_at",
]

SNAPSHOT_FIELDS = [
    "collected_at", "video_id", "views", "likes", "comments",
    "channel_subscribers", "channel_video_count",
    "hidden_subscriber_count", "watch_status",
]


def _read(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _migrate_header(path, fields):
    """열이 늘었으면 파일을 새 헤더로 다시 쓴다.

    헤더는 그대로 둔 채 새 행만 열을 늘리면 **값이 한 칸씩 밀린다.**
    에러가 나지 않고 조용히 어긋나므로 붙이기 전에 반드시 맞춘다.
    옛 행의 새 열은 빈 값으로 둔다 — 0 으로 채우면 «영상 0개» 라는
    거짓말이 된다.
    """
    p = Path(path)
    if not p.exists():
        return
    with open(p, encoding="utf-8", newline="") as f:
        try:
            head = next(csv.reader(f))
        except StopIteration:
            return
    if head == list(fields):
        return
    rows = _read(p)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def _append(path, fields, rows):
    if not rows:
        return 0
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _migrate_header(path, fields)
    new = not Path(path).exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


def read_videos():
    return _read(config.VIDEOS_CSV)


def known_video_ids():
    return {r["video_id"] for r in read_videos() if r.get("video_id")}


def append_videos(rows):
    """이미 있는 video_id 는 넣지 않는다. 고정 정보라 갱신할 이유가 없다."""
    known = known_video_ids()
    fresh, seen = [], set()
    for r in rows:
        vid = r.get("video_id")
        if not vid or vid in known or vid in seen:
            continue
        seen.add(vid)
        fresh.append(r)
    return _append(config.VIDEOS_CSV, VIDEO_FIELDS, fresh)


def read_snapshots():
    return _read(config.SNAPSHOTS_CSV)


def append_snapshots(rows):
    return _append(config.SNAPSHOTS_CSV, SNAPSHOT_FIELDS, rows)


def snapshot_history():
    """video_id 를 열쇠로 한 스냅샷 목록. 수집 시각 오름차순."""
    hist = {}
    for row in read_snapshots():
        vid = row.get("video_id")
        if vid:
            hist.setdefault(vid, []).append(row)
    for rows in hist.values():
        rows.sort(key=lambda r: r.get("collected_at", ""))
    return hist


def last_snapshot_by_video():
    """video_id 를 열쇠로 한 «직전 관측».

    Gain 은 «전날» 이 아니라 «직전 관측» 기준으로 계산해야 한다.
    하루를 빠뜨렸을 때 2일치가 1일치로 읽히면 값이 2배가 된다.
    """
    return {vid: rows[-1] for vid, rows in snapshot_history().items() if rows}
