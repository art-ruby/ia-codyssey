# 일본 YouTube 롱폼 콘텐츠 트렌드 분석

**M1-1 — AI 데이터 분석: 데이터 기반 트렌드 분석** 과제 제출물.

일본 YouTube 롱폼 영상 632건(구독자·조회수 시계열 포함)을 분석해, **구독자는
적은데 유난히 잘 된 영상**이 어떤 조건에서 나오는지 살펴본 리포트다. 분석
전문은 [REPORT.md](REPORT.md)에 있다.

## 빠른 실행

```bash
pip install -r requirements.txt
python analysis.py
```

`images/`에 그래프 3개를 다시 그리고, [REPORT.md](REPORT.md)에 옮긴 인사이트
수치를 콘솔에 그대로 출력한다. 
이유와 재현 방법은 [data/README.md](data/README.md)에 있다.

## 폴더 구조

```

├── README.md            이 문서 — 실행 방법
├── REPORT.md             분석 리포트 (주제·질문·데이터·시각화·인사이트·결론·AI 사용 로그)
├── requirements.txt
├── .env.example          YOUTUBE_API_KEY 템플릿 (실제 키 없음)
├── analysis.py            그래프 3개 + 인사이트 수치를 뽑는 진입점
├── images/
│   ├── 01_view_velocity_trend.png     게시 주차별 평균 조회 속도
│   ├── 02_subscriber_vs_views.png     구독자 대비 조회수 (Outlier 분포)
│   ├── 03_topic_performance.png       검색어별 성과·공급량
│   └── screenshot_dashboard.png       보너스: 탐색용 웹 대시보드
├── src/
│   ├── analysis.py        지표 계산 — Video Score·Channel Score 등 모든 수식
│   ├── config.py           설정값 (가중치·구간·임계값과 그 근거 주석)
│   ├── storage.py          CSV 읽기/쓰기
│   ├── seeds.py             검색어 목록·한글 라벨
│   ├── collector.py        데이터 수집 — 검색→필터→저장 (원본 데이터 대신 제출)
│   ├── snapshot_collector.py  조회수 스냅샷 갱신
│   ├── youtube.py          YouTube Data API v3 클라이언트 + 할당량 관리
│   └── language.py          일본어 여부 판정
├── docs/
│   └── benchmark.md        REPORT.md가 인용하는 매크(구매 조회수) 방어 근거
└── data/
    └── README.md            데이터 출처·수집 규모·재현 방법 (원본 CSV는 미포함)
```

## 과제 요구사항 대조

| 요구사항 | 위치 |
|---|---|
| 분석 리포트 (주제·질문·데이터·시각화·인사이트·결론/한계) | [REPORT.md](REPORT.md) |
| 데이터 100개 이상 | 632건 (요구치의 6배) — [data/README.md](data/README.md) |
| 분석 질문 3개 이상 | REPORT.md §2 (4개) |
| 시각화 2개 이상(권장 3개+) | `images/01~03` (3개) — REPORT.md §6 |
| 시계열 분석 기법 2개 이상 | REPORT.md §5 (이동평균·변화율·구간별 통계 3개) |
| 인사이트 3개 이상 + 관찰/해석 구분 | REPORT.md §7 (4개, 관찰→해석→행동 형식) |
| Python 코드 (원본 데이터 또는 수집 스크립트) | `analysis.py`, `src/*.py` — 수집 스크립트 제출 |
| requirements.txt | [requirements.txt](requirements.txt) |
| 데이터 출처/수집 방법/라이선스 | REPORT.md §8-B, [data/README.md](data/README.md) |
| AI 사용 로그 (작업/이유/검증) | REPORT.md §10 |
| **보너스** — 대시보드 (스크린샷 + 시나리오) | `images/screenshot_dashboard.png` — 아래 참고 |

## 보너스 — 탐색용 웹 대시보드

`images/screenshot_dashboard.png`는 이 분석과 같은 데이터를 읽는 Streamlit
대시보드다. 표(🔥 떡상영상 · 📈 시계열 · 🎯 Outlier 분포 · 📊 데이터)에서
**기간·검색어·구독자 구간 필터를 바꿔가며** 탐색할 수 있고, 결과를 CSV로
내려받을 수 있다. 화면은 저장된 CSV만 읽어 필터를 조작해도 API를 부르지
않는다. 대시보드 전체 소스는 이 과제의 핵심 분석 범위를 넘어서는 별도
파이프라인(댓글 분석·제작 브리프 등)에 함께 물려 있어 이번 제출에는 포함하지
않았다 — 별도 요청 시 정리해서 추가할 수 있다.

## 참고

- 분석 결과·인사이트: [REPORT.md](REPORT.md)
- 데이터 출처·수집 방법·재현: [data/README.md](data/README.md)
- 매크 방어 임계값 근거: [docs/benchmark.md](docs/benchmark.md)
