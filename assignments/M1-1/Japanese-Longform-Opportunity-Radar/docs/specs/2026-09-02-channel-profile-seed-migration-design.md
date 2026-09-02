# 채널 프로필 + 검색어 재설계 — 설계 스펙

| | |
|---|---|
| 날짜 | 2026-09-02 |
| 대상 프로젝트 | `assignments/M1-1/Japanese-Longform-Opportunity-Radar/` |
| 근거 문서 | `assignments/M1-1/Claude_Code_전달용_Japanese_Longform_Radar_2채널_통합구현_최종지시서.md` (v3) §3~12, §61~65 |
| 범위 | "2채널 통합 구현" 8개 서브프로젝트 중 **#1 채널 프로필 기반**만. 나머지(랭킹 윈도우 버그 수정, Channel Fit, 댓글 파이프라인, Production Brief, Script Writer, UI 통합, automaker 계약)는 각자 별도 스펙으로 이후 진행 |
| 상태 | **구현·검증 완료 (2026-09-02).** 아래 본문은 설계 시점 기록이고, 검토 중 반영된 수정과 실제 검증 결과는 §12 참고 |

## 1. 배경

기존 프로젝트는 8~9개의 단일 명사 검색어(老後·お金·仕事·孤独·AI·人生・SNS・住宅・注文住宅)로 일본 롱폼 영상을 수집하는 1채널 MVP다. Phase 1~10이 이미 완료돼 있고 실데이터(videos.csv 401건 등)도 쌓여 있다.

최종지시서는 이 위에 "돈·노후"(Channel A)와 "집·상속"(Channel B) 두 채널 관점을 얹으라고 지시하는데, 그 전제조건이 채널 프로필 자체와 그 채널들이 실제로 다룰 문제를 가리키는 검색어다. 이번 스펙은 그 전제조건만 다룬다.

이 작업 중 검색어 전략 자체도 바뀌었다 — 단일 명사 검색어의 잡음 문제(지시서 §7 "단일 명사 검색 금지")를 이번 기회에 실제로 해소하기로 했다. 기존 9개는 삭제하지 않고 `legacy` 상태로 은퇴시키며, 새로 10개의 "대상+상황+문제" 형태 검색어를 채널별로 활성화한다.

## 2. 범위 밖 (Non-goals)

- Channel Fit 판정 로직, LLM 호출 — sub-project 3
- 댓글 수집·분석 — sub-project 4
- Production Brief, Script Writer — sub-project 5, 6
- `app.py` UI 변경(채널 필터, 검색어 관리 화면의 활성/레거시 배지 등) — sub-project 7. 이번 스펙은 **데이터·모듈 계층만** 다루고 화면은 건드리지 않는다
- `src/analysis.py`의 90일 랭킹 윈도우 버그 수정 — 별도 스펙(sub-project 2), 이번 변경과 무관

## 3. 현재 상태 (as-is)

- `data/raw/seeds.json` 실제 구조: `{"seeds": [{"term": str, "label": str}, ...], "ignored"?: [str, ...]}`. 지시서 §12가 가정한 "레거시는 문자열 배열"과 다르다 — 실제 레거시는 이미 `{term,label}` 객체 배열이다.
- `src/seeds.py` 공개 함수: `current() terms() labels() ignored() add() remove() ignore() unignore() performance() weakest() candidates()`.
- 호출부: `src/collector.py`는 `seeds.terms()`만 호출(무인자). `app.py` tab5는 `current() MAX_SEEDS performance() weakest() candidates() add() remove() ignore() unignore() ignored()`를 호출.
- `data/config/` 디렉터리, `src/channels.py`, `data/config/channels.json` 전부 존재하지 않음.
- `config.py`에는 `SEEDS`(기본값 폴백용 리스트)와 `SEED_LABELS`(그래프 라벨용 dict)가 있고, 둘 다 현재 9개 시드 기준.

## 4. `data/config/channels.json` + `src/channels.py`

지시서 §6 예시를 그대로 쓰고 `profile_version`만 추가한다(§65 대비 — Channel Fit 캐시 무효화가 이 필드를 나중에 씀).

