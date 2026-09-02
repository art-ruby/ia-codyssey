# -*- coding: utf-8 -*-
"""Phase B — 채널 검증.

Phase A 는 «이 영상이 특이하게 강한가» 를 묻는 선별 단계다.
여기서는 «그 채널도 실제로 상승하고 있는가» 를 따로 묻는다.

    python -m src.channel_analyzer

두 점수를 합치지 않는다. 합치면 «영상은 터졌지만 채널은 아직» 이라는
가장 중요한 정보가 사라진다. (v5 §8)

흐름 — TOP 30 의 채널만 본다. 전부 보면 비싸고, 볼 이유도 없다.
    channels.list → uploads playlist → playlistItems.list → videos.list

누적 조회수가 아니라 ADViews 로 비교한다. 과거 영상은 시간이 쌓여
누적이 유리해지므로, 그대로 비교하면 Momentum 이 늘 1보다 작게 나온다.
"""
import csv
import sys
from datetime import datetime, timezone
from statistics import median

if __package__ in (None, ""):
    sys.exit("python -m src.channel_analyzer 로 실행하세요")

from . import analysis, config
from .youtube import Client, QuotaError, parse_duration

OUT = config.DATA_PROCESSED / "channels.csv"
RECENT_N = 5       # 최근 몇 개를 «지금» 으로 볼 것인가
PAST_N = 10        # 그 앞 몇 개를 «과거» 로 볼 것인가
FETCH_N = 50       # playlistItems 는 50개까지 같은 1 unit 이다. 안 늘릴 이유가 없다.
                   # 20개로 두었더니 Shorts 를 빼고 나면 롱폼이 8개도 안 되는
                   # 채널이 30개 중 10개였다 — 그만큼 Momentum 이 비었다.


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _age_days(published_at):
    """게시 후 경과일. 읽을 수 없으면 None."""
    try:
        t = datetime.fromisoformat((published_at or "").replace("Z", "+00:00"))
        return max((datetime.now(timezone.utc) - t).total_seconds() / 86400, 0.5)
    except Exception:
        return None


def channel_history(client, channel_ids):
    """채널별 최근 영상들의 ADViews 목록 (최신순)."""
    chans = client.channels(channel_ids)

    uploads = {}
    for cid, item in chans.items():
        pl = (item.get("contentDetails", {})
                  .get("relatedPlaylists", {}).get("uploads"))
        if pl:
            uploads[cid] = pl

    vid_of = {}
    for cid, pl in uploads.items():
        try:
            vid_of[cid] = client.playlist_items(pl, max_results=FETCH_N)
        except RuntimeError:
            vid_of[cid] = []          # 재생목록이 비공개인 채널이 있다

    all_ids = [v for ids in vid_of.values() for v in ids]
    details = client.videos(all_ids) if all_ids else {}

    hist = {}
    for cid, ids in vid_of.items():
        rows = []
        for vid in ids:                       # playlistItems 는 최신순이다
            item = details.get(vid)
            if not item:
                continue
            # Shorts 가 섞이면 분포가 왜곡된다. 롱폼만 본다.
            secs = parse_duration(item.get("contentDetails", {}).get("duration"))
            if secs < config.LONGFORM_MIN_SECONDS:
                continue
            pub = item.get("snippet", {}).get("publishedAt")
            try:
                views = int(item.get("statistics", {}).get("viewCount", 0))
            except (TypeError, ValueError):
                continue
            age = _age_days(pub)
            if age is None:
                continue
            rows.append({"video_id": vid, "views": views, "age_days": age})
        hist[cid] = rows
    return hist, chans


