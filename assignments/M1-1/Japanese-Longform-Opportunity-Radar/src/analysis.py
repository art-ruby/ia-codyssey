# -*- coding: utf-8 -*-
"""점수 계산 — 화면과 리포트가 같은 계산을 쓰도록 여기 한 곳에 둔다.

따로 두면 화면 숫자와 리포트 숫자가 갈린다.

규칙은 v5 개발확정본을 따른다.
  · Age Bucket 은 «분석 시점의 나이» 로 매번 다시 정한다 (§7)
  · 표본 n<20 이면 인접 버킷과 병합, 그래도 부족하면 전체 중앙값 대비 (§7)
  · Gain 은 «직전 관측» 기준, 실제 경과 일수로 나눈다 (§6)
"""
from datetime import datetime, timezone

import pandas as pd

from . import config, storage


def _to_dt(s):
    return pd.to_datetime(s, format="mixed", utc=True, errors="coerce")


def load():
    """videos.csv + 최신 스냅샷을 합친 표를 만든다."""
    videos = pd.DataFrame(storage.read_videos())
    if videos.empty:
        return videos

    snaps = pd.DataFrame(storage.read_snapshots())
    if not snaps.empty:
        snaps = snaps[snaps["watch_status"] == "active"].copy()
        snaps["collected_at"] = _to_dt(snaps["collected_at"])
        snaps = snaps.sort_values("collected_at").groupby("video_id").tail(1)
        videos = videos.merge(
            snaps[[c for c in
                   ["video_id", "views", "likes", "comments",
                    "channel_subscribers", "channel_video_count",
                    "hidden_subscriber_count", "collected_at"]
                   if c in snaps]],
            on="video_id", how="left")

    for col in ("views", "likes", "comments", "channel_subscribers",
                "channel_video_count", "duration_seconds"):
        if col in videos:
            videos[col] = pd.to_numeric(videos[col], errors="coerce")

    videos["published_at"] = _to_dt(videos["published_at"])
    now = pd.Timestamp.now(tz=timezone.utc)
    # 게시 당일 영상이 0일이 되어 나눗셈이 터지는 것을 막는다.
    videos["age_days"] = ((now - videos["published_at"]).dt.total_seconds()
                          / 86400).clip(lower=0.5)
    return videos


def add_metrics(df):
    """ADViews · Subscriber View Ratio · Age Bucket."""
    if df.empty:
        return df
    df = df.copy()
    df["adviews"] = df["views"] / df["age_days"]

    # 구독자를 숨긴 채널은 Ratio 를 계산하지 않는다. 0 으로 채우면 무한이 된다.
    hidden = df.get("hidden_subscriber_count", "").astype(str).str.lower() == "true"
    subs = df["channel_subscribers"].where(~hidden)
    # 분모가 너무 작아도 계산하지 않는다. 구독 6명에 1,461회는 244배가 되지만
    # «유난히 잘 됐다» 가 아니라 «구독자가 거의 없다» 는 뜻이다. (config 주석)
    df["subscriber_view_ratio"] = (df["views"] / subs).where(
        subs >= config.MIN_SUBSCRIBERS_FOR_RATIO)

    def bucket(days):
        for name, lo, hi in config.AGE_BUCKETS:
            if lo <= days <= hi:
                return name
        return f"{config.AGE_BUCKETS[-1][2]}+"

    df["age_bucket"] = df["age_days"].apply(bucket)
    return df


def _bucket_order():
    return [b[0] for b in config.AGE_BUCKETS] + [f"{config.AGE_BUCKETS[-1][2]}+"]


