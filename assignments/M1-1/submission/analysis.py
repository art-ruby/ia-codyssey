# -*- coding: utf-8 -*-
"""과제용 분석 — 그래프 3개와 인사이트 수치를 낸다.

    python analysis.py

여기서 나온 숫자를 REPORT.md 에 옮긴다. 숫자를 손으로 지어내지 않는다.
"""
import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import analysis as A, config, seeds

IMAGES = Path(__file__).resolve().parent / "images"
IMAGES.mkdir(exist_ok=True)

# 한글과 일본어를 같이 쓴다. 맑은고딕에는 일본 한자(孤独의 独)가 없어
# 검색어 라벨이 두부로 나온다. MS Gothic 을 뒤에 붙여 메운다.
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgun.ttf",
    r"C:\Windows\Fonts\msgothic.ttc",
    r"C:\Windows\Fonts\NanumGothic.ttf",
]


# 그래프 라벨은 한글로만 쓴다.
#
# 윈도우에 한글과 일본 한자를 동시에 가진 폰트가 없다(실측).
#   Malgun · Gulim · Batang   한글 O · 独 X
#   MS Gothic · Yu Gothic     한글 X · 独 O
# 폰트를 섞어 보았으나 「孤独」이 「孤」로 잘리거나, 강제 지정하면 라벨이
# 축 밖으로 밀려나거나 아예 사라졌다. 폰트 스택과 씨름할 문제가 아니다.
#
# 검색어는 config.SEED_LABELS 로 한글화해 그린다. 일본어 원문은 CSV 와
# 웹화면에 그대로 남는다 — 웹은 브라우저가 그리므로 깨지지 않는다.
def use_fonts():
    picked = []
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                font_manager.fontManager.addfont(path)
                picked.append(font_manager.FontProperties(fname=path).get_name())
            except Exception:
                pass
    if picked:
        plt.rcParams["font.family"] = picked
        plt.rcParams["axes.unicode_minus"] = False
        return " + ".join(picked)
    return None


def label(seed):
    """그래프용 한글 이름. 없으면 원문 그대로."""
    return seeds.labels().get(seed, config.SEED_LABELS.get(seed, seed))


def fig01_trend(df):
    """게시 주차별 평균 조회 속도 + 4주 이동평균."""
    w = (df.set_index("published_at").resample("W")["adviews"]
           .agg(["mean", "count"]))
    w = w[w["count"] > 0]
    w["ma4"] = w["mean"].rolling(4, min_periods=1).mean()

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 7.5), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1]})
    ax.plot(w.index, w["mean"], "o-", lw=1.4, ms=4, alpha=.55,
            label="주간 평균 조회 속도")
    ax.plot(w.index, w["ma4"], lw=2.6, color="#c0392b", label="4주 이동평균")
    ax.set_ylabel("평균 조회수 / 일")
    ax.set_title("게시 주차별 평균 조회 속도 (Average Daily Views)")
    ax.legend()
    ax.grid(alpha=.25)
    # 오른쪽이 높은 것은 «관심 증가» 가 아닐 수 있다. 보는 사람이 반드시
    # 알아야 하므로 그림 안에 적는다.
    ax.text(.01, .97,
            "주의: ADViews 는 조회수÷경과일이라 어린 영상일수록 높다.\n"
            "오른쪽 상승을 «관심 증가» 로 읽지 말 것.",
            transform=ax.transAxes, va="top", fontsize=9, color="#c0392b",
            bbox=dict(fc="#fdf2f0", ec="#c0392b", alpha=.9, pad=5))

    ax2.bar(w.index, w["count"], width=5, color="#7f8c8d", alpha=.7)
    ax2.set_ylabel("영상 수")
    ax2.set_xlabel("게시 주차")
    ax2.grid(alpha=.25)

    fig.tight_layout()
    fig.savefig(IMAGES / "01_view_velocity_trend.png", dpi=130)
    plt.close(fig)
    return w


def fig02_scatter(df):
    """구독자 대비 조회수 — 왼쪽 위가 Outlier."""
    d = df.dropna(subset=["channel_subscribers", "views"])
    d = d[(d["channel_subscribers"] > 0) & (d["views"] > 0)]

    fig, ax = plt.subplots(figsize=(10, 7))
    sc = ax.scatter(d["channel_subscribers"], d["views"],
                    c=d["video_score"], cmap="viridis",
                    s=28, alpha=.75, edgecolors="none")
    xs = [d["channel_subscribers"].min(), d["channel_subscribers"].max()]
    for mult, style in ((1, ":"), (10, "--"), (100, "-")):
        ax.plot(xs, [x * mult for x in xs], style, color="#e74c3c",
                lw=1, alpha=.6, label=f"구독자 x {mult}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("채널 구독자 수 (로그)")
    ax.set_ylabel("영상 조회수 (로그)")
    ax.set_title("구독자 대비 조회수 — 왼쪽 위일수록 Outlier")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=.25, which="both")
    fig.colorbar(sc, ax=ax, label="Video Score")
    fig.tight_layout()
    fig.savefig(IMAGES / "02_subscriber_vs_views.png", dpi=130)
    plt.close(fig)
    return d