def score(hist, chans, top_videos):
    """Channel Baseline · Momentum · Channel Score."""
    rows = []
    for v in top_videos:
        cid = v["channel_id"]
        h = hist.get(cid, [])

        # ── 나이를 통제한다 ──────────────────────────────────────
        # ADViews(조회수÷경과일)로 비교하면 안 된다. 조회수는 초기에 몰리는데
        # 경과일만 계속 늘어나므로, 오래된 영상의 ADViews 는 0 에 수렴한다.
        # 실제로 어떤 채널은 중앙 4.1/일이 나와 기준이 2,941배로 부풀었다.
        #
        # 대신 «대상보다 오래된 영상» 의 조회수와 견준다. 비교 대상이 시간을
        # 더 가졌는데도 대상이 이겼다면 그것은 진짜다. 편향이 신호를 찾는
        # 쪽이 아니라 반대쪽으로 작용하므로, 나온 값은 과소평가다.
        age = v.get("age_days")
        older = [x["views"] for x in h
                 if x["video_id"] != v["video_id"]
                 and (age is None or x["age_days"] > age)]

        baseline = None
        if len(older) >= 3:
            m = median(older)
            if m > 0 and v.get("views"):
                baseline = v["views"] / m

        # Momentum 도 같은 이유로 조회수로 본다. 최근 5개는 과거 10개보다
        # 시간이 적은데도 더 봤다면 채널이 실제로 오르고 있다는 뜻이다.
        momentum = None
        recent = [x["views"] for x in h[:RECENT_N]]
        past = [x["views"] for x in h[RECENT_N:RECENT_N + PAST_N]]
        if len(recent) >= 3 and len(past) >= 3:
            mp = median(past)
            if mp > 0:
                momentum = median(recent) / mp

        st = chans.get(cid, {}).get("statistics", {})
        rows.append({
            "channel_id": cid,
            "channel_name": v.get("channel_name", ""),
            "video_id": v["video_id"],
            "title": v.get("title", "")[:60],
            "video_score": v.get("video_score"),
            "subscribers": st.get("subscriberCount", ""),
            "longform_found": len(h),
            "channel_baseline": round(baseline, 2) if baseline else "",
            "channel_momentum": round(momentum, 2) if momentum else "",
        })

    # 백분위는 계산된 것들 안에서만 낸다. 빈 값을 0 으로 채우면 순위가 뒤틀린다.
    for key, out in (("channel_baseline", "baseline_pct"),
                     ("channel_momentum", "momentum_pct")):
        vals = sorted(r[key] for r in rows if r[key] != "")
        for r in rows:
            if r[key] == "" or not vals:
                r[out] = ""
                continue
            rank = sum(1 for v in vals if v <= r[key])
            r[out] = round(rank / len(vals) * 100, 1)

    for r in rows:
        b, m = r["baseline_pct"], r["momentum_pct"]
        if b != "" and m != "":
            r["channel_score"] = round(b * config.W_CHANNEL_BASELINE
                                       + m * config.W_CHANNEL_MOMENTUM, 1)
            r["score_basis"] = "baseline+momentum"
        elif b != "":
            # Momentum 을 못 낸 채널은 Baseline 만으로 낸다. 다만 둘 다로 낸
            # 점수와 같은 자로 잰 것이 아니므로 근거를 남겨 구분할 수 있게 한다.
            r["channel_score"] = b
            r["score_basis"] = "baseline_only"
        else:
            r["channel_score"] = ""
            r["score_basis"] = "none"
    return rows


def main():
    _utf8()
    df = analysis.build()
    if df.empty:
        print("데이터가 없습니다. python -m src.collector 를 먼저 실행하세요.")
        return 1

    top = df.dropna(subset=["video_score"]).nlargest(
        config.PRIORITY_A_TOP, "video_score")
    cids = list(dict.fromkeys(top["channel_id"].tolist()))
    print(f"Phase A TOP {len(top)} → 채널 {len(cids)}개 검증")
    print(f"  예상 비용 약 {1 + len(cids) + (len(cids) * FETCH_N // 50 + 1)} units "
          "(search 없음)")

    try:
        client = Client()
    except RuntimeError as e:
        print(f"\n{e}")
        return 1

    try:
        hist, chans = channel_history(client, cids)
    except QuotaError as e:
        print(f"\n{e}")
        client.log_quota("quota exceeded")
        return 1

    rows = score(hist, chans, top.to_dict("records"))
    client.log_quota("channel_analyzer")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["channel_id", "channel_name", "video_id", "title", "video_score",
              "subscribers", "longform_found", "channel_baseline",
              "channel_momentum", "baseline_pct", "momentum_pct", "channel_score",
              "score_basis"]
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"  {client.report()}")
    print(f"  저장 → {OUT}")

    scored = [r for r in rows if r["channel_score"] != ""]
    print(f"\n  Channel Score 계산됨 {len(scored)}건 / {len(rows)}건")
    print("\n  Video Score 는 높은데 Channel Score 가 낮은 것 "
          "= 영상만 터지고 채널은 아직")
    print(f"\n  {'채널':<18}{'Video':>7}{'Chan':>7}{'기준':>7}{'모멘텀':>8}  제목")
    for r in sorted(rows, key=lambda x: -(x["video_score"] or 0))[:12]:
        cs = f"{r['channel_score']:.0f}" if r["channel_score"] != "" else "  -"
        bl = f"{r['channel_baseline']:.1f}" if r["channel_baseline"] != "" else "  -"
        mo = f"{r['channel_momentum']:.2f}" if r["channel_momentum"] != "" else "   -"
        print(f"  {r['channel_name'][:17]:<18}{r['video_score']:>7.1f}{cs:>7}"
              f"{bl:>7}{mo:>8}  {r['title'][:26]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
