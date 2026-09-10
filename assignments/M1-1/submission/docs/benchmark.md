# 벤치마킹 — 깃허브의 유사 프로젝트

**2026-09-03.** 이 프로젝트와 비슷한 걸 만드는 곳이 있는지 깃허브에서 찾아
방법론을 비교했다. 다음에 또 찾아볼 일이 있으면 여기부터 본다 — 이미 본 것을
다시 찾느라 시간을 쓰지 않는다.

## 어떻게 찾았나

`gh search repos`로 다음 키워드를 돌렸다. 재현하려면 그대로 쓴다.

```bash
gh search repos "youtube outlier" --limit 15
gh search repos "youtube niche finder" --limit 10
gh search repos "youtube trend research tool"
gh search repos "youtube api streamlit dashboard"
gh search repos "youtube content research pipeline"
gh search repos "youtube small channel viral"
gh search repos "youtube channel momentum score"
gh search repos "youtube video velocity age"
gh search repos "youtube api quota tracker dashboard"
```

뒤 세 개(모멘텀·나이 보정·할당량 대시보드)는 **결과가 0건이었다.** 이게
그 자체로 신호다 — 아래 「우리가 이미 더 나은 것」 참고.

---

## 가장 가까운 후보 3개

### [yuben-app](https://github.com/shkuratovdesigner/yuben-app)

```
16★ · MIT · Python/FastAPI + React · 2026-08-31 마지막 커밋
```

> Find the YouTube videos that massively outperform their channels —
> and learn exactly why.

우리와 가장 가까운 한 줄 정의다. 핵심 신호는 **VSR = 조회수÷구독자** —
우리 `subscriber_view_ratio` 와 같은 지표다.

**특징**
- 로컬 실행(FastAPI + React, 한 프로세스). 호스팅 없음, 텔레메트리 없음
- API 키를 OS 키체인에 저장. 프런트엔드는 키를 쓸 순 있어도 읽어올 순 없음
- LLM 13개 제공자를 어댑터 하나로 (`detect/models/check_env/stream`)
- **참여율로 매크 필터** — 조회수 1,000회당 좋아요 1.5개 미만이면 순위에서 빼고
  뺀 개수(`counts.promoted_excluded`)를 그대로 보고
- **신뢰 규칙(Trust rule)** — 모든 video_id·숫자는 결정론적 파이프라인 JSON에서만
  나온다. LLM 은 서술만 하고, 모델이 만든 video_id 는 절대 화면에 안 낸다
- 국가 선호 정렬 — `regionCode`/`relevanceLanguage` 가 소프트 힌트일 뿐이라는
  걸 알고, 채널이 자진 신고한 국가로 **정렬**만 하지 필터링은 안 함
  (우리도 `config.py` 주석에 같은 결론을 독립적으로 적어 두고 있었다)
- 키 없이 번들 픽스처로 UI 전체를 볼 수 있는 목업 모드

### [yt-research-agent](https://github.com/IsaiahDupree/yt-research-agent)

```
0★ · 2026-07-06 마지막 커밋
```

> A programmatic YouTube content-research pipeline for serious operators.

```
니치 + 시드 채널
  ↓
소스: YouTube API · Google Trends(관심도 곡선) · Reddit(화제 가속도)
  ↓
분석: 이상치 탐지 · 조회 속도 · 트렌드 신호 · 리텐션 추정
  ↓
0~100 점수(가중치 9개, 전부 문서에 근거 명시)
  ↓
LLM 브리프: 훅 · 제목 후보 · 썸네일 컨셉 · 개요
```

우리 Channel Fit + Production Brief와 목적이 같다. 다른 점은 **유튜브 신호
하나가 아니라 Trends·Reddit까지 삼각측량**한다는 것과, HIGH/MEDIUM/LOW가
아니라 **0~100 점수를 쓴다**(대신 가중치를 전부 공개한다고 주장).

### [youtube-outlier-finder](https://github.com/slaavass/youtube-outlier-finder)

```
5★ · MIT · TypeScript · 2026-07-25 마지막 커밋
```

Shorts 전용. 신호는 **채널의 최근 15편 중앙값 ÷ 구독자**. 나이 보정은 없고
대신 고정 임계값 6개를 동시에 통과해야 한다.

```
구독자 ≤ 50,000        중앙값 ÷ 구독자 ≥ 10배
Shorts 중앙 조회 ≥ 75,000   채널 나이 ≤ 12개월
영상 길이 ≤ 120초         표본 ≥ 4편
```

---

## 그 외 찾은 것 (참고만)