```json
[
  {
    "id": "money_retirement",
    "name_ko": "돈·노후",
    "name_ja": "お金・老後",
    "audience": "50-69",
    "promise_ko": "50대 이후 돈과 노후에서 손해를 줄이는 선택",
    "core_question_ko": "이 선택이 50대 이후 내 돈과 현금흐름에 어떤 영향을 주는가?",
    "discovery_enabled": true,
    "production_enabled": true,
    "profile_version": 1,
    "lenses": ["cashflow", "loss_prevention", "pension", "tax", "insurance", "income"]
  },
  {
    "id": "housing_inheritance",
    "name_ko": "집·상속",
    "name_ja": "家・相続",
    "audience": "50-69",
    "promise_ko": "50대 이후 집과 상속에서 자산과 생활을 지키는 선택",
    "core_question_ko": "이 집을 보유·상속·처분하는 것이 내 자산과 생활에 어떤 영향을 주는가?",
    "discovery_enabled": true,
    "production_enabled": false,
    "profile_version": 1,
    "lenses": ["housing", "inheritance", "vacant_house", "maintenance", "disposal", "relocation"]
  }
]
```

`src/channels.py` 공개 함수:

```python
CHANNELS_JSON = config.ROOT / "data" / "config" / "channels.json"

def records() -> list[dict]:
    """전체 채널 프로필. 파일이 없거나 JSON이 깨졌으면 빈 리스트 — 예외를 던지지 않는다."""

def get(channel_id: str) -> dict | None:
    """단일 채널. 없으면 None."""

def enabled_for_discovery() -> list[dict]:
    """discovery_enabled=true 인 채널만."""

def enabled_for_production() -> list[dict]:
    """production_enabled=true 인 채널만."""
```

다른 모듈(향후 seeds/channel_fit/app)은 `channels.json`을 직접 열지 않고 이 네 함수만 쓴다 — storage.py 원칙(§63)과 동일한 이유.

## 5. `data/raw/seeds.json` 스키마 v2

레코드 필드: `term, label_ko, channels(list), pillar, intent, audience, active(bool), legacy(bool)`.

**기존 9개** → 삭제하지 않고 다음으로 전환:

```json
{"term": "老後", "label_ko": "노후", "channels": [], "pillar": "legacy",
 "intent": "", "audience": "50-69", "active": false, "legacy": true}
```
(老後·お金·仕事·孤独·AI・人生・SNS・住宅・注文住宅 9개 전부 동일 패턴, `label_ko`만 원래 `label` 값 승계)

**신규 활성 10개**:

| term | label_ko | channels | pillar | intent |
|---|---|---|---|---|
| 年金 繰下げ 損 | 연금 연기수령 손해 | money_retirement | pension | loss_prevention |
| 老後資金 足りない | 노후자금 부족 | money_retirement | retirement_savings | shortfall_anxiety |
| 定年後 お金 | 정년 후 돈 | money_retirement | money | general_concern |
| 定年後 住民税 | 정년 후 주민세 | money_retirement | tax | cost_pressure |
| 親の介護 費用 | 부모 간병 비용 | money_retirement | caregiving | cost_pressure |
| 50代 再就職 厳しい | 50대 재취업의 어려운 현실 | money_retirement | reemployment | income_risk |
| 50代 AI 仕事 | 50대 AI와 일자리 | money_retirement | ai_work | job_disruption |
| 老後 住まい 失敗 | 노후 주거 실패 | housing_inheritance | housing_retirement | regret_prevention |
| 実家 空き家 処分 | 본가·빈집 처분 | housing_inheritance | vacant_house | disposal_difficulty |
| マンション 老後 維持費 | 노후 맨션 유지비 | housing_inheritance | maintenance_cost | cost_pressure |

전부 `audience: "50-69", active: true, legacy: false`. `channels`가 리스트이므로 향후 `老後 持ち家 維持費`처럼 두 채널 다 태깅하는 교차 시드도 그대로 수용된다(지시서 §10).

파일 위치는 지금처럼 `data/raw/seeds.json` 그대로 유지한다(`data/config/`로 옮길 이유 없음). 최상위에 `schema_version` 키를 추가해 마이그레이션 중복 실행을 막는다.

## 6. `src/seeds.py` 변경

