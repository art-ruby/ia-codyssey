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


# 스냅샷에서 끌어오는 열. videos.csv 에는 없고 video_snapshots.csv 에만 있다
# (storage.VIDEO_FIELDS / SNAPSHOT_FIELDS 참고). 스냅샷이 없을 때도 이 열들이
# «결측으로라도» 있어야 아래 계산이 KeyError 없이 돈다.
FROM_SNAPSHOT = ["views", "likes", "comments", "channel_subscribers",
                 "channel_video_count", "hidden_subscriber_count",
                 "collected_at"]


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
            snaps[["video_id"] + [c for c in FROM_SNAPSHOT if c in snaps]],
            on="video_id", how="left")

    # 스냅샷이 아직 하나도 없으면 위 merge 를 통째로 건너뛰어 조회수 열 자체가
    # 없다. 그대로 내보내면 add_metrics() 가 KeyError 로 죽고, app.py 는 이
    # 예외를 감싸지 않으므로 «수집된 데이터가 없습니다» 안내조차 못 띄운 채
    # 화면 전체가 낙는다. 수집만 하고 snapshot_collector 를 아직 안 돌린
    # 첫날이 정확히 이 상태다.
    #
    # 없는 열은 결측으로 만들어 둔다. 0 으로 채우면 «조회수 0» 이라는
    # 거짓말이 되어, 못 잰 것이 «바닥» 으로 둔갑한다.
    for col in FROM_SNAPSHOT:
        if col not in videos:
            videos[col] = pd.NA

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
    #
    # df.get(col, "") 로 쓰면 안 된다 — 열이 없을 때 돌아오는 것은 빈 Series
    # 가 아니라 «문자열 하나» 라, 이어지는 .astype() 에서 AttributeError 로
    # 죽는다. 열이 없는 상황을 막으려고 넣은 방어가 오히려 터뜨리는 셈이다.
    if "hidden_subscriber_count" in df:
        hidden = df["hidden_subscriber_count"].astype(str).str.lower() == "true"
    else:
        hidden = pd.Series(False, index=df.index)
    subs = df["channel_subscribers"].where(~hidden)
    # 분모가 너무 작아도 계산하지 않는다. 구독 6명에 1,461회는 244배가 되지만
    # «유난히 잘 됐다» 가 아니라 «구독자가 거의 없다» 는 뜻이다. (config 주석)
    ratio = (df["views"] / subs).where(subs >= config.MIN_SUBSCRIBERS_FOR_RATIO)

    # 참여율(좋아요/조회수)이 바닥이면 «잘 됐다» 가 아니라 매크일 수 있다.
    # (yuben-app 벤치마킹, config.MIN_ENGAGEMENT_PER_1K 근거 참고)
    #
    # 행을 지우지 않는다 — 이 프로젝트는 이상치를 «지우지 않고 찾는다»는
    # 원칙이다(REPORT.md §4). 대신 subscriber_view_ratio 만 비워서, 매크
    # 의심 영상이 구독자 대비 보너스를 못 받게 한다 — Video Score 는
    # svr_percentile 이 없으면 나이 보정 백분위만으로 계산되므로(add_scores),
    # 그 영상이 사라지지도 뻥튀기되지도 않는다.
    #
    # likes 가 없으면(비공개 등) 매크로 몰지 않는다 — «모른다» 를 «나쁘다»
    # 로 바꾸면 안 된다.
    df["engagement_per_1k"] = (df["likes"] / df["views"] * 1000)
    low_engagement = df["engagement_per_1k"] < config.MIN_ENGAGEMENT_PER_1K
    df["low_engagement"] = low_engagement.where(df["likes"].notna(), False)
    df["subscriber_view_ratio"] = ratio.where(~df["low_engagement"])

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