def fig03_topic(df):
    """검색어별 성과와 공급량.

    «최근 30일 vs 이전 30일 평균 ADViews» 는 쓰지 않는다.
    ADViews 는 조회수÷경과일인데 유튜브 조회수는 초기에 몰린다. 그래서
    최근 영상일수록 ADViews 가 구조적으로 높다. 두 기간을 그대로 비교하면
    «어린 영상 vs 늙은 영상» 을 비교하는 셈이라 성장이 아니라 지표의 편향이
    나온다. 실제로 그렇게 재보니 16,000% 같은 값이 나왔다.

    대신 편향이 없는 둘을 본다.
      · 같은 나이대(8~30일) 안에서의 중앙 ADViews  — 나이를 통제한 성과
      · 기간별 게시 영상 수                        — 나이와 무관한 공급량
    """
    now = pd.Timestamp.now(tz="UTC")
    window = df[(df["age_days"] >= 8) & (df["age_days"] <= 30)]

    rows = []
    for seed in sorted(df["seed"].dropna().unique()):
        s = window[window["seed"] == seed]["adviews"]
        recent = ((df["seed"] == seed)
                  & (df["published_at"] > now - pd.Timedelta(days=30))).sum()
        prev = ((df["seed"] == seed)
                & (df["published_at"] <= now - pd.Timedelta(days=30))
                & (df["published_at"] > now - pd.Timedelta(days=60))).sum()
        rows.append({"seed": seed,
                     "median_adviews": s.median() if len(s) >= 3 else None,
                     "n_window": len(s),
                     "supply_recent": int(recent), "supply_prev": int(prev)})
    g = pd.DataFrame(rows)
    if g.empty:
        return g

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, max(4.5, len(g) * .6)))

    ok = g.dropna(subset=["median_adviews"]).sort_values("median_adviews")
    if not ok.empty:
        ax1.barh([label(s) for s in ok["seed"]], ok["median_adviews"],
                 color="#2980b9", alpha=.85)
        for i, (v, n) in enumerate(zip(ok["median_adviews"], ok["n_window"])):
            ax1.text(v, i, f"  {v:,.0f} (n={n})", va="center", fontsize=9)
    ax1.set_xlabel("중앙 조회수 / 일")
    ax1.set_title("검색어별 성과\n(게시 후 8~30일 영상만 — 나이를 맞춰 비교)",
                  fontsize=11)
    ax1.grid(axis="x", alpha=.25)

    idx = list(range(len(g)))
    h = .38
    ax2.barh([i + h / 2 for i in idx], g["supply_recent"], height=h,
             label="최근 30일", color="#c0392b", alpha=.85)
    ax2.barh([i - h / 2 for i in idx], g["supply_prev"], height=h,
             label="이전 30일", color="#95a5a6", alpha=.85)
    ax2.set_yticks(idx)
    ax2.set_yticklabels([label(s) for s in g["seed"]])
    ax2.set_xlabel("영상 수")
    ax2.set_title("검색어별 공급량\n(게시 수 — 나이 편향이 없다)", fontsize=11)
    ax2.legend(fontsize=9)
    ax2.grid(axis="x", alpha=.25)

    fig.tight_layout()
    fig.savefig(IMAGES / "03_topic_performance.png", dpi=130)
    plt.close(fig)
    return g