읽기 경로는 항상 **순수 함수**다 — 어떤 공개 함수를 불러도 파일에 쓰지 않는다. 필드가 없는 옛 레코드는 읽을 때 메모리에서만 기본값을 채운다(`active` 없으면 `True`로 간주 → 마이그레이션 전에도 지금과 동일하게 동작).

```python
def _normalize(d: dict) -> dict:
    return {
        "term": d.get("term", ""),
        "label_ko": d.get("label_ko") or d.get("label") or d.get("term", ""),
        "channels": d.get("channels") or [],
        "pillar": d.get("pillar", ""),
        "intent": d.get("intent", ""),
        "audience": d.get("audience", "50-69"),
        "active": d.get("active", True),
        "legacy": d.get("legacy", False),
    }

def records() -> list[dict]:
    """활성 + 레거시 전부. 정규화됨. 파일 없으면 config 기본 10개."""

def current() -> list[dict]:
    """records() 중 active=True. = 지금 실제로 검색에 쓰는 것 (기존 의미 그대로)."""

def terms(active_only: bool = True) -> list[str]:
    """active_only=True(기본): current()의 term. False: records() 전부의 term.
    collector.py의 기존 무인자 호출 seeds.terms()는 그대로 활성만 돌려받는다."""

def labels() -> dict[str, str]:
    """records() 전부(활성+레거시) 기준 term→label_ko.
    레거시로 내려도 과거 401건의 실적 조회(performance())가 화면에서 사라지면 안 되므로
    active 필터를 걸지 않는다."""

def get(term: str) -> dict | None:
    """records() 중 단일 term 조회."""

def terms_for_channel(channel_id: str) -> list[str]:
    """channels 리스트에 channel_id를 포함한 records()의 term."""
```

`add()` — 재활성화 지원:

```python
def add(term, label="", channels=None, pillar="", intent=""):
    """
    - term이 이미 active면 거부: "이미 쓰고 있습니다"
    - term이 inactive/legacy로 존재하면: 그 레코드를 active=True, legacy=False로
      갱신(label/channels/pillar/intent는 넘긴 값이 있으면 덮어쓰고 없으면 유지) →
      "다시 활성화했습니다" (신규 생성이 아니라 갱신 — 중복 레코드 방지)
    - term이 아예 없으면 신규 생성(active=True, legacy=False, audience="50-69")
    - 두 경우 모두 처리 후 활성 개수가 MAX_SEEDS(15) 초과면 거부
    """
```

`remove()` — 하드삭제 대신 비활성화:

```python
def remove(term):
    """
    - 활성 레코드가 1개뿐이면 거부(기존과 동일 가드, 판정 기준을 active 개수로 변경)
    - 그 외엔 삭제 대신 active=False (legacy 플래그는 건드리지 않음 —
      "사람이 방금 뺀 것"과 "원래 legacy였던 것"을 구분해서 남긴다)
    """
```

`candidates()` — 제외 집합 확장:

```python
def candidates(df, top=CANDIDATE_TOP):
    """
    변경점 한 줄: 제외 집합 `have`를 terms()(활성만) 대신
    {r["term"] for r in records()}(활성+레거시 전부)로 바꾼다.
    AI·人生・住宅처럼 outlier 제목에 여전히 자주 등장하는 옛 시드가
    "새 후보"로 재부상하는 것을 막는다.
    """
```

공유 내부 헬퍼(중복 로직 방지 — `add()`와 `migrate_v2()`가 함께 씀):

```python
def _upsert(records_list, term, **fields):
    """term으로 찾아 있으면 갱신, 없으면 append. (records_list, created, reactivated) 반환."""
```

`ignore()/unignore()/ignored()/performance()/weakest()`는 변경 없음(내부에서 쓰는 `labels()`/`terms()`의 결과 집합만 커질 뿐 로직은 그대로).

## 7. 마이그레이션 — 명시적 1회 실행

**절대 자동으로 실행되지 않는다.** `import seeds`든 `seeds.terms()` 호출이든, 파일을 쓰는 부수효과가 없다. 오직 아래 진입점만 파일을 바꾼다.

