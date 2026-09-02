# Japanese Long-form Opportunity Radar

일본 YouTube 롱폼(10분 이상) 공개 데이터를 매일 모아, **작은 채널인데 잘 된
영상**과 실제로 성장 중인 채널을 찾는다. 찾은 소재는 Claude 웹에 붙여넣을
**한 장**으로 뽑아 쓴다.

프로그램이 대본을 쓰지 않는다 — 재료만 모아 준다.

```
매일 07:00  자동 수집 → CSV 에 한 줄씩 쌓임
아침        화면 열기 → 5분 안에 소재 고르기 → [복사] → Claude 웹
```

문서 — [prd.md](prd.md) 무엇을 만드나 · [tech.md](tech.md) 어떻게 쓰나 ·
[task.md](task.md) 어디까지 했나 · [REPORT.md](REPORT.md) 분석 결과 ·
[docs/automaker-contract.md](docs/automaker-contract.md) automaker 와 주고받는 파일

## 두 채널

Radar 는 하나다. 수집·점수는 공통이고, **같은 데이터를 두 관점으로 읽는다.**

```
🛡️ 제도와 현실의 덫       연금·세금 함정 / 빈집·수선적립금 / 개호 부담
🍂 정년 후 고독과 자존감    직함 상실·재취업 / 황혼이혼 / 소규모 벌이
```

`data/config/channels.json` 에 있다. 코드에 채널 이름을 박지 않는다.

## 이렇게 씁니다

### 화면 열기

`앱실행.cmd` 를 두 번 누른다. 브라우저가 열린다.
(검은 창은 켜 둔 채로. 닫으면 화면도 꺼진다.)

### 매일 아침 5분

```
1. ☀️ 오늘의 발견 을 연다
2. 위에서 채널을 고른다        [전체] [🛡️ 제도와 현실의 덫] [🍂 정년 후 고독과 자존감]
3. 🔥 지금 오르는 중  10건을 훑는다   ← 진짜로 지금 오르는 것
4. 🆕 어제 새로 들어온 것 10건을 훑는다  ← 게시일을 꼭 같이 본다
5. 마음에 드는 것의 [열기] 를 눌러 실제 영상을 본다
6. 쓸 만하면 아래 [한 장 만들기] → 복사 → Claude 웹에 붙여넣기
```

여기까지가 «소재를 고르는» 일이다. 보통 5분이면 끝난다.

### 만들기로 정했으면

```
7. 📋 Claude 웹으로 넘기기 아래 «🎬 제작 후보로 확정하기»
8. 어느 채널에서 만들지 고른다
9. [댓글 받고 브리프 만들기]        1~2분 걸린다 (댓글 수집 + 분석 + 판정)
10. Channel Fit 7개 항목과 브리프를 읽는다
11. [Claude 대본용 자료 만들기] → 복사 → Claude 웹
12. 나온 대본을 data/scripts/{채널}/ 에 저장
```

**[FACT CHECK] 표시가 붙은 것은 확인 전에 영상으로 만들지 않는다.**
연금·세금·상속은 틀리면 보는 사람이 실제로 손해를 본다.

### 데이터는 알아서 쌓인다

매일 아침 7시에 작업 스케줄러가 수집한다. 손댈 것이 없다.
직접 돌리고 싶으면 `⏰ 자동 실행` 탭에서 상태를 보고, 터미널에서

```bash
python -m src.snapshot_collector
```

---

## 준비

```bash
pip install -r requirements.txt
```

```bash
copy .env.example .env
```

`.env` 에 키를 넣는다. **코드에는 절대 적지 않는다.**

| 키 | 쓰임 | 없으면 |
|---|---|---|
| `YOUTUBE_API_KEY` | 수집·스냅샷 | 아무것도 못 한다 |
| `OPENAI_API_KEY` | 제목 한글화, 검색어 뜻 | 일본어 원문 그대로 나온다 |

YouTube 키는 Google Cloud Console → YouTube Data API v3 사용 설정 → API 키. 무료다.