def add_opportunity(df):
    """어디서 소재를 발굴할 것인가 — 구독자 규모 군(sub_tier)과 배수 등급.

    **점수를 만들지 않는다.** Video Score 는 건드리지 않고, 이미 계산된
    subscriber_view_ratio 를 등급으로 이름 붙이기만 한다. 그래서 이 함수를
    빼도 기존 화면과 리포트는 그대로 동작한다.

    subscriber_view_ratio 를 다시 계산하지 않고 그대로 쓰는 것이 중요하다 —
    그 열은 이미 구독자 하한(1,000)·구독자 비공개·매크 방어를 통과한 값이다.
    여기서 views/subs 를 다시 나누면 그 방어를 전부 우회하게 된다.
    (구독 6명 채널이 244배로 «강력» 1위가 되는 일이 실제로 생긴다)
    """
    if df.empty:
        return df
    df = df.copy()

    # ── 구독자 군 ──
    # 구독자를 못 잰 것(비공개·스냅샷 전)은 A·B·C 어디에도 넣지 않는다.
    # 전체의 21.5%(167건)라 조용히 사라지게 두면 안 된다. D 로 남겨
    # 나이 보정 백분위로만 보게 한다.
    subs = df["channel_subscribers"]
    if "hidden_subscriber_count" in df:
        hidden = df["hidden_subscriber_count"].astype(str).str.lower() == "true"
        subs = subs.where(~hidden)

    tier = pd.Series("D", index=df.index, dtype=object)
    tier[subs.notna() & (subs > 0)] = "C"
    tier[subs <= config.SECONDARY_ZONE_MAX_SUBSCRIBERS] = "B"
    tier[subs <= config.OPPORTUNITY_ZONE_MAX_SUBSCRIBERS] = "A"
    df["sub_tier"] = tier

    # ── 배수 등급 ──
    # 조회수 하한은 «분자가 작은 것» 을 막는다. 구독 1,200명에 4,000회는
    # 3.3배지만 수요의 증거가 아니다.
    ratio = df["subscriber_view_ratio"]
    enough = df["views"] >= config.OPPORTUNITY_MIN_VIEWS

    grade = pd.Series("", index=df.index, dtype=object)
    grade[enough & (ratio >= config.OPPORTUNITY_RATIO_WATCH)] = "관찰"
    grade[enough & (ratio >= config.OPPORTUNITY_RATIO_STRONG)] = "주목"
    grade[enough & (ratio >= config.OPPORTUNITY_RATIO_VERY_STRONG)] = "강력"
    df["opportunity_grade"] = grade

    # 초소형 배지 — 등급과 직교한다. «3배짜리 초소형» 도 «10배짜리 초소형» 도
    # 있다. 등급 안에 섞으면 둘 중 하나를 못 보게 된다.
    df["is_micro"] = (subs.notna()
                      & (subs >= config.MIN_SUBSCRIBERS_FOR_RATIO)
                      & (subs <= config.SMALL_CHANNEL_MAX_SUBSCRIBERS))

    # 배수를 «못 잰» 이유를 남긴다. 값이 비어 있는 것만으로는 구독자가
    # 적어서인지, 비공개라서인지, 매크 의심이라서인지 알 수 없다.
    why = pd.Series("", index=df.index, dtype=object)
    why[subs.isna()] = "구독자 미상"
    why[subs.notna() & (subs < config.MIN_SUBSCRIBERS_FOR_RATIO)] = "구독자 1천 미만"
    why[df["low_engagement"].fillna(False)] = "매크 의심"
    df["ratio_missing_why"] = why.where(ratio.isna(), "")
    return df


def build():
    """수집 → 지표 → 백분위 → 점수 → 발굴군. 화면과 리포트가 이 함수를 쓴다."""
    df = load()
    if df.empty:
        return df
    return add_opportunity(add_scores(add_age_adjusted(add_metrics(df))))


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

    # **실제로 잰 증가량**을 같이 남긴다.
    #
    # daily_view_gain 은 «하루로 환산한 값» 이지 «하루 동안 잰 값» 이 아니다.
    # 8.4시간을 재서 2.85배 하면 화면에는 「하루 +180,282」로 뜨는데,
    # 실제로 본 것은 8.4시간에 +63,168 이다. 이름만 보고는 그 차이를 알 수 없다.
    #
    # 순위는 왜곡되지 않는다 — 지금은 모든 영상의 간격이 같아 배율도 같다.
    # 왜곡되는 것은 **절대값과 «하루» 라는 이름**이다. 그래서 원값을 함께 준다.
    snaps["view_gain"] = (snaps["views"] - snaps["prev_views"]).where(~too_soon)
    snaps["elapsed_hours"] = (days * 24).where(~too_soon)
    snaps["daily_view_gain"] = ((snaps["views"] - snaps["prev_views"]) / days
                                ).where(~too_soon)
    # 하루를 다 못 채운 관측은 «추세» 가 아니라 «초기 신호» 다.
    snaps["is_early"] = snaps["elapsed_hours"] < config.FULL_DAY_HOURS
    return snaps.dropna(subset=["daily_view_gain"])