```python
def migrate_v2(apply: bool = False) -> dict:
    """
    - 이미 schema_version >= 2 면: {"already": True} 반환, 아무 것도 안 함(멱등)
    - apply=False(기본, 미리보기): 계획만 반환, 파일 미변경
        {"deactivate": [...9개 term...], "add_or_reactivate": [...10개 레코드...]}
    - apply=True(실제 반영):
        1) STORE 원본을 seeds.json.bak 으로 복사. 실패하면 예외를 올리고 아무 것도 쓰지 않는다
        2) 기존 9개를 label_ko로 정규화 + active=False, legacy=True, pillar="legacy"
        3) 신규 10개를 _upsert로 반영
        4) schema_version=2 기록 후 저장
        5) 적용 결과 리포트 반환
    """
```

CLI 진입점 `tools/migrate_seeds.py` (기존 `tools/backfill_titles.py`·`tools/setup_translate.py`와 같은 위치·같은 성격):

```bash
python tools/migrate_seeds.py            # 미리보기만 — 9개 비활성화 / 10개 활성화 계획 출력, 파일 미변경
python tools/migrate_seeds.py --apply    # 실제 반영 (백업 후 저장)
```

미리보기 출력에는 활성 시드 개수 변화에 따른 할당량 영향(10개 × 200 units = 2,000/일 = 20%)도 함께 보여준다.

## 8. 에러 처리 / 방어적 설계

- `channels.py`: `data/config/channels.json`이 없거나 JSON 파싱 실패 → 예외 없이 빈 리스트/`None`. (현재 `seeds.py`의 `_load()`가 깨진 JSON을 다루는 방식과 동일한 패턴)
- `seeds.py`: 마이그레이션 전 파일(옛 스키마)을 어떤 공개 함수로 읽어도 죽지 않아야 한다 — `_normalize()`가 누락 필드를 기본값으로 채우므로 마이그레이션을 영영 안 돌려도 지금과 똑같이 동작한다.
- `migrate_v2(apply=True)`: 백업 파일 쓰기가 실패하면(디스크 권한 등) 원본 파일은 절대 건드리지 않는다 — 백업 성공이 저장의 선행조건.
- `add()`/`migrate_v2()` 둘 다 `MAX_SEEDS` 상한을 활성 개수 기준으로 검사 — 레거시 9개는 상한 계산에서 제외.

## 9. 테스트 — `tests/test_seeds.py` (신규), API 호출 없이

- `_normalize()`: 필드 누락(구 스키마) 시 기본값 채움 / 필드 존재(신 스키마) 시 그대로 보존
- `current()`/`terms()`가 `active` 필터를 정확히 반영
- `labels()`가 비활성/레거시 term도 포함
- `add()`: 신규 term → 생성 / 이미 active인 term → 거부 / inactive·legacy term → 레코드 갱신(재활성화, 개수 불변) / MAX_SEEDS 경계(15개째 성공, 16개째 거부 — 레거시는 카운트에서 제외됨을 함께 확인)
- `remove()`: active=False 전환(레코드는 남음), 활성 1개 남았을 때 거부
- `candidates()`: 레거시/비활성 term은 `terms()`엔 없어도 후보에서 제외되는지
- `migrate_v2(apply=False)`: 파일 mtime/내용 불변, 계획 결과 형태 확인
- `migrate_v2(apply=True)`: 임시 디렉터리에 복사해서 실행 → `.bak` 생성 및 원본 내용 일치, 결과 19개 레코드(9 legacy + 10 active), `schema_version==2`; 재실행 시 아무 변화 없음(멱등, 20개로 안 늘어남)
- 모든 테스트는 `config.DATA_RAW`/`seeds.STORE`를 `tmp_path`로 바꿔치기해서 실제 `data/raw/seeds.json`을 절대 건드리지 않는다

`src/channels.py`도 같은 파일이나 `tests/test_channels.py`에: 정상 파일 파싱, 파일 없음, 깨진 JSON, `enabled_for_discovery`/`enabled_for_production` 필터링.

## 10. 회귀 확인

