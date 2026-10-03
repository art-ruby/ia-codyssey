# AI 동향 '새 소식' 설계

- 작성일: 2026-10-04
- 상태: 설계 승인됨, 구현 전
- 관련 화면: S04 AI 동향, 프로젝트·설정
- 선행 조건: 링크 가져오기(`server/app/features/materials/fetcher.py`, SSRF 방어) 검토·반영

## 1. 목표와 배경

AI 동향 화면은 지금 사용자가 직접 넣은 자료만 중요도 순으로 보여준다. 외부 최신 소식은 들어오지 않는다. 이 설계는 사용자가 고른 공식 블로그·커뮤니티의 새 글을 모아 AI 동향 위쪽에 '새 소식'으로 보여주고, 원하는 글만 자료로 저장해 기존 분석·검토·승인 흐름에 넣는다.

PRD 61행은 "외부 뉴스·SNS 자동 수집"을 후속 단계로 두었다. 이 설계는 그 일부(사용자가 고른 RSS·Atom 피드의 수집)를 앞당기는 범위 변경이며, 구현할 때 `docs/decisions.md`에 기록한다.

### 사용자 결정 (2026-10-04)

| 항목 | 결정 |
|---|---|
| 출처 | 공식 블로그·뉴스룸 + 커뮤니티 |
| 가져오는 때 | AI 동향 화면을 열 때 마지막 수집이 6시간을 넘었으면 자동, 그리고 '지금 새로고침' 버튼 |
| 두는 곳 | AI 동향의 '새 소식' 칸. 고른 글만 '자료로 저장' |
| 순서 | 관심 분야·프로젝트 키워드에 맞는 글 먼저, 나머지는 최신순. AI 호출 없음 |
| 출처 관리 | 기본 목록 + 설정에서 켜기·끄기·추가 |
| 구현 방식 | A안: 서버가 수집해 Firestore에 저장, 화면은 저장된 소식을 바로 읽음 |

### 버린 방식

- 요청마다 실시간 수집(B안): 출처 6곳 이상을 매번 읽어 화면이 느리고, 저장·숨김 상태를 기억할 수 없다.
- 브라우저 직접 수집(C안): 대부분의 피드가 CORS로 막히고 CSP를 크게 열어야 한다.

## 2. 범위

- **포함:** 개인 모드의 피드 수집·저장·표시, 키워드 우선 정렬, 자료로 저장, 숨기기·되돌리기, 출처 켜기·끄기·추가·삭제, 30일·300건 정리.
- **제외:** 예약 수집, AI 요약·중요도 판단, 웹페이지 긁어오기(예: Anthropic), YouTube 채널, 검색 API, 읽음 표시, 알림, 인기 점수 표시.
- **모드:** 개인 모드에서만 수집·표시한다. 표본 모드 화면은 "새 소식은 개인 모드에서 볼 수 있습니다."만 보이고, 소식 API는 표본 모드 요청을 422로 거부한다. 표본 시연 데이터에 외부 글이 섞이지 않게 하기 위해서다.

## 3. 데이터

모든 문서는 기존 저장소 계층(`server/app/core/firestore.py`)을 거치며 `owner_id`·`mode` 필드를 가진다.

### `news_sources`

| 필드 | 설명 |
|---|---|
| `name` | 표시 이름 (40자) |
| `feed_url` | RSS·Atom 주소 (http·https, 기본 포트) |
| `kind` | `official` \| `community` |
| `enabled` | 켜짐 여부 |
| `builtin_key` | 기본 출처면 키, 직접 추가한 출처면 null |
| `version`, `created_at`, `updated_at` | 기존 규칙 |

처음 조회할 때 기본 목록으로 문서를 만든다. 사용자당 최대 20곳. 기본 출처는 끌 수만 있고 삭제할 수 없다.

### `news_items`

문서 ID는 정규화한 링크(기존 `url_keys`의 비교 키)의 해시다. 같은 글은 한 번만 저장된다.

