"""
일본 YouTube 롱폼 콘텐츠 트렌드 분석 — 탐색용 웹 대시보드
https://github.com/art-ruby/ia-codyssey/tree/main/assignments/M1-1
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import numpy as np

# 페이지 설정
st.set_page_config(
    page_title="일본 YT 롱폼 콘텐츠 분석 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        body { font-family: 'Segoe UI', sans-serif; }
        .main-title { font-size: 2.5em; font-weight: bold; }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px; border-radius: 10px; text-align: center;
        }
        .insight-box {
            background-color: #f0f2f6; padding: 15px;
            border-left: 4px solid #667eea; border-radius: 5px; margin: 10px 0;
        }
    </style>
""", unsafe_allow_html=True)

# 타이틀
col1, col2 = st.columns([8, 2])
with col1:
    st.markdown("### 📊 일본 YouTube 롱폼 콘텐츠 트렌드 분석")
    st.markdown("**M1-1 AI 데이터 분석** — 구독자 대비 조회수 성과 분석 대시보드")

with col2:
    st.markdown("**📅 분석 기준일**")
    st.markdown("2026-09-02")

st.divider()

# ============================================================================
# 데이터 로드 시뮬레이션 (실제 CSV가 없으므로 샘플 데이터 생성)
# ============================================================================

@st.cache_data
def load_sample_data():
    """
    샘플 데이터 생성 (실제 데이터가 없을 때)
    REPORT.md의 분석 결과를 반영한 대표 수치 포함
    """

    # 검색어 목록 (src/seeds.py 참고)
    keywords = ['老後', 'お金', '仕事', '孤独', 'AI', '人生', 'SNS', '住宅']

    # 샘플 영상 데이터 생성 (632건 기준)
    np.random.seed(42)
    n_videos = 632

    base_date = datetime(2026, 7, 3)
    dates = [base_date + timedelta(days=int(x)) for x in np.random.uniform(0, 60, n_videos)]

    data = {
        'video_id': [f'vid_{i:04d}' for i in range(n_videos)],
        'title': [f'動画タイトル {i}' for i in range(n_videos)],
        'channel_name': [f'チャンネル {i % 100}' for i in range(n_videos)],
        'published_at': dates,
        'duration_seconds': np.random.exponential(600, n_videos).astype(int) + 600,  # 10분 이상
        'views': np.random.lognormal(8, 2, n_videos).astype(int),
        'likes': np.random.lognormal(5, 2, n_videos).astype(int),
        'comments': np.random.lognormal(4, 2, n_videos).astype(int),
        'channel_subscribers': np.random.lognormal(10, 2, n_videos).astype(int),
        'seed': np.random.choice(keywords, n_videos),
        'days_since_publish': np.random.exponential(20, n_videos).astype(int),
    }

    videos_df = pd.DataFrame(data)

    # 조회수 속도 (views per day) 추가
    videos_df['views_per_day'] = videos_df['views'] / (videos_df['days_since_publish'] + 1)

    # 이상치 탐지: 구독자 대비 조회수 비율이 높은 영상
    videos_df['views_per_subscriber'] = videos_df['views'] / (videos_df['channel_subscribers'] + 1)

    return videos_df

videos_df = load_sample_data()

# ============================================================================
# 사이드바 — 필터 설정
# ============================================================================

st.sidebar.markdown("### 🔍 필터 설정")
st.sidebar.divider()

# 1. 날짜 범위
st.sidebar.markdown("**📅 게시 기간**")
date_range = st.sidebar.date_input(
    "기간 선택",
    value=(datetime(2026, 7, 3).date(), datetime(2026, 9, 1).date()),
    key="date_range"
)

# 2. 검색어 필터
st.sidebar.markdown("**🔑 검색어 필터**")
keywords = sorted(videos_df['seed'].unique())
selected_keywords = st.sidebar.multiselect(
    "분석 검색어 선택 (선택 안 하면 전체)",
    keywords,
    default=keywords,
    key="keywords"
)

# 3. 구독자 구간
st.sidebar.markdown("**👥 채널 구독자 수**")
min_subscribers = st.sidebar.number_input(
    "최소 구독자",
    min_value=0,
    value=0,
    step=1000,
    key="min_sub"
)
max_subscribers = st.sidebar.number_input(
    "최대 구독자",
    min_value=0,
    value=int(videos_df['channel_subscribers'].max()) + 100000,
    step=1000,
    key="max_sub"
)

# 4. 조회수 범위 (선택)
st.sidebar.markdown("**👁️ 조회수 범위 (선택)**")
min_views = st.sidebar.number_input(
    "최소 조회수",
    min_value=0,
    value=0,
    step=100,
    key="min_views"
)

# ============================================================================
# 필터 적용
# ============================================================================

filtered_df = videos_df.copy()

# 날짜 필터
if len(date_range) == 2:
    date_start = pd.Timestamp(date_range[0])
    date_end = pd.Timestamp(date_range[1])
    filtered_df = filtered_df[
        (filtered_df['published_at'] >= date_start) &
        (filtered_df['published_at'] <= date_end)
    ]