| 저장소 | 별 | 최종 수정 | 한 줄 |
|---|---:|---|---|
| [Niche-Finder](https://github.com/johanfortus/Niche-Finder) | 15 | 2025-06 | Kaggle 트렌딩 데이터셋 + K-Means/FP-Growth 로 니치 군집화. 실시간 채널 탐지가 아니라 정적 데이터셋 분석이라 목적이 다르다 |
| [youtube-outlier-researcher](https://github.com/mikeydub68/youtube-outlier-researcher) | 0 | 2025-11 | 경쟁 채널 추적 + 채널 평균 대비 바이럴 판정 |
| [easeusmedia/youtube-outlier](https://github.com/easeusmedia/youtube-outlier) | 0 | 2026-08 | 이상치 점수 + 자막 전체를 PDF 로 묶어 냄 |
| [YoutubeOutliers](https://github.com/noveoko/YoutubeOutliers) | 2 | 2024-04 | 이상치 탐지 도구 + 데이터셋 |

이 넷은 방법론이 위 3개와 겹치거나(구독자 대비 배수) 목적이 달라서(정적
데이터셋) 더 깊이 보지 않았다.

---

## 채택한 것

### ✅ 참여율로 매크 방어 (yuben-app)

**우리에게 이 방어가 전혀 없었다.** 조회수만 보고 이상치를 뽑았는데, 매크
돌린 영상이 섞여도 걸러낼 방법이 없었다.

문턱값(1.5)을 그대로 가져오지 않고 **우리 데이터로 다시 확인**했다 —
이 프로젝트의 원칙이 "숫자는 실측 분포를 보고 정한다"라서다.

```
2026-09-03 · 632건 중 likes 있는 623건
참여율(좋아요÷조회수×1,000) 중앙 9.15 · 25% 5.05 · 75% 17.33
1.5 미만  67건 (10.6%)
```

1.5는 우리 분포에서도 뚜렷한 하위 극단이라 그대로 썼다. `config.py` 에
`MIN_ENGAGEMENT_PER_1K`, `src/analysis.py` 의 `add_metrics()` 에 반영했다.
행은 지우지 않고 `subscriber_view_ratio` 만 결측 처리한다 — 매크 의심
영상은 「구독자 대비 보너스」만 못 받고, Video Score는 나이 보정 백분위
하나로 계산된다(사라지지도 깨지지도 않는다).

**정직한 결과** — 구독자 1,000명 이상(비율을 재는 대상)만 놓고 보면
지금 데이터에는 「참여율 바닥 & 구독대비 5배 이상」이 0건이다. 지금 이상치
목록이 실제로 오염돼 있었다는 증거는 아직 없다. 다만 롱테일 검색어로 구독자
아주 적은 채널이 계속 느는 추세라(REPORT.md §4), 증거가 나오고 나서
고치면 그 사이 뽑은 검색어 후보가 이미 오염된다 — 그래서 미리 깔았다.

## 보류한 것

### ⏸ Trends·Reddit 삼각측량 (yt-research-agent)

유튜브 신호만이 아니라 구글 트렌드·레딧 화제성까지 보는 건 진짜 기능
격차다. 다만:

- Google Trends 는 공식 API 가 없다. 비공식 라이브러리(pytrends 등)는
  자주 깨진다 — 이 프로젝트의 "조용히 실패하면 안 된다" 원칙과 부딪힌다
- Reddit 은 별도 인증·할당량 체계가 필요해 지금의 "화면은 API 를 절대
  자동으로 안 부른다" 구조에 축 하나를 더 넣는 일이다

지금 당장 할 일은 아니다. 나중에 데이터가 충분히 쌓여 "유튜브 신호만으론
부족하다"는 게 실측으로 확인되면 다시 본다.

### ⏸ 목업 모드 (yuben-app)

키 없이 번들 픽스처로 UI를 볼 수 있게 하는 것. 과제 시연·리뷰 상황에는
편하지만, 매일 혼자 쓰는 개인 도구에는 우선순위가 낮다.

---

## 우리가 이미 더 앞선 것

**나이 보정이 없다 — 찾은 도구 전부.** youtube-outlier-finder는 고정
배수 하나뿐이고, yuben-app도 티어(2×/5×)만 있지 「같은 나이대 안에서」
비교하지 않는다. 우리가 `+16,162%` 버그로 배운 것 — 나이를 안 맞추면
어린 영상이 무조건 이긴다 — 을 이 도구들은 신경 쓰지 않는다.

**Video Score / Channel Score 분리도 못 찾았다.** "영상 하나가 튀었나"와
"채널 자체가 크는 중인가"를 따로 묻는 도구가 없었다. 벤치마킹 검색에서
"channel momentum score"·"video velocity age" 가 0건이었던 것도 같은
맥락으로 읽힌다 — 흔한 패턴이 아니다.

**댓글 → 채널별 재해석 → Production Brief** 까지 이어지는 파이프라인은
yt-research-agent가 브리프를 내는 것 정도 말고는 아무도 안 한다.

## 이미 우리 architecture 에 있던 원칙 — 이번에 이름을 붙임

yuben-app의 「신뢰 규칙(Trust rule)」— LLM 은 서술만 하고, video_id·숫자는
결정론적 파이프라인에서만 나온다 — 을 확인해 보니 **우리도 이미 이렇게
짜여 있었다.** `channel_fit.judge()`도 `production_brief.build()`도
`video_id` 를 파이썬 인자로 받지, LLM JSON에서 파싱하지 않는다.

다만 이게 문서 어디에도 원칙으로 적혀 있지는 않아서, 다음에 누가(다음
세션 포함) 코드를 확장할 때 조용히 깨질 수 있다 → `tech.md` §6-B에
명문화했다.