| 필드 | 설명 |
|---|---|
| `source_id`, `source_name`, `kind` | 출처 |
| `title` | 200자, 공백 정리 |
| `link` | 원문 주소, http·https만 |
| `summary` | 피드 요약에서 HTML 태그를 지운 글, 500자 |
| `published_at` | 피드 게시 시각(UTC), 없으면 null |
| `fetched_at` | 처음 수집한 시각 |
| `saved_material_id` | 자료로 저장했거나 같은 URL 자료에 연결된 경우 자료 ID |
| `hidden` | 숨김 여부 |

### `news_state` (사용자당 문서 1개)

| 필드 | 설명 |
|---|---|
| `last_success_at` | 마지막으로 한 곳 이상 성공한 수집 시각 |
| `last_attempt_at` | 마지막 수집 시도 시각 |
| `refreshing_until` | 수집 중 표시의 기한(시작 + 3분). 지나면 없는 것으로 본다 |
| `sources` | 출처별 마지막 결과 `{source_id: {ok, count, error}}` |

### 정리

수집이 끝날 때마다, 저장하지 않은 글 중 `fetched_at`이 30일 지난 것을 지운다. 그 뒤에도 300건이 넘으면 저장하지 않은 오래된 글부터 지운다. 저장한 글(`saved_material_id` 있음)은 지우지 않는다.

## 4. 수집 흐름

1. `GET /api/news`는 저장된 소식과 상태를 바로 돌려준다.
2. `last_attempt_at`이 6시간을 넘었고 수집 중이 아니면, 트랜잭션으로 `refreshing_until`을 차지한 뒤 BackgroundTasks로 수집을 시작하고 응답에 `refreshing: true`를 담는다. 동시 요청 중 하나만 차지한다.
3. 화면은 `refreshing`이면 5초 간격으로 최대 6번 다시 불러온다.
4. `POST /api/news/refresh`는 6시간 조건을 무시한다. 다만 수집 중이거나 마지막 시도가 5분 이내면 수집하지 않고 현재 상태만 돌려준다.

### 출처 하나 읽기

- 외부 접근은 `fetcher`의 주소 검사(공개 IP만, IP 고정, 리다이렉트 재검사, 포트 80·443, 쿠키·인증·프록시 미사용)와 크기 2MiB·시간 15초 제한을 그대로 쓴다. 허용 형식에 `application/rss+xml`, `application/atom+xml`, `application/xml`, `text/xml`을 더한 피드 전용 함수를 둔다.
- XML은 표준 라이브러리 `xml.etree.ElementTree`로 읽는다. `<!DOCTYPE`가 있는 문서는 파싱 전에 거부한다(엔티티 확장 차단).
- RSS(`item`)와 Atom(`entry`)을 모두 읽는다. 제목·링크가 없거나 링크가 http·https가 아닌 글은 건너뛴다.
- 게시 시각 내림차순으로 정렬해 출처당 최신 20건만 본다. 이미 있는 ID는 건너뛰어 숨김·저장 상태를 덮어쓰지 않는다.
- 출처는 차례로 읽고 전체 수집은 90초 안에 끝낸다. 남은 출처는 `timeout`으로 기록한다.

## 5. 기본 출처

2026-10-04에 서비스 User-Agent로 실제 응답을 확인했다.

| 키 | 이름 | 주소 | 종류 | 기본값 | 확인 |
|---|---|---|---|---|---|
| `openai` | OpenAI News | https://openai.com/news/rss.xml | 공식 | 켜짐 | 200, 약 760KB, 1,245건 |
| `google-ai` | Google AI 블로그 | https://blog.google/technology/ai/rss/ | 공식 | 켜짐 | 200 |
| `deepmind` | Google DeepMind 블로그 | https://deepmind.google/blog/rss.xml | 공식 | 켜짐 | 200 |
| `huggingface` | Hugging Face 블로그 | https://huggingface.co/blog/feed.xml | 공식 | 켜짐 | 200 |
| `geeknews` | GeekNews | https://news.hada.io/rss/news | 커뮤니티 | 켜짐 | 200, Atom |
| `hn-ai` | Hacker News (AI, 100점 이상) | https://hnrss.org/newest?q=AI&points=100 | 커뮤니티 | 켜짐 | 200, 1~8초 |
| `reddit-localllama` | Reddit r/LocalLLaMA | https://www.reddit.com/r/LocalLLaMA/.rss | 커뮤니티 | 꺼짐 | 200, 연속 요청 시 429 |