def add_age_adjusted(df):
    """같은 Age Bucket 안에서 ADViews 백분위를 낸다.

    표본이 적으면 백분위가 무의미해진다 — n=10 이면 한 칸이 10점이다.
    그래서 n<20 이면 인접 버킷과 합치고, 그래도 모자라면 전체 중앙값 대비
    비율로 물러선다. 어느 쪽을 썼는지 method 열에 남긴다.
    """
    if df.empty:
        return df
    df = df.copy()
    order = _bucket_order()
    counts = df["age_bucket"].value_counts().to_dict()

    # 표본이 부족한 버킷을 인접한 것과 묶는다.
    group = {}
    pending = []
    for name in order:
        n = counts.get(name, 0)
        if n == 0:
            continue
        pending.append(name)
        if sum(counts.get(p, 0) for p in pending) >= config.MIN_BUCKET_N:
            label = "+".join(pending)
            for p in pending:
                group[p] = label
            pending = []
    if pending:                       # 마지막에 남은 것들
        label = "+".join(pending)
        for p in pending:
            group[p] = label

    df["age_group"] = df["age_bucket"].map(group).fillna(df["age_bucket"])
    gsize = df.groupby("age_group")["adviews"].transform("size")
    df["age_bucket_n"] = gsize

    # 충분한 그룹은 그룹 내 백분위
    pct = df.groupby("age_group")["adviews"].rank(pct=True) * 100

    # 그래도 부족한 그룹은 전체 중앙값 대비 비율 → 0~100 으로 눌러 담는다.
    # fallback 을 Seed 단위로 하지 않는다 — 모집단이 더 작아 오히려 불안정하다.
    overall_median = df["adviews"].median()
    ratio = (df["adviews"] / overall_median) if overall_median else df["adviews"] * 0
    fallback = (ratio.clip(0, 3) / 3 * 100)

    small = gsize < config.MIN_BUCKET_N
    df["age_adjusted_percentile"] = pct.where(~small, fallback).round(1)
    df["percentile_method"] = pd.Series("bucket", index=df.index).where(
        ~small, "median_ratio")
    return df


def add_scores(df):
    """Video Score. Channel Score 는 Phase B 에서 따로 계산한다.

    두 점수를 하나로 합치지 않는다 — «영상은 터졌지만 채널은 아직» 이라는
    가장 중요한 정보가 사라진다.
    """
    if df.empty:
        return df
    df = df.copy()
    svr_pct = df["subscriber_view_ratio"].rank(pct=True) * 100
    df["svr_percentile"] = svr_pct.round(1)

    # 구독자 비공개라 SVR 이 없으면 그 항목을 빼고 나머지로만 계산한다.
    a = df["age_adjusted_percentile"]
    b = df["svr_percentile"]
    combined = a * config.W_AGE_ADJUSTED + b * config.W_SUBSCRIBER_RATIO
    df["video_score"] = combined.where(b.notna(), a).round(1)
    df["computed_at"] = datetime.now(timezone.utc).isoformat()
    return df


def build():
    """수집 → 지표 → 백분위 → 점수. 화면과 리포트가 이 함수를 쓴다."""
    df = load()
    if df.empty:
        return df
    return add_scores(add_age_adjusted(add_metrics(df)))


def gains():
    """직전 관측 대비 하루치 증가. 스냅샷이 2회 이상 쌓여야 나온다."""
    snaps = pd.DataFrame(storage.read_snapshots())
    if snaps.empty:
        return pd.DataFrame()
    snaps = snaps[snaps["watch_status"] == "active"].copy()
    snaps["collected_at"] = _to_dt(snaps["collected_at"])
    snaps["views"] = pd.to_numeric(snaps["views"], errors="coerce")
    snaps = snaps.sort_values(["video_id", "collected_at"])

    g = snaps.groupby("video_id")
    snaps["prev_views"] = g["views"].shift(1)
    snaps["prev_at"] = g["collected_at"].shift(1)
    # «전날» 이 아니라 «직전 관측» 이다. 하루를 빠뜨려도 값이 부풀지 않는다.
    days = (snaps["collected_at"] - snaps["prev_at"]).dt.total_seconds() / 86400
    snaps["elapsed_days"] = days

    # 간격이 너무 짧으면 계산하지 않는다. 같은 날 두 번 돌리면 0.007일 같은
    # 값으로 나누게 되어 몇 건의 잡음이 하루치로 수만 건이 된다.
    too_soon = days < (config.MIN_GAIN_HOURS / 24)
    snaps["daily_view_gain"] = ((snaps["views"] - snaps["prev_views"]) / days
                                ).where(~too_soon)
    return snaps.dropna(subset=["daily_view_gain"])