- `python -m src.collector --dry-run` — 시드 개수가 10개로 바뀌고 예상 비용이 2,000 units(20%)로 나오는지
- `app.py` 6개 탭 전부 예외 없이 렌더 — 특히 tab5(검색어 관리)는 19개 레코드가 활성/레거시 구분 없이 나열되는 과도기 상태(§11에서 인지된 상태, sub-project 7 전까지 유지)
- `videos.csv`/`video_snapshots.csv`/`channels.csv`/자막 캐시 — 행 수·내용 변화 없음

## 11. 열린 이슈 (다음 서브프로젝트로 이월)

- tab5의 **성과 목록**(performance())이 활성/레거시를 시각적으로 구분하지 않는 과도기 상태 — sub-project 7에서 상태 배지 추가. (단, "현재 검색어 (N/15)" 헤더는 `current()`를 쓰므로 지금도 활성 10개만 정확히 보인다 — §12-6 참고)
- `pillar`/`intent` 값은 1차 제안이라 sub-project 3(Channel Fit)이 실제로 이 값을 소비하기 시작하면 어휘를 재검토할 수 있음
- `注文住宅`·`老後` 등 레거시 시드는 신규 데이터 유입이 멈추지만 기존 401건의 seed 태그·이력은 영구 보존됨 — 의도된 동작

## 12. 검토 중 반영된 수정 + 실제 검증 결과 (2026-09-02)

스펙 승인 후 구현 직전에 사용자가 6가지를 추가로 지정했다. 반영 내용:

1. **할당량 표현** — "units/10,000" 대신 "Search Queries 호출 수/100회 = %"로 통일. `config.SEARCH_CALLS_DAILY_BUDGET = DAILY_QUOTA // SEARCH_COST`(=100)를 신설해 매직넘버 없이 계산하고, `collector.py`의 dry-run 출력과 `tools/migrate_seeds.py`의 미리보기 출력 둘 다 이 기준으로 바꿨다. (§4/§7 갱신 사항)
2. **`config.SEEDS`/`SEED_LABELS` 갱신** — `config.SEEDS`는 신규 활성 10개 term으로, `SEED_LABELS`는 기존 9개를 유지한 채 신규 10개를 추가했다. 신규 10개의 channels/pillar/intent는 `config.DEFAULT_SEED_META`에 두어 값의 원본이 config.py 한 곳(SEEDS·SEED_LABELS·DEFAULT_SEED_META)에만 있게 했다 — `seeds.py`의 `NEW_SEEDS_V2`는 이 셋을 조합만 한다.
3. **`performance()` vs `weakest()` 분리** — `performance()`는 여전히 active+legacy 전부(19개)를 보여주되 각 행에 `active`/`legacy` 필드를 추가했고, `weakest()`는 그중 `active=True`인 것만 최소값을 고르도록 필터를 추가했다.
4. **`terms_for_channel(channel_id, active_only=True)`** — 시그니처에 파라미터 추가.
5. **atomic write + 최상위 필드 보존** — `_atomic_write()`가 임시 파일에 쓰고 `json.loads`로 재검증한 뒤 `os.replace()`로 교체한다. `migrate_v2(apply=True)`는 백업(`shutil.copyfile`)이 끝난 뒤에만 쓰기를 시도하고, `new_data = dict(raw)`로 `ignored` 등 기존 최상위 필드를 그대로 들고 간다.
6. **UI 과도기 설명 정정** — "현재 검색어 (N/15)" 헤더는 `current()`(activeman)를 쓰므로 처음부터 정확히 10개만 보인다. 19개가 섞여 보이는 곳은 **성과 목록(performance()) 한 곳뿐**이고, ACTIVE/LEGACY 배지는 sub-project 7에서 추가한다.

### 실제 실행 검증 (2026-09-02, 실데이터 기준)