Anthropic은 공식 RSS가 없어(404) 기본 목록에 넣지 않는다.

## 6. 키워드와 순서

- **키워드:** 설정의 `interests`를 `·`, `/`, `,`로 나누고 앞뒤 공백을 지운다. 활성 프로젝트 이름을 더한다. 2자 미만은 버린다.
- **일치:** 제목과 요약에서 대소문자 구분 없이 찾는다. 영문·숫자로만 된 키워드는 단어 경계로 찾는다(`API`가 `rapid`에 걸리지 않게). 한글이 들어간 키워드는 부분 일치로 찾는다.
- **순서:** 숨긴 글을 빼고, 키워드가 맞은 글 묶음을 위에, 나머지를 아래에 둔다. 각 묶음은 `published_at`(없으면 `fetched_at`) 내림차순이고, 같으면 ID 순이다. 응답은 처음 30건과 다음 커서를 준다.
- **응답 항목:** 글 필드와 `matched_keywords` 배열.
- 인기 점수는 쓰지 않는다(PRD S04 "외부 인기 수치를 표시하지 않는다").

## 7. API

| 메서드·경로 | 동작 |
|---|---|
| `GET /api/news?cursor=` | `{items, next_cursor, state: {refreshing, last_success_at, last_attempt_at, failures: [{source_name, error}]}}` |
| `POST /api/news/refresh` | 4장 규칙으로 수집을 시작하고 `GET`과 같은 형식으로 응답 |
| `POST /api/news/{id}/save` | 자료로 저장. 중복 요청 키 필수. `{item, material_id, created}` |
| `POST /api/news/{id}/hide` · `/unhide` | 숨기기·되돌리기 |
| `GET /api/news/sources` | 출처 목록 |
| `POST /api/news/sources` | `{name, feed_url}` 추가. 저장 전 한 번 읽어 피드인지 확인. 실패하면 422와 이유 |
| `PUT /api/news/sources/{id}` | `{enabled, expected_version}` 켜기·끄기 |
| `DELETE /api/news/sources/{id}` | 직접 추가한 출처만 삭제. 기본 출처는 409 |

모든 경로는 로그인과 소유자 확인을 거치고, 표본 모드는 422다. 오류 응답에는 기존처럼 `reason`과 한국어 `detail`을 담고 외부 주소를 에코하지 않는다.

### 자료로 저장

기존 `materials.service.create_material`로 만든다. URL에는 `link`, 제목에는 `title`, 본문에는 `summary`를 넣는다. 본문은 화면의 "본문·핵심 내용(원문에서 가져온 내용)" 칸이다. 설명·저장 이유는 비워 둔다. 같은 URL 자료가 있으면(기존 409) 새로 만들지 않고 그 자료 ID를 `saved_material_id`로 연결하며 `created: false`를 돌려준다. 저장한 자료는 받은 자료에 들어가 기존 분석·검토·승인 흐름을 탄다.

## 8. 화면

- **AI 동향:** 기존 세 칸(대응 필요·학습 자료·판단 보류) 위에 '새 소식' 칸을 둔다. 기존 세 칸은 바꾸지 않는다.
  - 머리줄: "새 소식 N건 · 마지막 확인 ○시간 전 · [지금 새로고침]". 수집 중이면 "새 소식을 확인하는 중…"을 보인다. 실패한 출처는 한 줄로 접어 보인다.
  - 카드: 제목(원문 링크, 새 탭), 출처와 공식·커뮤니티 표시, 상대 시각, 맞은 키워드 칩, 요약 두 줄, [자료로 저장] [숨기기].
  - 저장 뒤 "저장됨 · 받은 자료에서 보기", 숨긴 뒤 잠깐 "되돌리기"를 보인다. 30건 뒤에는 "더 보기"를 둔다.