def main():
    print(f"폰트: {use_fonts() or '못 찾음 — 라벨이 깨질 수 있다'}")

    df = A.build()
    scored = df[df["views"].notna()].copy()
    print(f"분석 대상 {len(scored)}건\n")

    w = fig01_trend(scored)
    d = fig02_scatter(scored)
    g = fig03_topic(scored)
    print("그래프 3개 저장 → images/\n")

    print("=" * 64)
    print("REPORT.md 에 옮길 숫자")
    print("=" * 64)

    lo, hi = scored["published_at"].min(), scored["published_at"].max()
    print("\n[데이터]")
    print(f"  영상 {len(scored)}건 · 채널 {scored['channel_id'].nunique()}개")
    print(f"  게시 기간 {lo:%Y-%m-%d} ~ {hi:%Y-%m-%d}")
    print(f"  길이 중앙 {scored['duration_seconds'].median() / 60:.0f}분")
    # 비율을 못 재는 이유가 둘이다. 뭉뜽그리면 «비공개» 가 부풀어 보인다.
    hidden = (scored.get("hidden_subscriber_count", "")
              .astype(str).str.lower() == "true").sum()
    small = int(((scored["channel_subscribers"] < config.MIN_SUBSCRIBERS_FOR_RATIO)
                 & scored["channel_subscribers"].notna()).sum())
    print(f"  구독대비 못 잼 {int(scored['subscriber_view_ratio'].isna().sum())}건 "
          f"— 비공개 {int(hidden)}건 · 구독 "
          f"{config.MIN_SUBSCRIBERS_FOR_RATIO:,}명 미만 {small}건")

    print("\n[인사이트 1] 게시 주차별 조회 속도 — 해석에 주의")
    last4 = w["mean"].tail(4).mean()
    prev4 = w["mean"].tail(8).head(4).mean()
    print(f"  최근 4주 평균 {last4:,.0f}/일 · 그 전 4주 {prev4:,.0f}/일")
    print(f"  겉보기 변화 {(last4 - prev4) / prev4 * 100:+.1f}%")
    print("  주의: 이것을 «관심이 늘었다» 로 읽으면 안 된다. ADViews 는 조회수를")
    print("  경과일로 나눈 값이라 어린 영상일수록 구조적으로 높다.")
    print("  나이를 통제하지 않은 기간 비교는 지표의 편향을 본 것이다.")
    win = scored[(scored["age_days"] >= 8) & (scored["age_days"] <= 30)]
    print(f"\n  나이를 맞춰 본 값 (게시 후 8~30일 {len(win)}건)")
    print(f"    중앙 {win['adviews'].median():,.0f}/일 · "
          f"평균 {win['adviews'].mean():,.0f}/일")

    print("\n[인사이트 2] 소형 채널 Outlier")
    small = d[d["channel_subscribers"] <= 10000]
    out = small[small["subscriber_view_ratio"] >= 5]
    print(f"  구독자 1만 이하 {len(small)}건 중 구독자 대비 5배 이상 {len(out)}건")
    for _, r in out.nlargest(3, "subscriber_view_ratio").iterrows():
        print(f"    {r['subscriber_view_ratio']:>6.0f}배  "
              f"구독 {int(r['channel_subscribers']):>7,} → "
              f"{int(r['views']):>9,}회  {r['title'][:26]}")

    print("\n[인사이트 3] 검색어별 성과와 공급량")
    print("  성과는 게시 후 8~30일 영상만으로 잰다 — 나이를 맞추지 않으면")
    print("  최근 영상이 많은 검색어가 무조건 이긴다.")
    if not g.empty:
        print(f"\n    {'검색어':<8}{'중앙 조회속도':>13}{'표본':>6}"
              f"{'최근30일':>9}{'이전30일':>9}")
        for _, r in g.sort_values("median_adviews", ascending=False,
                                  na_position="last").iterrows():
            med = (f"{r['median_adviews']:,.0f}" if pd.notna(r["median_adviews"])
                   else "표본부족")
            print(f"    {r['seed']:<8}{med:>13}{int(r['n_window']):>6}"
                  f"{int(r['supply_recent']):>9}{int(r['supply_prev']):>9}")

    ch = config.DATA_PROCESSED / "channels.csv"
    if ch.exists():
        c = pd.read_csv(ch)
        both = (c["score_basis"] == "baseline+momentum").sum()
        cs = pd.to_numeric(c["channel_score"], errors="coerce")
        gap = c[(c["video_score"] >= 85) & (cs <= 30)]
        print("\n[인사이트 4] 영상만 터진 채널")
        print(f"  검증 채널 {len(c)}개 · Momentum 계산됨 {both}개")
        print(f"  Video Score 85 이상인데 Channel Score 30 이하 = {len(gap)}건")
        for _, r in gap.iterrows():
            print(f"    Video {r['video_score']:>5.1f} / Channel "
                  f"{r['channel_score']:>5} · 기준 {r['channel_baseline']:>5}  "
                  f"{str(r['channel_name'])[:20]}")

    snaps = A.gains()
    days = 0 if snaps.empty else snaps["collected_at"].dt.date.nunique()
    print("\n[한계]")
    print(f"  스냅샷 누적 {days}일 — 지금의 시계열은 개별 영상의 변화가 아니라")
    print("  게시 코호트 비교다. 매일 쌓으면 실제 일별 증가분으로 다시 잰다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