```
$ python tests/test_seeds.py / test_channels.py   → 전부 통과
$ python tests/test_basics.py                     → 기존에도 있던 무관한 실패 1건
                                                      ("키 없을 때 안내" — 로컬 .env에 실제
                                                      키가 있어 RuntimeError 전제가 성립하지
                                                      않음. config.py/youtube.py/seeds.py 중
                                                      이번에 건드린 파일이 없어 이번 변경과
                                                      무관 — 미해결로 남김)
$ python tests/test_watchlist.py                  → 전부 통과 (무관 모듈 회귀 없음 확인)

$ python tools/migrate_seeds.py            # 미리보기 — 파일 md5 불변 확인
$ python tools/migrate_seeds.py --apply    # 적용 — .bak md5 가 원본과 정확히 일치

seeds.terms()                → 신규 활성 10개와 정확히 일치 (set 비교 True)
seeds.terms(active_only=False) → 19개
seeds.weakest(seeds.performance(analysis.build()))
                              → None. 실제로 legacy "SNS"(n=27, outliers=0)가
                                필터 없으면 "빼기 후보"로 잘못 뽑혔을 항목이었음을
                                확인 — active 필터가 실제로 그 오탐을 막고 있다.
python -m src.collector --dry-run
                              → "검색(Search Queries) 20/100 = 20% · 약 2,000 units"

app.py 가 실제로 부르는 경로(seeds.current/performance/candidates,
channels.records/enabled_for_production)를 Streamlit 없이 재현 → 전부 정상.
videos.csv(401건)·video_snapshots.csv 등 원본 데이터는 무변경.
```

## 13. 커밋 범위 — git에는 메커니즘만, 값은 로컬에만 (2026-09-02, 사후 조정)

최초 커밋 뒤 "벤치마킹 가능하지 않도록 최소한만 제공"하라는 요청에 따라
git에 올라가는 것을 다시 정리했다. 실제 채널 정체성·구체적 검색어 전략은
**값**이지 **코드**가 아니므로, 코드(메커니즘)와 값(전략)을 분리해 값 쪽을
전부 로컬 전용으로 옮겼다.

**git에 남기는 것** — 스키마·읽기쓰기 로직뿐, 어떤 채널/시드가 실제로
쓰이는지는 드러나지 않는다.
```
src/channels.py                 — records/get/enabled_for_* (파일을 읽을 뿐, 값 없음)
src/seeds.py                    — _normalize/records/current/terms/labels/get/
                                   terms_for_channel/add/remove/performance/
                                   weakest/candidates/_atomic_write/_patch_record
src/config.py                   — SEEDS/SEED_LABELS 는 원래(2채널 작업 이전)의
                                   범용 단일 명사 8개로 되돌림. DEFAULT_SEED_META
                                   (채널별 pillar/intent 태그)는 완전히 제거
tests/test_seeds.py             — 합성 term(A1/A2/S0.../OLD/NEW 등)만 사용,
                                   fallback 테스트도 config.SEEDS 8개 기준으로 수정
tests/test_channels.py          — 실제 채널 id/이름 대신 channel_a/channel_b
                                   합성 데이터로 교체
```

**로컬에만 두는 것(.gitignore, 디스크에는 그대로 존재)**
```
data/config/                    — channels.json (채널 정체성 전부)
data/raw/seeds.json             — 실제 활성 10개 + 레거시 9개 (전략 전부)
data/raw/seeds.json.bak         — 마이그레이션 전 원본 백업
docs/specs/이 문서 자체          — git 커밋 대상에서 제외(로컬 참고용으로만 유지)
```

**제거한 것** — `tools/migrate_seeds.py`와 `seeds.py`의 `migrate_v2()`/
`_upsert()`/`NEW_SEEDS_V2`/`SCHEMA_VERSION`/`BACKUP`. 이 마이그레이션은
이미 로컬에서 1회 실행되어 `data/raw/seeds.json`에 결과가 영구히 남아 있고,
그 도구 자체가 신규 10개 시드 내용을 코드에 하드코딩하고 있었으므로
(§6 참고) 목적을 다한 뒤 코드에서 완전히 뺐다. `add()`/`remove()`(일상적으로
쓰는 쪽)는 특정 시드 내용을 전혀 담고 있지 않으므로 그대로 남겼다.

**실제 동작에는 영향 없음** — 위 변경은 전부 "파일이 아예 없을 때의 폴백
값"과 "git에 무엇을 커밋하는가"에만 관련된다. 로컬 `data/raw/seeds.json`·
`data/config/channels.json`은 이미 만들어져 있고 계속 그 값 그대로 쓰인다
(§12의 실제 실행 검증 결과는 이 조정 이후에도 동일하게 재확인됨:
`seeds.terms()` 10개, `terms(active_only=False)` 19개, dry-run 20/100=20%).