- **프로젝트·설정:** '소식 출처' 칸에 목록과 켜기·끄기, 직접 추가한 출처의 삭제, 이름·주소 추가 폼을 둔다.
- **안전:** 외부 글은 모두 `textContent`로 넣는다. 링크는 화면에서도 http·https인지 다시 확인하고, `target="_blank"`와 `rel="noopener noreferrer"`를 붙인다.

## 9. 오류 처리

| 상황 | 동작 |
|---|---|
| 출처 하나 실패(시간 초과, 4xx·5xx, 429, 피드 아님, DOCTYPE, 파싱 오류) | 그 출처만 건너뛰고 오류 코드를 `sources`에 남김 |
| 전부 실패 | 기존 소식은 그대로, "새 소식을 확인하지 못했습니다" 표시. `last_success_at`은 바꾸지 않음 |
| 수집 중 서버 재시작 | `refreshing_until`이 지나면 다음 요청이 다시 수집 |
| 같은 URL 자료가 이미 있음 | 새 자료를 만들지 않고 연결 |

## 10. 테스트

- **서버(가짜 HTTP 전송, 외부 접속 없음):** RSS·Atom 파싱과 날짜 정렬, 출처당 20건, DOCTYPE 거부, 태그 제거·길이 제한, 위험 링크·제목 없는 글 건너뛰기, 같은 글 중복 방지와 숨김·저장 상태 보존, 6시간·5분·수집 중 기한 규칙과 동시 요청 한 번만 수집, 일부·전체 실패, 키워드 분리·영문 단어 경계·한글 부분 일치, 순서와 커서, 숨기기·되돌리기, 자료로 저장(새 자료·같은 URL·중복 요청), 30일·300건 정리와 저장 글 보존, 인증·표본 모드 422·소유자 격리, 출처 추가 검증·20곳 상한·기본 출처 삭제 거부.
- **웹:** 정렬 결과 표시·키워드 칩·링크 검사·상대 시각은 Node 테스트, 화면 동작은 가짜 API 시험 페이지에서 확인.
- **실제 확인:** 기본 출처 6곳을 한 번 실제로 수집해 출처별 건수와 오류를 `docs/verification.md`에 기록. Render 운영 서버의 외부 접속은 배포 후 확인.

## 11. 영향 받는 파일(예정)

- 생성: `server/app/features/news/`(`sources.py`, `feeds.py`, `service.py`, `routes.py`, `schemas.py`), `server/tests/test_news_*.py`, `web/js/news.js`, `web/scripts/news.test.mjs`
- 수정: `server/app/features/materials/fetcher.py`(피드용 형식 허용), `server/app/main.py`(라우터·오류), `firestore.indexes.json`(필요한 색인), `web/js/views/trends.js`, `web/js/views/settings.js`, `web/assets/app.css`, `docs/api-contract.md`, `docs/decisions.md`, `README.md`

## 구현 메모 (2026-10-04)

- **외부 접속:** 원격 `m1-2`에 같은 목적의 URL 미리보기(`url_preview.py`)가 먼저 들어와, 별도 `fetcher.py` 대신 그 `_request`(공개 IP 고정·리다이렉트 재검사·2MiB)를 쓴다. 피드 형식 확인은 `news/feeds.py`가 한다.
- **수집 조건(4장 보완):** 자동 수집은 "마지막 **성공** 6시간 경과 + 마지막 **시도** 5분 경과", 수동은 "마지막 시도 5분 경과". 전부 실패해도 다음에 화면을 열 때(5분 뒤) 다시 시도하고, 수집 중 서버가 꺼져도 표시 기한(3분)이 지나면 다시 수집된다.
- **직접 추가한 출처의 종류:** `kind`에 `custom`을 더했다(화면 표시 "직접 추가").
- **목록 커서:** 계산된 순서라 Firestore 커서 대신 위치 숫자(`cursor=30`)를 쓴다.