번역 제공자를 갈아탈 때는 `config.py` 의 네 줄만 고친다.
모델 이름을 모르면 자동으로 찾아 맞춰 준다.

```bash
python tools/setup_translate.py https://copa.codyssey.kr/v1
```

## 실행

**웹페이지는 `app.py` 하나다.**

```bash
streamlit run app.py --server.address 127.0.0.1 --server.port 8502
```

화면은 **저장된 CSV 만 읽는다.** 필터를 만져도 API 를 부르지 않는다.
댓글·자막·판정처럼 돈이 드는 것은 **버튼을 눌렀을 때만** 부른다.

> `mockup/index.html` 은 **웹페이지가 아니다.** 2026-09-02 오전에 화면을
> 어떻게 그릴지 미리 그려 본 보관본이고 버튼이 동작하지 않는다.
> 지우지 않고 기록으로 둔다 — [mockup/README.md](mockup/README.md)

```bash
python -m src.collector --dry-run     # API 를 안 부르고 계획만 본다
python -m src.collector               # 검색 → 필터 → videos.csv  (하루 1회)
python -m src.snapshot_collector      # 조회수 갱신           (하루 1회)
python -m src.channel_analyzer        # 채널 검증
python analysis.py                    # 그래프 3개 + 인사이트 숫자
```

`run_daily.cmd` 를 윈도우 작업 스케줄러에 매일 1회로 걸어 두면 된다.
`.cmd` 는 **CRLF + ASCII 로 저장해야 한다** — LF 면 스케줄러가 조용히 실패한다.

## 화면

색·글꼴은 `.streamlit/config.toml` 에 있다. 주황은 영상 점수, 청록은 채널
점수와 링크 — **두 점수를 합치지 않는다는 것을 색으로도 보인다.**

| 탭 | 무엇 |
|---|---|
| ☀️ 오늘의 발견 | 지금 오르는 중 · 어제 새로 들어온 것 · **Claude 웹으로 넘기기** |
| 🔥 떡상영상 | Video Score 상위 30 |
| 📈 시계열 | 게시 주차별 조회 속도 |
| 🎯 Outlier 분포 | 구독자 대비 조회수 |
| 📊 데이터 | 전체 표 + CSV 내려받기 |
| 🔎 검색어 관리 | 검색어별 성과 · 후보 제안 · 추가/빼기 |

표의 **[열기]** 를 누르면 유튜브가 열린다. 숫자만 보고는 «이게 진짜인가» 를
확인할 수 없다. **영상수**는 채널이 올려 둔 전체 편수다 — 구독자와 함께 보면
«영상이 쌓여 큰 채널»과 «몇 편으로 뜬 채널»이 갈린다.

## 스냅샷은 오늘부터

`snapshot_collector.py` 는 **개발 순서의 항목이 아니다.** 첫날부터 매일 돈다.

영상 하나의 스냅샷 한 장으로는 그 영상이 처음부터 잘 됐는지 지금 막 터지는지
알 수 없다. 며칠 쌓여야 «지금 가속 중인가» 를 알 수 있고, **지나간 날의
조회수는 나중에 받을 수 없다.**

싸다 — `videos.list` 는 50개를 묶어 1 unit 이라 300개를 추적해도 하루 12 units.

증가량은 **관측이 6시간 넘게 벌어져야** 계산한다. 같은 날 두 번 돌리면
0.03일 같은 값으로 나누게 되어 몇 건의 잡음이 하루 수만 건으로 부풀어 오른다.

## 할당량

`search.list` 는 `videos.list` 보다 **100배 비싸다.** 실질 상한은 하루 약 100회.

```
수집       1,615 units   ← 검색 16회가 거의 전부
스냅샷        12 units
채널 검증   40~57 units
```

정상 운영은 하루 약 1,630 units(16%). **수집을 여섯 번 돌리면 하루치가 동나고
그날은 스냅샷도 못 남긴다.** 그래서 같은 날 두 번째 수집은 API 를 부르기 전에
막는다 — 정말 필요하면 `--force`.