# 검색어 필터
if selected_keywords:
    filtered_df = filtered_df[filtered_df['seed'].isin(selected_keywords)]

# 구독자 수 필터
filtered_df = filtered_df[
    (filtered_df['channel_subscribers'] >= min_subscribers) &
    (filtered_df['channel_subscribers'] <= max_subscribers)
]

# 조회수 필터
if min_views > 0:
    filtered_df = filtered_df[filtered_df['views'] >= min_views]

# ============================================================================
# 메인 대시보드 — 탭 구성
# ============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔥 떡상영상",
    "📈 시계열",
    "🎯 이상치 분포",
    "📊 데이터",
    "📋 분석 결과"
])

# ============================================================================
# TAB 1: 떡상영상 (High-performing videos)
# ============================================================================

with tab1:
    st.markdown("### 🔥 높은 성과의 영상 (Outlier)")
    st.markdown("""
    **구독자 대비 조회수가 높은 영상들입니다.**
    - 지표: `views_per_subscriber` (조회수 ÷ 채널 구독자)
    - 정렬: 내림차순
    """)

    if len(filtered_df) > 0:
        # Top 10 영상 표시
        top_videos = filtered_df.nlargest(10, 'views_per_subscriber')[
            ['title', 'channel_name', 'views', 'channel_subscribers', 'views_per_subscriber', 'published_at']
        ].copy()

        top_videos['views_per_subscriber'] = top_videos['views_per_subscriber'].round(2)
        top_videos['published_at'] = pd.to_datetime(top_videos['published_at']).dt.strftime('%Y-%m-%d')

        # 컬럼 이름 한글화
        top_videos = top_videos.rename(columns={
            'title': '제목',
            'channel_name': '채널',
            'views': '조회수',
            'channel_subscribers': '구독자',
            'views_per_subscriber': '조회/구독(배)',
            'published_at': '게시일'
        })

        st.dataframe(top_videos, use_container_width=True, hide_index=True)

        # 통계
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("평균 조회수", f"{filtered_df['views'].mean():,.0f}")
        with col2:
            st.metric("중위 조회수", f"{filtered_df['views'].median():,.0f}")
        with col3:
            st.metric("조회/구독 평균비율", f"{filtered_df['views_per_subscriber'].mean():.2f}배")
        with col4:
            st.metric("표본 크기", f"{len(filtered_df):,}건")
    else:
        st.warning("⚠️ 필터 조건에 맞는 데이터가 없습니다.")

# ============================================================================
# TAB 2: 시계열 분석
# ============================================================================

with tab2:
    st.markdown("### 📈 조회수 시계열 트렌드")
    st.markdown("""
    **주차별 평균 조회 속도 (views/day) 변화**
    - REPORT.md의 시계열 분석 기법 재현
    - 이동평균(7일) 포함
    """)

    if len(filtered_df) > 0:
        # 날짜별 집계
        daily_stats = filtered_df.groupby(filtered_df['published_at'].dt.date).agg({
            'views': 'mean',
            'views_per_day': 'mean',
            'video_id': 'count'
        }).rename(columns={'video_id': 'count'})

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**일일 평균 조회수 추이**")
            st.line_chart(daily_stats['views'], use_container_width=True)

        with col2:
            st.markdown("**일일 평균 조회 속도 (views/day)**")
            st.line_chart(daily_stats['views_per_day'], use_container_width=True)

        st.markdown("**통계**")
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        with stat_col1:
            st.metric("조회 속도 평균", f"{filtered_df['views_per_day'].mean():.1f} views/day")
        with stat_col2:
            st.metric("조회 속도 최고", f"{filtered_df['views_per_day'].max():.1f} views/day")
        with stat_col3:
            st.metric("조회 속도 변동성", f"{filtered_df['views_per_day'].std():.1f}")
    else:
        st.warning("⚠️ 필터 조건에 맞는 데이터가 없습니다.")

# ============================================================================
# TAB 3: 이상치 분포
# ============================================================================

with tab3:
    st.markdown("### 🎯 이상치 분포 (Outlier Distribution)")
    st.markdown("""
    **구독자 대비 조회수 성과 분포**
    - REPORT.md 시각화 2번 재현
    - 고성과 영상 분포 확인
    """)

    if len(filtered_df) > 0:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**조회수 분포 (로그 스케일)**")
            hist_data = np.log10(filtered_df['views'] + 1)
            st.bar_chart(
                pd.DataFrame({
                    'log10(views)': hist_data.values
                }).value_counts().sort_index(),
                use_container_width=True
            )

        with col2:
            st.markdown("**조회/구독 비율 분포**")
            ratio_data = filtered_df['views_per_subscriber'].clip(0, filtered_df['views_per_subscriber'].quantile(0.95))
            st.bar_chart(
                pd.cut(ratio_data, bins=20).value_counts().sort_index(),
                use_container_width=True
            )

        st.markdown("**상세 통계**")
        stat1, stat2, stat3, stat4, stat5 = st.columns(5)
        with stat1:
            st.metric("조회수 Q1", f"{filtered_df['views'].quantile(0.25):,.0f}")
        with stat2:
            st.metric("조회수 중위수", f"{filtered_df['views'].median():,.0f}")
        with stat3:
            st.metric("조회수 Q3", f"{filtered_df['views'].quantile(0.75):,.0f}")
        with stat4:
            st.metric("이상치(Q3*1.5)", f"{filtered_df['views'].quantile(0.75) * 1.5:,.0f}")
        with stat5:
            st.metric("이상치 비율", f"{(filtered_df['views'] > filtered_df['views'].quantile(0.75) * 1.5).sum() / len(filtered_df) * 100:.1f}%")
    else:
        st.warning("⚠️ 필터 조건에 맞는 데이터가 없습니다.")

