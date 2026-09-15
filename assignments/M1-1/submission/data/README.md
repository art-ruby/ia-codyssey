# 데이터 안내

이 폴더에는 원본 CSV를 올리지 않았다. **YouTube API Services Terms of
Service**는 API로 수집한 데이터의 재배포를 제한한다 — 그래서 `data/raw/`,
`data/processed/`는 `.gitignore`로 막고, 대신 **수집 스크립트 전체**와
**실제로 수집했던 규모·기간·처리 방법**을 남긴다. ([REPORT.md](../REPORT.md)
§3, §8-B, §9 에 상세)

## 실제 분석에 쓰인 데이터 (2026-09-02 수집 기준)

| 항목 | 값 |
|---|---|
| 출처 | YouTube Data API v3 (공개 메타데이터만) |
| 수집 영상 | 777건 |
| 분석 대상 | 632건 (조회수 스냅샷이 있는 것) |
| 채널 수 | 449개 |
| 게시 기간 | 2026-07-03 ~ 2026-09-01 (약 60일) |
| 필터 | 10분 이상 · 일본어(가나 비율 10%+ 또는 defaultAudioLanguage=ja) |

## 직접 재현하는 방법

```bash
pip install -r ../requirements.txt
copy ..\.env.example ..\.env      # YOUTUBE_API_KEY 를 넣는다 (무료, Google Cloud Console)

cd ..
python -m src.collector           # 검색 → 필터 → data/raw/videos.csv
python -m src.snapshot_collector  # 조회수 스냅샷 → data/raw/video_snapshots.csv
python analysis.py                # 그래프 3개(images/) + 인사이트 숫자 출력
```

`src/collector.py`가 검색어(`老後·お金·仕事·孤独·AI·人生·SNS·住宅`)로
YouTube를 검색하고, `src/snapshot_collector.py`가 조회수를 갱신한다. 두
스크립트 모두 표준 라이브러리(`urllib`)만 쓴다 — 추가 설치가 필요 없다.

## 스키마 (수집되면 이 모양으로 쌓인다)

**`data/raw/videos.csv`** — 변하지 않는 정보
```
video_id · title · description · channel_id · channel_name
published_at · duration_seconds · default_audio_language
detected_language · kana_ratio · seed · found_at
```

**`data/raw/video_snapshots.csv`** — 시간에 따라 변하는 정보
```
collected_at · video_id · views · likes · comments
channel_subscribers · hidden_subscriber_count · watch_status
```

두 파일을 나눈 이유: 조회수처럼 매일 바뀌는 값과 제목처럼 고정된 값을
합치면, 고정 정보를 매일 다시 저장하게 된다.