쓴 양은 `data/raw/quota_log.csv` 에 쌓인다.

## 파일

```
.streamlit/config.toml    화면 색·글꼴 (공식 테마 옵션만 씀)
src/config.py             설정. 값을 바꾸려면 여기만 고친다
src/storage.py            CSV 읽기·쓰기
src/youtube.py            API 호출 + 할당량
src/language.py           일본어 판정
src/collector.py          검색 수집
src/snapshot_collector.py 조회수 갱신 + Watchlist
src/channel_analyzer.py   채널 검증 (Phase B)
src/analysis.py           지표 계산 — 모든 수식이 여기 있다
src/translate.py          번역 (제공자 교체 가능)
src/subtitles.py          자막 발췌 (yt-dlp)
src/export.py             내보내기 한 장
src/seeds.py              검색어 목록과 후보
src/channels.py           채널 프로필 (2채널)
src/channel_fit.py        우리 채널에서 만들 가치가 있나 (HIGH/MEDIUM/LOW)
src/comments.py           댓글 수집 + 분석
src/production_brief.py   브리프 조립 + Claude 대본용 자료
prompts/                  channel_fit · comment_analyzer · script_writer
mockup/index.html         보관용 목업 (동작 안 함 · 09-02 오전 상태)
mockup/build.py           목업 데이터 다시 뽑기

analysis.py               그래프 3개 + 인사이트
app.py                    화면
tools/backfill_titles.py  빠진 번역 채우기
tools/setup_translate.py  번역 모델 자동 설정

data/raw/videos.csv           변하지 않는 정보
data/raw/video_snapshots.csv  시간에 따라 변하는 정보
data/raw/quota_log.csv        하루에 얼마나 썼나
data/raw/seeds.json           검색어 (없으면 config.SEEDS 가 기본값)
data/raw/subs/                자막 캐시
data/raw/comments/            댓글 원본
data/config/channels.json     채널 정체성
data/processed/channel_fit.csv  채널 적합도 판정
data/processed/comments/      댓글 분석
data/briefs/{channel}/        Production Brief
data/scripts/{channel}/       Claude 대본 (사람이 저장)
```

**수식은 `src/analysis.py` 에만 있다.** 화면에서 다시 계산하지 않는다.

## 이 프로그램의 실패는 조용하다

형식이 틀리면 에러가 아니라 「0개」로 나오고, 계산이 틀리면 **그럴듯한 숫자**가
나온다. 실제로 걸린 것들이다.

| 증상 | 원인 |
|---|---|
| 주제 성장률 `+16,162%` | 나이 보정 없이 기간 비교 |
| Channel Baseline `2,941배` | 옛 영상의 ADViews 가 0 에 수렴 |
| 그래프 라벨 `孤独` → `孤` | 한글과 일본 한자를 같이 가진 폰트가 없다 |
| 낱말 뜻이 「맞춤형 주택 짓기 노하우」 | 제목용 프롬프트를 낱말에 씀 |
| 자막 「없음」 | 실제로는 `429` (요청 과다) |
| CSV 값이 한 칸씩 밀림 | 헤더는 그대로 두고 열만 늘림 |
| 뺄 검색어를 거꾸로 짚음 | 이상치가 아니라 중앙 점수로 줄 세움 |

**돌린 뒤 숫자를 눈으로 본다.** 「돌아갔다」는 확인이 아니다.
말이 안 되게 큰 값은 성공이 아니라 버그의 신호다.

## 주의

- `.env` 는 git 에 올리지 않는다. 키는 코드·URL·로그에 적지 않는다
- Streamlit 은 `--server.address 127.0.0.1` 로만 띄운다
- `src/` 밑을 고쳤으면 **Streamlit 을 다시 띄운다.** `app.py` 와 달리
  하위 모듈은 자동으로 다시 읽지 않아 옛 코드가 계속 돈다