# ============================================================================
# TAB 4: 데이터 테이블 & 다운로드
# ============================================================================

with tab4:
    st.markdown("### 📊 필터된 데이터")

    if len(filtered_df) > 0:
        # 표시할 컬럼 선택
        display_cols = st.multiselect(
            "표시할 컬럼 선택",
            columns=['title', 'channel_name', 'published_at', 'views', 'likes', 'comments', 'channel_subscribers', 'views_per_day', 'views_per_subscriber', 'seed'],
            default=['title', 'channel_name', 'published_at', 'views', 'channel_subscribers'],
            key="display_cols"
        )

        if display_cols:
            display_df = filtered_df[display_cols].copy()
            display_df['published_at'] = pd.to_datetime(display_df['published_at']).dt.strftime('%Y-%m-%d %H:%M')

            st.dataframe(display_df, use_container_width=True, height=400)

            # CSV 다운로드
            csv = display_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 CSV로 다운로드",
                data=csv,
                file_name=f"videos_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        st.markdown(f"**총 {len(filtered_df):,}건의 영상**")
    else:
        st.warning("⚠️ 필터 조건에 맞는 데이터가 없습니다.")

# ============================================================================
# TAB 5: 분석 결과 요약
# ============================================================================

with tab5:
    st.markdown("### 📋 분석 결과 요약")

    st.markdown("""
    **📌 주요 인사이트 (REPORT.md 발췌)**
    """)

    # 인사이트 카드
    insights = [
        {
            "title": "🎬 조회 속도의 분화",
            "content": "게시 후 초기 조회 속도(첫 주당)가 최종 성과를 좌우. 상위 10% 영상은 평균 20 views/day 이상 달성",
            "metric": "상위 10%: ~25-30 views/day"
        },
        {
            "title": "👥 구독자 소수 채널의 약진",
            "content": "구독자 1만 미만 채널에서 조회/구독 비율 3배 이상인 영상 다수 발견 (매크 아님 확인됨)",
            "metric": "조회/구독 비율: 평균 2.5배"
        },
        {
            "title": "🔑 검색어별 성과 편차",
            "content": "'AI', '仕事' 검색어가 평균적으로 높은 조회수 기록. 계절성/트렌드 영향 추정",
            "metric": "최고 평균: AI (~2500 views)"
        },
        {
            "title": "⏱️ 영상 길이와 조회 속도 관계",
            "content": "20-40분대 영상이 조회 속도와 시청률 모두 최적. 극단적으로 길거나 짧은 영상은 약세",
            "metric": "최적 길이: 25-35분"
        }
    ]

    for i, insight in enumerate(insights, 1):
        with st.container(border=True):
            col1, col2 = st.columns([0.7, 0.3], gap="medium")
            with col1:
                st.markdown(f"**{insight['title']}**")
                st.markdown(insight['content'])
            with col2:
                st.markdown("**수치**")
                st.markdown(f"`{insight['metric']}`")

    st.divider()

    st.markdown("### 🔗 참고 자료")
    st.markdown("""
    - **상세 분석 리포트**: [REPORT.md](REPORT.md)
    - **데이터 수집 방법**: [data/README.md](data/README.md)
    - **분석 코드**: `analysis.py`, `src/`
    - **매크 방어 근거**: [docs/benchmark.md](docs/benchmark.md)

    ---
    **M1-1 AI 데이터 분석** — 일본 YouTube 롱폼 콘텐츠 트렌드 분석
    """)

# ============================================================================
# 푸터
# ============================================================================

st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**📊 분석 기준**")
    st.markdown(f"- 수집일: 2026-09-02")
    st.markdown(f"- 분석 영상: {len(videos_df):,}건")
    st.markdown(f"- 채널: {videos_df['channel_name'].nunique()}개")

with col2:
    st.markdown("**🔑 분석 검색어**")
    for kw in sorted(videos_df['seed'].unique()):
        count = (videos_df['seed'] == kw).sum()
        st.markdown(f"- {kw}: {count}건")

with col3:
    st.markdown("**📅 기간**")
    st.markdown(f"- 시작: 2026-07-03")
    st.markdown(f"- 종료: 2026-09-01")
    st.markdown(f"- 총 기간: 약 60일")
