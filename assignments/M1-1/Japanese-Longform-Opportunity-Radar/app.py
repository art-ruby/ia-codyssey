# -*- coding: utf-8 -*-
"""Japanese Long-form Opportunity Radar — 화면.

    streamlit run app.py

이 화면은 **이미 수집된 CSV 만 읽는다.** 필터를 만질 때마다 API 를 부르면
하루 상한(검색 약 100회)이 몇 번 만에 날아간다. 새 수집은 명령으로만 한다.

    python -m src.collector            수집
    python -m src.snapshot_collector   매일 1회
"""
import subprocess
import sys

import pandas as pd
import streamlit as st

from src import (analysis, channel_fit, channels, comments, config,
                 export, production_brief, seeds,
                 snapshot_collector, storage, translate)

st.set_page_config(page_title="Japanese Long-form Opportunity Radar",
                   page_icon="📡", layout="wide")

# 글꼴만 CSS 로 불러온다. 색·모서리·표는 .streamlit/config.toml 이 맡는다 —
# Streamlit 내부 클래스 이름은 버전마다 바뀌므로 최소한만 손댄다.
#
# 한글과 일본어가 한 줄에 같이 오는 화면이라 둘 다 필요하다.
#   IBM Plex Sans KR  한글·본문      Noto Sans JP  일본어 원문
#   IBM Plex Mono     숫자 (자릿수를 맞춘다)
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+JP:wght@400;500&display=swap">
<style>
  /* 숫자는 자릿수를 맞춘다 — 표를 세로로 훑을 때 자릿수가 흔들리면 못 읽는다 */
  [data-testid="stMetricValue"], [data-testid="stDataFrame"] {
    font-variant-numeric: tabular-nums;
  }
  /* 제목이 어중간하게 잘리지 않게 */
  h1, h2, h3 { text-wrap: balance; letter-spacing: -0.01em; }
  /* 탭 이름을 조금 좁혀 11개가 한 줄에 들어가게 */
  [data-testid="stTabs"] button p { font-size: 0.92rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load():
    return analysis.build(), analysis.gains()


df, gain_df = load()

st.title("📡 Japanese Long-form Opportunity Radar")

if df.empty:
    st.error("수집된 데이터가 없습니다.")
    st.code("python -m src.collector", language="bash")
    st.stop()

# ── 요약 ─────────────────────────────────────────────────────────
scored = df[df["views"].notna()]
c1, c2, c3, c4 = st.columns(4)
c1.metric("수집 영상", f"{len(df):,}")
c2.metric("조회수 있음", f"{len(scored):,}")
c3.metric("중앙 길이", f"{int(df['duration_seconds'].median() // 60)}분")
snap_days = gain_df["collected_at"].dt.date.nunique() if not gain_df.empty else 0
c4.metric("스냅샷 누적", f"{snap_days + 1}일" if snap_days else "1일 (첫날)")

if gain_df.empty:
    st.info(
        "**아직 증가량을 계산할 수 없습니다.** 스냅샷이 한 번뿐이라 "
        "«지금 오르는 중인 영상» 을 가릴 수 없습니다.\n\n"
        "내일 `python -m src.snapshot_collector` 를 한 번 더 돌리면 "
        "진짜 시계열이 시작됩니다. 하루 약 10 units 밖에 안 듭니다."
    )

# ── 필터 ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("필터")
    st.caption("여기를 만져도 API 를 부르지 않습니다. 이미 받아 둔 데이터만 거릅니다.")

    # 이름을 seeds 로 두면 src.seeds 모듈을 가린다. 아래 «검색어 관리» 가
    # seeds.current() 를 부르는 순간 AttributeError 로 죽는다.
    seed_opts = sorted(df["seed"].dropna().unique())
    buckets = [b for b in
               [x[0] for x in config.AGE_BUCKETS] + ["90+"]
               if b in set(df["age_bucket"])]

    # 검색어가 20개라 펼쳐 두면 사이드바가 칩으로 가득 찬다. 접어 두고
    # 몇 개가 걸려 있는지만 이름에 적는다 — 평소에는 전부 켜 놓고 쓴다.
    with st.expander(f"검색어 {len(seed_opts)}개", expanded=False):
        pick_seed = st.multiselect(
            "검색어 (Seed)", seed_opts, default=seed_opts,
            label_visibility="collapsed")
    with st.expander(f"게시 후 경과 {len(buckets)}구간", expanded=False):
        pick_bucket = st.multiselect(
            "게시 후 경과 (Age Bucket)", buckets, default=buckets,
            label_visibility="collapsed")

    max_subs = int(scored["channel_subscribers"].max() or 0)
    sub_cap = st.select_slider(
        "채널 구독자 상한",
        options=[1_000, 10_000, 50_000, 100_000, 500_000, max(max_subs, 500_001)],
        value=max(max_subs, 500_001),
        format_func=lambda v: "전체" if v > 500_000 else f"{v:,}명 이하")

    min_min = st.slider("최소 길이(분)", 10, 60,
                        config.LONGFORM_MIN_SECONDS // 60)

    st.divider()
    st.caption("새 데이터가 필요하면 터미널에서")
    st.code("python -m src.snapshot_collector", language="bash")

view = scored[
    scored["seed"].isin(pick_seed)
    & scored["age_bucket"].isin(pick_bucket)
    & (scored["duration_seconds"] >= min_min * 60)
    & (scored["channel_subscribers"].fillna(0) <= sub_cap)
].copy()

if view.empty:
    st.warning("조건에 맞는 영상이 없습니다. 필터를 넓혀 보세요.")
    st.stop()

st.caption(f"조건에 맞는 영상 **{len(view):,}건** / 전체 {len(scored):,}건")

(tab0, tab1, tab2, tab3, tab4, tab5,
 tab6, tab7, tab8, tab9, tab10) = st.tabs(
    ["☀️ 오늘의 발견", "🔥 떡상영상", "📈 시계열", "🎯 Outlier 분포", "📊 데이터",
     "🔎 검색어 관리", "🏆 채널 검증", "📋 Watchlist", "📶 수집·할당량",
     "⏰ 자동 실행", "🌐 번역 설정"])


def title_of(row):
    """한글 제목. 없으면 원문."""
    ko = str(row.get("title_ko") or "").strip()
    return ko or str(row.get("title") or "")


def watch_url(ids):
    """유튜브 주소. 숫자만 보고는 «이게 진짜인가» 를 확인할 수 없다.
    표에서 바로 열 수 있어야 소재를 고르는 일이 끝난다. (prd §5.1 [열기])"""
    return "https://www.youtube.com/watch?v=" + ids.astype(str)


LINK = st.column_config.LinkColumn("▶", display_text="열기", width="small")


@st.cache_data(ttl=60)
def channel_seeds():
    """채널 id → 그 채널에 달린 검색어 집합.

    비활성 검색어도 넣는다 — 검색어를 뺐다고 그 검색어로 이미 모아 둔
    영상까지 화면에서 사라지면 안 된다.
    """
    return {c["id"]: set(seeds.terms_for_channel(c["id"], active_only=False))
            for c in channels.records()}


def channel_picker(key):
    """[전체] [채널A] [채널B]. 고른 채널 id 를 준다(전체면 None).

    Radar 는 하나다. 채널은 «같은 시장 데이터를 어느 관점으로 볼 것인가» 일
    뿐이라 수집·점수는 공통이고 여기서 걸러 보기만 한다.
    """
    live = [c for c in channels.records() if c.get("discovery_enabled")]
    if not live:
        return None, []
    label = {"전체": None}
    for c in live:
        label[f"{c.get('emoji', '')} {c['name_ko']}".strip()] = c["id"]
    picked = st.radio("채널", list(label), horizontal=True,
                      label_visibility="collapsed", key=key)
    return label[picked], live


def only_channel(frame, channel_id, cmap):
    """그 채널의 검색어로 모은 영상만."""
    if channel_id is None or "seed" not in frame:
        return frame
    return frame[frame["seed"].isin(cmap.get(channel_id, set()))]


# ── ☀️ 오늘의 발견 — 아침 5분에 보는 화면 ────────────────────────
with tab0:
    ch_id, ch_live = channel_picker("ch_today")
    cmap = channel_seeds()
    focus = only_channel(scored, ch_id, cmap)
    now_ch = next((c for c in ch_live if c["id"] == ch_id), None)

    if now_ch:
        st.caption(
            f"**{now_ch['promise_ko']}**　"
            f"이 채널이 늘 묻는 것 — {now_ch['core_question_ko']}"
        )
        if not now_ch.get("production_enabled"):
            st.caption("🔬 아직 실제 업로드 전 — 후보와 데이터를 쌓는 중입니다.")

    if ch_id and focus.empty:
        st.warning(
            f"**이 채널 검색어로 모은 영상이 아직 없습니다.** "
            f"검색어 {len(seeds.terms_for_channel(ch_id))}개를 새로 넣었지만 "
            "아직 한 번도 수집을 돌리지 않았습니다. "
            "화면은 API 를 부르지 않으니 터미널에서 한 번 돌려야 채워집니다."
        )
        st.code("python -m src.collector", language="bash")

    st.subheader("🔥 지금 오르는 중")
    st.caption(
        "직전 관측 대비 하루치 증가. **스냅샷 두 장을 비교한 값이라 "
        "착각할 여지가 없습니다.** 지금 실제로 오르고 있다는 증거입니다."
    )

    if gain_df.empty:
        st.info(
            "**아직 잴 수 없습니다.** 관측이 6시간 넘게 벌어져야 하루치 증가를 "
            "계산합니다.\n\n"
            "같은 날 두 번 돌리면 0.03일 같은 값으로 나누게 되어 몇 건의 잡음이 "
            "하루 수만 건으로 부풀어 오릅니다. 그래서 일부러 막아 두었습니다.\n\n"
            "매일 아침 7시 자동 수집이 걸려 있으니 하루만 지나면 여기가 채워집니다."
        )
    else:
        latest = (gain_df.sort_values("collected_at")
                        .groupby("video_id").tail(1))
        rise = latest.merge(
            df[["video_id", "title", "title_ko", "channel_name",
                "channel_subscribers", "channel_video_count", "views",
                "video_score", "age_days", "seed"]],
            on="video_id", how="left", suffixes=("", "_v"))
        rise = only_channel(rise, ch_id, cmap).nlargest(10, "daily_view_gain")

    # 빈 표에 .apply() 를 걸면 float 열이 나와 .str 이 터진다. 채널을 고르면
    # 실제로 비는 일이 흔하다 — 방금 모은 영상은 스냅샷이 한 번뿐이라
    # 아직 증가량이 없다. 크래시가 아니라 «왜 비었는지» 를 알려 준다.
    if not gain_df.empty and rise.empty:
        st.info(
            "**이 채널에는 아직 증가량을 잰 영상이 없습니다.** 증가량은 같은 "
            "영상을 6시간 넘게 벌어진 두 시점에 봐야 나옵니다. 방금 모은 "
            "영상은 아직 한 번밖에 못 봤습니다.\n\n"
            "내일 아침 자동 수집이 한 번 더 돌면 여기가 채워집니다."
        )
    elif not gain_df.empty:
        st.dataframe(pd.DataFrame({
            "열기": watch_url(rise["video_id"]),
            "하루 증가": rise["daily_view_gain"].round(0),
            "간격(시간)": (rise["elapsed_days"] * 24).round(1),
            "제목": rise.apply(title_of, axis=1).str.slice(0, 38),
            "채널": rise["channel_name"].str.slice(0, 14),
            "구독자": rise["channel_subscribers"],
            "영상수": rise["channel_video_count"],
            "누적 조회": rise["views_v"] if "views_v" in rise else rise["views"],
            "점수": rise["video_score"].round(1),
        }), use_container_width=True, hide_index=True,
            column_config={
                "하루 증가": st.column_config.NumberColumn(format="localized"),
                "구독자": st.column_config.NumberColumn(format="localized"),
                "영상수": st.column_config.NumberColumn(format="localized"),
                "누적 조회": st.column_config.NumberColumn(format="localized"),
                "열기": LINK,
            })

    st.divider()

    st.subheader("🆕 어제 새로 들어온 것")
    st.caption(
        "⚠️ **«어제 처음 봤다» 이지 «어제 떴다» 가 아닙니다.** 검색으로 이제야 "
        "걸렸을 뿐 한 달 전에 이미 터진 영상일 수 있습니다. 그래서 게시일을 "
        "같이 봅니다."
    )

    fresh = focus.copy()
    if "found_at" in fresh:
        found = pd.to_datetime(fresh["found_at"], format="mixed",
                               utc=True, errors="coerce")
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=30)
        fresh = fresh[found >= cutoff]

    if fresh.empty:
        st.info("최근 30시간 안에 새로 들어온 영상이 없습니다. "
                "다음 수집(내일 아침 7시) 뒤에 채워집니다.")
    else:
        new_top = fresh.nlargest(10, "video_score")
        st.dataframe(pd.DataFrame({
            "열기": watch_url(new_top["video_id"]),
            "점수": new_top["video_score"].round(1),
            "제목": new_top.apply(title_of, axis=1).str.slice(0, 38),
            "채널": new_top["channel_name"].str.slice(0, 14),
            "구독자": new_top["channel_subscribers"],
            "영상수": new_top["channel_video_count"],
            "조회수": new_top["views"],
            "구독대비": new_top["subscriber_view_ratio"].round(1),
            "게시 후": new_top["age_days"].round(0).astype(int),
            "나이대": new_top["age_bucket"],
        }), use_container_width=True, hide_index=True,
            column_config={
                "열기": LINK,
                "점수": st.column_config.ProgressColumn(
                    "점수", min_value=0, max_value=100, format="%.1f"),
                "구독자": st.column_config.NumberColumn(format="localized"),
                "영상수": st.column_config.NumberColumn(
                    "영상수", format="localized",
                    help="이 채널이 유튜브에 올려 둔 전체 영상 수. 구독자와 함께 "
                         "보면 «영상이 쌓여 큰 채널»과 «몇 편으로 뜬 채널»이 갈린다."),
                "조회수": st.column_config.NumberColumn(format="localized"),
                "게시 후": st.column_config.NumberColumn("게시 후", format="%d일"),
            })
        old = new_top[new_top["age_days"] > 30]
        if not old.empty:
            st.caption(f"↑ 이 중 {len(old)}건은 게시된 지 30일이 넘었습니다 — "
                       "지금 뜨는 것이 아니라 이제야 발견된 것입니다.")

    st.divider()

    # ── Claude 웹으로 넘기기 (prd F-3) ───────────────────────────
    st.subheader("📋 Claude 웹으로 넘기기")
    st.caption(
        "영상을 고르고 [한 장 만들기] 를 누르면 붙여넣을 글이 나옵니다. "
        "**글 상자 오른쪽 위 복사 아이콘**을 누르면 그대로 복사됩니다."
    )

    pool = focus.nlargest(40, "video_score")
    if not gain_df.empty:
        movers = set(gain_df.nlargest(10, "daily_view_gain")["video_id"])
        pool = pd.concat([focus[focus["video_id"].isin(movers)], pool])
        pool = pool.drop_duplicates("video_id")

    labels = {
        r["video_id"]: f"{r['video_score']:>5.1f}  {title_of(r)[:44]}"
        for _, r in pool.iterrows()
    }
    if not labels:
        st.info("고를 영상이 없습니다. 위에서 채널을 «전체» 로 바꾸거나 "
                "수집을 한 번 돌리세요.")
        st.stop()

    picked = st.selectbox("영상", list(labels), format_func=lambda k: labels[k],
                          label_visibility="collapsed")

    col_a, col_b = st.columns([1, 3])
    with col_a:
        go = st.button("한 장 만들기", type="primary", use_container_width=True)
    with col_b:
        subs = st.checkbox("자막 발췌 넣기 (몇 초 걸립니다)", value=True)

    if go:
        # 자막은 유튜브에서 받아 온다. 누를 때만 부른다 — 고를 때마다
        # 받으면 요청이 몰려 429 로 막힌다.
        with st.spinner("자막을 받아 한 장으로 묶는 중…"):
            st.session_state["one_pager"] = export.one_pager(
                picked, with_subtitles=subs)

    if st.session_state.get("one_pager"):
        st.code(st.session_state["one_pager"], language=None)

    st.divider()

    # ── 제작 후보 확정 → Production Brief → 대본 자료 (지시서 §53) ──
    st.subheader("🎬 제작 후보로 확정하기")
    st.caption(
        "위 한 장은 «이 소재를 고를지» 판단용입니다. 여기서부터는 "
        "**고른 소재를 어떤 영상으로 만들지** 설계합니다. "
        "댓글을 받고 채널 관점으로 해석하므로 **누를 때만** API 를 부릅니다."
    )

    live = [c for c in channels.records() if c.get("discovery_enabled")]
    if not live:
        st.info("등록된 채널이 없습니다. `data/config/channels.json` 을 확인하세요.")
    else:
        names = {f"{c.get('emoji', '')} {c['name_ko']}".strip(): c["id"]
                 for c in live}
        pick_name = st.radio(
            "이 소재를 어느 채널에서 제작합니까?", list(names),
            horizontal=True, key="brief_channel")
        brief_ch = names[pick_name]
        prof = channels.get(brief_ch) or {}
        if not prof.get("production_enabled"):
            st.caption("🔬 연구모드 — 브리프와 대본은 만들 수 있지만 "
                       "실제 업로드 채널은 아직 시작 전입니다.")

        b1, b2 = st.columns(2)
        make = b1.button("댓글 받고 브리프 만들기", type="primary",
                         use_container_width=True)
        pack = b2.button("Claude 대본용 자료 만들기", use_container_width=True)

        if make:
            with st.spinner("댓글 수집 → 분석 → Channel Fit 판정 → 브리프 조립…"):
                row = scored[scored["video_id"] == picked]
                r0 = comments.fetch(picked)
                if r0.get("status") == "ok" and not row.empty:
                    comments.analyze(picked, row.iloc[0])
                res = production_brief.build(picked, brief_ch)
            st.session_state["brief"] = res
            st.session_state["brief_for"] = (picked, brief_ch)
            if r0.get("status") != "ok":
                st.warning(f"댓글: {r0.get('why', '')} — 나머지는 그대로 만들었습니다.")

        if pack:
            with st.spinner("대본 작성용 자료를 묶는 중…"):
                st.session_state["pack"] = production_brief.script_package(
                    picked, brief_ch)
            st.session_state["brief_for"] = (picked, brief_ch)

        res = st.session_state.get("brief")
        if res and st.session_state.get("brief_for", (None, None))[1] == brief_ch:
            if not res.get("ok"):
                st.error(res.get("why", "브리프를 만들지 못했습니다"))
            else:
                fit = res.get("fit") or {}
                if fit.get("ok"):
                    cols = st.columns(len(channel_fit.ASPECTS))
                    for col, (k, label) in zip(cols, channel_fit.ASPECTS):
                        col.metric(label, fit.get(k, "—"))
                st.caption(f"저장됨 — `{res['path']}` ({res['chars']:,}자)")
                with st.expander("브리프 보기", expanded=True):
                    st.markdown(res["text"])

        pk = st.session_state.get("pack")
        if pk and st.session_state.get("brief_for", (None, None))[1] == brief_ch:
            if not pk.get("ok"):
                st.error(pk.get("why", "자료를 만들지 못했습니다"))
            else:
                st.caption(
                    f"{pk['chars']:,}자 — 이대로 Claude 웹에 붙여넣으면 "
                    "제목 후보·썸네일 문구·일본어 대본·FACT CHECK 가 나옵니다.")
                st.code(pk["text"], language=None)


# ── 떡상영상 ─────────────────────────────────────────────────────
with tab1:
    st.subheader("Video Score 상위")
    st.caption(
        "Video Score = 같은 나이대 안에서의 조회 속도 백분위 × 0.6 "
        "+ 구독자 대비 조회수 백분위 × 0.4 — 채널 성장 여부는 별도 지표입니다."
    )
    top = view.nlargest(30, "video_score")
    # 한글 제목을 먼저 보여주고 원문을 옆에 둔다. 번역이 틀릴 수 있고,
    # 복사해 Claude 웹으로 넘길 때는 원문이 필요하다.
    ko = top.get("title_ko", pd.Series("", index=top.index)).fillna("")
    show = pd.DataFrame({
        "점수": top["video_score"],
        "제목": ko.where(ko.str.strip() != "", top["title"]).str.slice(0, 40),
        "원문": top["title"].str.slice(0, 30),
        "채널": top["channel_name"].str.slice(0, 16),
        "구독자": top["channel_subscribers"],
        "영상수": top["channel_video_count"],
        "조회수": top["views"],
        "구독대비": top["subscriber_view_ratio"].round(1),
        "경과": top["age_days"].round(0).astype(int),
        "나이대": top["age_bucket"],
        "표본": top["age_bucket_n"],
        "길이(분)": (top["duration_seconds"] // 60).astype(int),
    })
    show.insert(0, "열기", watch_url(top["video_id"]))
    st.dataframe(show, use_container_width=True, hide_index=True,
                 column_config={
                     "열기": LINK,
                     "점수": st.column_config.ProgressColumn(
                         "점수", min_value=0, max_value=100, format="%.1f"),
                     "구독자": st.column_config.NumberColumn(format="localized"),
                     "조회수": st.column_config.NumberColumn(format="localized"),
                     "구독대비": st.column_config.NumberColumn(
                         "구독대비", help="조회수 ÷ 구독자. 구독자 비공개면 빈칸"),
                     "표본": st.column_config.NumberColumn(
                         "표본", help="같은 나이대 영상 수. 적으면 점수를 덜 믿는다"),
                 })

    small = top[top["percentile_method"] == "median_ratio"]
    if not small.empty:
        st.warning(f"{len(small)}건은 같은 나이대 표본이 20건 미만이라 "
                   "백분위 대신 전체 중앙값 대비로 계산했습니다.")

# ── 시계열 ───────────────────────────────────────────────────────
with tab2:
    st.subheader("게시 주차별 평균 조회 속도")
    st.caption(
        "**주의** — 이것은 개별 영상의 시간 변화가 아니라 «그 주에 게시된 "
        "영상들» 의 평균입니다. 진짜 시계열은 스냅샷이 쌓여야 나옵니다."
    )
    weekly = (view.set_index("published_at")
                  .resample("W")["adviews"].agg(["mean", "count"])
                  .rename(columns={"mean": "평균 조회속도", "count": "영상 수"}))
    weekly["4주 이동평균"] = weekly["평균 조회속도"].rolling(4, min_periods=1).mean()
    st.line_chart(weekly[["평균 조회속도", "4주 이동평균"]])
    st.bar_chart(weekly["영상 수"])

    if not gain_df.empty:
        st.subheader("지금 오르는 중인 영상")
        st.caption("직전 관측 대비 하루치 증가. 하루를 걸러도 실제 경과일로 나눕니다.")
        latest = gain_df.sort_values("collected_at").groupby("video_id").tail(1)
        merged = latest.merge(df[["video_id", "title", "channel_name"]],
                              on="video_id", how="left")
        rise = merged.nlargest(15, "daily_view_gain")
        st.dataframe(pd.DataFrame({
            "열기": watch_url(rise["video_id"]),
            "하루 증가": rise["daily_view_gain"].round(0),
            "간격(일)": rise["elapsed_days"].round(1),
            "제목": rise["title"].str.slice(0, 44),
            "채널": rise["channel_name"].str.slice(0, 16),
        }), use_container_width=True, hide_index=True,
            column_config={"열기": LINK})

# ── Outlier 분포 ─────────────────────────────────────────────────
with tab3:
    st.subheader("구독자 대비 조회수")
    st.caption("왼쪽 위 = 구독자가 적은데 조회수가 높은 영상. 우리가 찾는 것.")
    plot = view.dropna(subset=["channel_subscribers"]).copy()
    plot = plot[plot["channel_subscribers"] > 0]
    if plot.empty:
        st.info("구독자가 공개된 영상이 없습니다.")
    else:
        st.scatter_chart(plot, x="channel_subscribers", y="views",
                         color="age_bucket", size="video_score")
        st.caption(f"구독자 비공개라 제외된 영상 "
                   f"{len(view) - len(plot)}건")

    st.subheader("나이대별 표본 수")
    st.caption("표본이 20건 미만인 나이대는 백분위가 불안정해 다르게 계산합니다.")
    bc = (view.groupby("age_bucket")
              .agg(영상수=("video_id", "size"),
                   평균조회속도=("adviews", "mean")).round(0))
    st.dataframe(bc, use_container_width=True)

# ── 데이터 ───────────────────────────────────────────────────────
with tab4:
    st.subheader("전체 데이터")
    cols = ["video_id", "title_ko", "title", "channel_name", "channel_subscribers",
            "views", "adviews", "subscriber_view_ratio", "age_days",
            "age_bucket", "age_bucket_n", "age_adjusted_percentile",
            "percentile_method", "video_score", "seed", "duration_seconds"]
    full = view[[c for c in cols if c in view]].copy()
    full.insert(0, "열기", watch_url(view["video_id"]))
    st.dataframe(full, use_container_width=True, hide_index=True,
                 column_config={"열기": LINK})
    st.download_button("CSV 내려받기",
                       view.to_csv(index=False).encode("utf-8-sig"),
                       "opportunity_radar.csv", "text/csv")


# ── 🔎 검색어 관리 (③ · prd F-4) ─────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _meanings(terms):
    """후보의 한글 뜻. 사용자가 일본어를 모르므로 이것 없이는 못 고른다.

    `translate_titles` 가 아니라 `translate_terms` 다. 전자는 제목을 지어낸다.
    """
    ok, _ = translate.available()
    if not ok or not terms:
        return {}
    return {t: ko for t, ko in zip(terms, translate.translate_terms(list(terms)))}


with tab5:
    st.caption(
        "검색어를 8개로 고정해 두면 **일주일쯤 뒤 같은 영상만 나옵니다.** "
        "여기서 늘리고 줄입니다. 바꾼 것은 **다음 수집부터** 쓰입니다."
    )

    now = seeds.current()
    st.subheader(f"현재 검색어 ({len(now)}/{seeds.MAX_SEEDS})")
    per = len(config.SEARCH_ORDERS) * config.SEARCH_COST      # 검색어 1개 값
    cost = len(now) * per
    pct = cost / config.DAILY_QUOTA * 100
    st.caption(
        f"검색어 1개 = 검색 {len(config.SEARCH_ORDERS)}회 = 약 {per} units. "
        f"{len(now)}개면 하루 **{cost:,} units ({pct:.0f}%)** 듭니다."
    )
    # 목표는 «하루 할당량 20% 이내»(prd §12) 인데 상한 15개면 30% 가 된다.
    # 두 요건이 서로 어긋나므로, 선을 넘을 때 눈에 보이게 알린다.
    if pct > 20:
        st.warning(
            f"목표는 **하루 20% 이내**인데 지금 {pct:.0f}% 입니다. "
            f"검색어 {int(config.DAILY_QUOTA * 0.2 // per)}개까지가 그 선입니다. "
            "더 늘리려면 성과가 낮은 것을 빼거나, 20% 기준을 다시 정해야 합니다."
        )

    badge = {c["id"]: f"{c.get('emoji', '')} {c['name_ko']}".strip()
             for c in channels.records()}

    perf = seeds.performance(scored)
    for row in perf:
        if not row.get("active"):
            continue                     # 뺀 검색어는 아래 접힌 칸에서 본다
        c1, c2, c3, c4 = st.columns([3, 2, 4, 1])
        rec = seeds.get(row["term"]) or {}
        tags = " · ".join(badge[i] for i in rec.get("channels", []) if i in badge)
        c1.markdown(f"**{row['label']}**　`{row['term']}`"
                    + (f"<br><span style='font-size:0.8em;opacity:0.7'>{tags}</span>"
                       if tags else ""), unsafe_allow_html=True)
        c2.markdown(f"영상 {row['n']}건")
        if row["median_score"] is not None:
            c3.markdown(f"중앙 점수 **{row['median_score']:.1f}** "
                        f"· 구독대비 5배 넘은 것 {row['outliers']}건")
        else:
            c3.markdown("아직 수집된 영상이 없습니다")
        if c4.button("빼기", key=f"rm_{row['term']}", use_container_width=True):
            ok, msg = seeds.remove(row["term"])
            (st.success if ok else st.warning)(msg)
            st.rerun()

    gone = [r for r in perf if not r.get("active") and r["n"]]
    if gone:
        with st.expander(f"지금은 안 쓰는 검색어 {len(gone)}개 — 과거 실적은 남아 있습니다"):
            for row in gone:
                med = f"{row['median_score']:.1f}" if row["median_score"] else "—"
                st.markdown(f"`{row['term']}` **{row['label']}** · "
                            f"영상 {row['n']}건 · 중앙 {med} · 이상치 {row['outliers']}건")

    st.caption(
        "**이상치 수로 줄 세웠습니다.** 찾는 것은 «구독자에 비해 유난히 잘 된 "
        "영상»이지 «평균이 높은 주제»가 아닙니다. 중앙 점수가 낮아도 이상치가 "
        "많으면 편차가 큰 주제라 오히려 사냥터로 좋습니다."
    )
    weak = seeds.weakest(perf)
    if weak:
        st.warning(
            f"**{weak['label']}**(`{weak['term']}`)은 영상 {weak['n']}건을 모으는 "
            f"동안 구독대비 {seeds.OUTLIER_RATIO:.0f}배 넘은 영상이 하나도 "
            "없었습니다. 뺄 후보입니다."
        )

    st.divider()

    # ── 데이터에서 뽑은 후보 ─────────────────────────────────────
    st.subheader("새 검색어 후보")
    st.caption(
        f"구독자 대비 {seeds.OUTLIER_RATIO:.0f}배 넘게 본 영상 제목에서 "
        f"{seeds.MIN_APPEARANCES}번 이상 나온 말입니다.\n\n"
        "⚠️ **주제가 아니라 «형식»이거나 채널명인 경우가 많습니다.** "
        "「ゆっくり解説」은 주제가 아니라 영상 형식이라 그대로 넣으면 "
        "그 형식의 영상만 걸립니다. 보고 직접 고르세요."
    )

    cands = seeds.candidates(scored)
    if not cands:
        st.info("아직 후보가 없습니다. 데이터가 더 쌓이면 나옵니다.")
    else:
        mean = _meanings(tuple(c["term"] for c in cands))
        for c in cands:
            c1, c2, c3, c4 = st.columns([3, 4, 1, 1])
            ko = mean.get(c["term"], "")
            c1.markdown(f"`{c['term']}`　**{ko}**" if ko else f"`{c['term']}`")
            c2.caption(f"{c['count']}편에 등장 · 예) {c['titles'][0][:38]}")
            if c3.button("추가", key=f"add_{c['term']}", use_container_width=True):
                ok, msg = seeds.add(c["term"], ko)
                (st.success if ok else st.warning)(msg)
                if ok:
                    st.rerun()
            if c4.button("무시", key=f"ig_{c['term']}", use_container_width=True):
                seeds.ignore(c["term"])
                st.rerun()

    st.divider()

    # ── 한글로 찾기 ─────────────────────────────────────────────
    st.subheader("한글로 찾기")
    st.caption(
        "⚠️ **단순 번역은 검색어로 못 씁니다.** 「노후」를 그대로 옮기면 "
        "「老後」지만 일본에서 많이 쓰는 말은 「定年後」「シニア」일 수 있습니다. "
        "번역이 아니라 **그쪽에서 실제로 쓰는 말**을 물어봅니다."
    )
    col1, col2 = st.columns([3, 1])
    topic = col1.text_input("주제", placeholder="예) 노후 자금, 부업, 미니멀리즘",
                            label_visibility="collapsed")
    if col2.button("찾기", use_container_width=True) and topic.strip():
        ok, why = translate.available()
        if not ok:
            st.error(f"찾을 수 없습니다 — {why}")
        else:
            with st.spinner("일본에서 쓰는 말을 물어보는 중…"):
                st.session_state["found_terms"] = translate.suggest_search_terms(
                    topic.strip())

    for i, d in enumerate(st.session_state.get("found_terms") or []):
        c1, c2, c3 = st.columns([3, 4, 1])
        c1.markdown(f"`{d['term']}`")
        c2.caption(d.get("meaning") or "")
        if c3.button("추가", key=f"sg_{i}_{d['term']}", use_container_width=True):
            ok, msg = seeds.add(d["term"], d.get("meaning", ""))
            (st.success if ok else st.warning)(msg)
            if ok:
                st.rerun()

    # ── 무시 목록 ───────────────────────────────────────────────
    skip = sorted(seeds.ignored())
    if skip:
        with st.expander(f"무시한 후보 {len(skip)}개 — 다시 제안하지 않습니다"):
            for w in skip:
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"`{w}`")
                if c2.button("되살리기", key=f"un_{w}", use_container_width=True):
                    seeds.unignore(w)
                    st.rerun()


# ── 🏆 채널 검증 (Phase B) ───────────────────────────────────────
@st.cache_data(ttl=60)
def load_channels():
    path = config.DATA_PROCESSED / "channels.csv"
    if not path.exists():
        return pd.DataFrame()
    c = pd.read_csv(path)
    for col in ("subscribers", "longform_found", "video_score", "channel_score",
                "channel_baseline", "channel_momentum"):
        if col in c:
            c[col] = pd.to_numeric(c[col], errors="coerce")
    return c


with tab6:
    st.subheader("채널 검증 (Phase B)")
    st.caption(
        "Phase A(Video Score)는 «이 영상이 특이하게 강한가» 를 묻습니다. "
        "여기서는 «그 채널도 실제로 상승하고 있는가» 를 따로 봅니다. "
        "**기준(평소 대비)** = 이 영상 ÷ 이 영상보다 **오래된** 영상들의 중앙 조회수 — "
        "비교 대상이 시간을 더 가졌으므로 나온 값은 과소평가입니다. "
        "Video Score 와 Channel Score 는 합치지 않습니다."
    )
    chans = load_channels()
    if chans.empty:
        st.info("아직 채널 검증 결과가 없습니다. 명령으로 먼저 돌려야 합니다(화면은 API 를 부르지 않습니다).")
        st.code("python -m src.channel_analyzer", language="bash")
    else:
        def _verdict(row):
            if pd.isna(row.get("channel_score")):
                return "판정 못 함"
            if row["channel_score"] >= 70:
                return "채널째 오름"
            if pd.notna(row.get("channel_baseline")) and row["channel_baseline"] < 1:
                return "영상만 눈에 띔"
            return "보통"

        # NaN 을 NumberColumn 의 커스텀 format 문자열(예: "%.2f배")에 그대로
        # 맡기면 빈칸이 아니라 "None" 글자가 찍힌다(이 Streamlit 버전의 특성).
        # export.py 의 _fmt() 와 같은 방식으로 여기서 먼저 문자열로 바꾼다 —
        # «점수가 낮다» 와 «모른다» 를 구분해야 하므로 0 으로도 채우지 않는다.
        def _f1(v):
            return "—" if pd.isna(v) else f"{v:.1f}"

        def _fx(v):
            return "—" if pd.isna(v) else f"{v:.2f}배"

        show = pd.DataFrame({
            "채널": chans["channel_name"].astype(str).str.slice(0, 18),
            "구독자": chans["subscribers"],
            "롱폼": chans["longform_found"],
            "Video": chans["video_score"].map(_f1),
            "Channel": chans["channel_score"].map(_f1),
            "평소 대비": chans["channel_baseline"].map(_fx),
            "최근 흐름": chans["channel_momentum"].map(_fx),
            "판정": chans.apply(_verdict, axis=1),
        })
        show.insert(0, "열기", watch_url(chans["video_id"]))
        st.dataframe(show, use_container_width=True, hide_index=True,
                     column_config={
                         "열기": LINK,
                         "구독자": st.column_config.NumberColumn(format="localized"),
                     })
        unresolved = int(chans["channel_score"].isna().sum())
        if unresolved:
            st.caption(f"↑ {unresolved}개 채널은 비교할 과거 롱폼이 모자라 판정하지 못했습니다 "
                       "(«점수가 낮다» 가 아니라 «모른다» 입니다).")


# ── 📋 Watchlist ─────────────────────────────────────────────────
with tab7:
    st.subheader("Watchlist")
    st.caption(
        "추적 대상과 졸업 규칙입니다. 졸업해도 지우지 않고, "
        "삭제·비공개 영상도 기록으로 남깁니다."
    )
    videos_all = storage.read_videos()
    if not videos_all:
        st.info("아직 수집된 영상이 없습니다.")
    else:
        history_all = storage.snapshot_history()
        active_list, dropped = snapshot_collector.build_watchlist(videos_all, history_all)
        graduated_n = sum(1 for _, reason in dropped if reason != "상한 초과")
        over_n = sum(1 for _, reason in dropped if reason == "상한 초과")
        active_n = len(active_list)

        last_snap = storage.last_snapshot_by_video()
        unavailable_n = sum(1 for v in last_snap.values()
                            if v.get("watch_status") == "unavailable")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("active", f"{active_n:,}", "추적 중")
        c2.metric("graduated", f"{graduated_n:,}", "60일 초과 또는 증가 없음")
        c3.metric("unavailable", f"{unavailable_n:,}", "삭제·비공개(최근 관측 기준)")
        c4.metric("상한", f"{config.WATCHLIST_MAX:,}",
                  f"여유 {max(config.WATCHLIST_MAX - active_n, 0):,}")
        if over_n:
            st.caption(f"↑ 상한 초과로 이번에 {over_n}건이 함께 빠질 예정입니다.")

        st.divider()
        st.markdown(f"""
| 항목 | 규칙 |
|---|---|
| 등록 | Video Score 상위 {config.WATCHLIST_REGISTER_TOP}개 |
| 상한 | {config.WATCHLIST_MAX}건. 넘으면 최근 발견 순으로 남긴다 |
| 졸업 | 게시 후 {config.GRADUATE_AFTER_DAYS}일 초과 · 또는 스냅샷 {config.MIN_SNAPSHOTS_FOR_GAIN_GRADUATION}회 이상인데 증가 없음 |
| 보존 | 졸업해도 지우지 않는다. 다음 스냅샷부터 추적 대상에서만 빠진다 |
| 삭제·비공개 | 응답에 없는 id 는 `watch_status = unavailable` 로 기록 |
""")
        st.caption(
            "`videos.list` 는 삭제된 영상을 에러가 아니라 조용히 빼고 줍니다. "
            "기록하지 않으면 추적이 왜 끊겼는지 알 수 없습니다."
        )


# ── 📶 수집 · 할당량 ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_quota_log():
    if not config.QUOTA_LOG.exists():
        return pd.DataFrame()
    return pd.read_csv(config.QUOTA_LOG)


with tab8:
    st.subheader("수집 · 할당량")
    st.caption(
        "`search.list` 는 `videos.list` 보다 100배 비쌉니다 — "
        "이 프로젝트의 유일한 하드 제약입니다. **이 화면은 API 를 부르지 않고 "
        "`quota_log.csv` 만 읽습니다.**"
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("search.list", f"{config.SEARCH_COST} units", "검색 1회")
    c2.metric("videos.list 등", f"{config.CHEAP_COST} unit", "50개당 1회")
    c3.metric("하루 상한", f"{config.DAILY_QUOTA:,} units",
              f"검색 {config.SEARCH_CALLS_DAILY_BUDGET}회 상당")

    qlog = load_quota_log()
    if qlog.empty:
        st.info("아직 quota_log.csv 가 없습니다. 명령을 한 번 이상 돌리면 쌓입니다.")
    else:
        qlog["units"] = pd.to_numeric(qlog["units"], errors="coerce").fillna(0)
        today = pd.Timestamp.now().date().isoformat()
        today_units = qlog.loc[qlog["date"] == today, "units"].sum()
        pct = today_units / config.DAILY_QUOTA * 100 if config.DAILY_QUOTA else 0
        st.metric("오늘 쓴 양", f"{today_units:,.0f} units",
                  f"{pct:.0f}% (상한 {config.DAILY_QUOTA:,})")
        if pct >= 80:
            st.warning("오늘 이미 80% 넘게 썼습니다 — 남은 하루 동안 여유가 별로 없습니다.")

        show = qlog.sort_values("date", ascending=False).rename(columns={
            "date": "날짜", "note": "작업", "search_calls": "검색",
            "cheap_calls": "그 외", "units": "units"})
        st.dataframe(show[["날짜", "작업", "검색", "그 외", "units"]],
                     use_container_width=True, hide_index=True,
                     column_config={"units": st.column_config.NumberColumn(
                         format="localized")})


# ── ⏰ 자동 실행 ─────────────────────────────────────────────────
@st.cache_data(ttl=60)
def scheduler_status(prefix="JP Radar"):
    """작업 스케줄러 상태. 시스템 조회일 뿐 네트워크 호출이 아니다.

    실패해도(윈도우가 아니거나, 작업이 없거나) 예외를 올리지 않고 None 을
    돌려준다 — 이 화면은 조용히 실패해도 앱 전체가 죽으면 안 된다.
    """
    try:
        # 날짜는 PowerShell 쪽에서 문자열로 만든다. 그대로 ConvertTo-Json 하면
        # .NET DateTime 이 «/Date(1788303612000)/» 로 직렬화돼 사람이 못 읽는다.
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-ScheduledTask -TaskName '{prefix}*' -ErrorAction SilentlyContinue | "
             "Get-ScheduledTaskInfo | Select-Object TaskName,LastTaskResult,"
             "@{n='LastRunTime';e={if($_.LastRunTime){$_.LastRunTime.ToString('yyyy-MM-dd HH:mm')}else{''}}},"
             "@{n='NextRunTime';e={if($_.NextRunTime){$_.NextRunTime.ToString('yyyy-MM-dd HH:mm')}else{''}}} | "
             "ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=10)
        if p.returncode != 0 or not p.stdout.strip():
            return None
        import json
        data = json.loads(p.stdout)
        return data if isinstance(data, list) else [data]
    except Exception:
        return None


with tab9:
    st.subheader("자동 실행")
    st.caption(
        "«쌓는 주기» 와 «보는 주기» 는 다릅니다. 스냅샷은 매일 쌓여야 시계열이 "
        "생기고, 사람은 그것을 아침에 봅니다."
    )
    tasks = scheduler_status()
    if tasks:
        show = pd.DataFrame(tasks).rename(columns={
            "TaskName": "작업", "LastRunTime": "마지막 실행",
            "LastTaskResult": "결과", "NextRunTime": "다음 실행"})
        order = [c for c in ["작업", "마지막 실행", "결과", "다음 실행"] if c in show]
        st.dataframe(show[order], use_container_width=True, hide_index=True)
        bad = [t for t in tasks if str(t.get("LastTaskResult")) not in ("0",)]
        if bad:
            st.warning(f"{len(bad)}개 작업의 마지막 결과가 0(성공)이 아닙니다 — 로그를 확인하세요.")
        else:
            st.success("등록된 작업의 마지막 결과가 전부 0(성공)입니다.")
    else:
        st.info(
            "'JP Radar' 로 시작하는 작업 스케줄러 항목을 찾지 못했습니다 — "
            "윈도우가 아니거나, 아직 등록 전이거나, 이름이 다를 수 있습니다."
        )

    st.divider()
    st.subheader("run_daily.cmd")
    cmd_path = config.ROOT / "run_daily.cmd"
    if cmd_path.exists():
        st.code(cmd_path.read_text(encoding="utf-8"), language="bat")
    else:
        st.caption("run_daily.cmd 가 없습니다.")

    st.subheader("최근 로그")
    log_path = config.DATA_RAW / "run_log.txt"
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        st.code("\n".join(lines[-20:]) or "(비어 있음)", language=None)
    else:
        st.caption("아직 run_log.txt 가 없습니다.")


# ── 🌐 번역 설정 ─────────────────────────────────────────────────
with tab10:
    st.subheader("번역 설정")
    st.caption(
        "제공자는 몇 달이면 가격·모델·한도가 바뀝니다. 갈아타는 일이 큰 공사가 "
        "되지 않도록 `config.py` 네 줄로 고칠 자리를 못박아 두었습니다."
    )
    ok, why = translate.available()
    status = "🟢 연결됨" if ok else f"🔴 꺼짐 — {why}"
    st.markdown(f"""
| 설정 | 값 |
|---|---|
| 상태 | {status} |
| PROVIDER | `{config.TRANSLATE_PROVIDER}` |
| MODEL | `{config.TRANSLATE_MODEL}` |
| BASE_URL | `{config.TRANSLATE_BASE_URL or "(제공자 기본값)"}` |
| BATCH | {config.TRANSLATE_BATCH}건씩 묶어 보냄 |
""")

    st.divider()
    st.subheader("제목 한글화")
    total = len(df)
    ko_col = df["title_ko"].fillna("") if "title_ko" in df else pd.Series([""] * total)
    done = int(ko_col.str.strip().ne("").sum())
    st.progress(done / total if total else 0, text=f"{done:,} / {total:,}건 완료")

    missing = total - done
    if missing:
        st.caption(f"{missing:,}건이 아직 한글 제목이 없습니다.")
        if ok:
            if st.button(f"빠진 제목 채우기 ({missing:,}건)"):
                with st.spinner("tools/backfill_titles.py 실행 중… (몇 초~몇 분)"):
                    result = subprocess.run(
                        [sys.executable, str(config.ROOT / "tools" / "backfill_titles.py")],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
                st.code(result.stdout or result.stderr or "(출력 없음)", language=None)
                if result.returncode == 0:
                    st.success("완료. 위 [새로고침] 이 안 보이면 브라우저를 새로고침하세요.")
                    st.cache_data.clear()
                else:
                    st.error("실패했습니다 — 위 로그를 확인하세요.")
        else:
            st.caption(f"지금 설정으로는 번역할 수 없습니다 — {why}")
    else:
        st.caption("전부 번역되어 있습니다.")
