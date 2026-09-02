# -*- coding: utf-8 -*-
"""검색어 목록과 후보.

검색어를 고정해 두면 **일주일쯤 뒤 같은 영상만 나온다.** 그렇다고
자동으로 늘리면 안 된다 — 제목에서 뽑은 말은 주제가 아니라 «형식» 이거나
채널명일 때가 많다. 「ゆっくり解説」 는 주제가 아니라 영상 형식이다.
그대로 넣으면 그 형식의 영상만 걸린다.

**프로그램은 후보만 내놓고 넣을지는 사람이 정한다.** (prd F-4)

검색어는 «바뀌는 값» 이라 코드가 아니라 데이터로 둔다. `config.py` 를 화면에서
고쳐 쓰면 쓰다 실패했을 때 프로그램이 아예 안 뜬다. 실제 운영 중인 검색어는
`data/raw/seeds.json`(로컬 데이터, git 대상 아님)에 있다.

레코드 필드: term · label_ko · channels(list) · pillar · intent · audience ·
active(bool) · legacy(bool). `channels`는 어느 채널 관점과 관련될 수 있는지에
대한 참고 태그일 뿐 — 실제 채널 적합도 판단은 이 태그가 아니라 영상 단위
평가(Channel Fit, 별도 모듈)가 한다. 한 시드가 여러 채널에 걸칠 수도, 아예
어느 채널에도 안 걸릴 수도 있다.

읽기(records/current/terms/labels/get/terms_for_channel)는 항상 **순수 함수**다
— 어떤 공개 함수를 불러도 파일에 쓰지 않는다. 쓰기는 add()/remove()/ignore()/
unignore() 뿐이고, 전부 대상 레코드 하나만 갱신한다 — 다른 레코드의 저장
형태는 건드리지 않는다.
"""
import json
import os
import re
from collections import Counter

from . import config

STORE = config.DATA_RAW / "seeds.json"

MAX_SEEDS = 15            # prd F-4. 검색어 1개 = 검색 2회 = 200 units
OUTLIER_RATIO = 5.0       # 구독자 대비 몇 배부터 «잘 된 영상» 으로 볼 것인가
MIN_APPEARANCES = 2       # 이만큼 나온 말만 후보
CANDIDATE_TOP = 12

# 후보에서 뺄 말. 주제가 아니라 형식·수식어라 검색어로 쓰면 그것만 걸린다.
NOISE = {
    "解説", "ゆっくり", "ゆっくり解説", "総集編", "作業用", "睡眠用",
    "朗読", "実話", "感動", "衝撃", "閲覧注意", "完全版", "保存版",
    "最新", "速報", "公式", "配信", "切り抜き", "まとめ", "前編", "後編",
    "第一話", "第一章", "アニメ", "漫画", "動画", "チャンネル", "登録",
    # 뜻이 너무 넓어 검색어로 쓰면 아무거나 걸리는 말
    "本当", "理由", "絶対", "必要", "場合", "自分", "最後", "今回",
    "結果", "状態", "以上", "以下", "全部", "普通", "問題",
}


# ──────────────────────────────────────────────────────────────────
# 읽기 — 항상 순수 함수. 파일에 쓰지 않는다.
# ──────────────────────────────────────────────────────────────────

def _load():
    if STORE.exists():
        try:
            d = json.loads(STORE.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
        except Exception:
            pass          # 깨졌으면 기본값으로. 검색어 때문에 멈추지 않는다.
    return {}


def _normalize(d):
    """옛 스키마(term+label만)도 새 스키마도 같은 모양으로 읽는다.

    필드가 없으면 지금까지와 동일하게 동작하도록 기본값을 채운다 — 특히
    `active` 가 없으면 True 로 본다(지금까지 모든 시드가 그래 왔던 것과
    같다). 이 함수는 메모리에서만 채울 뿐 디스크에 쓰지 않는다.
    """
    return {
        "term": d.get("term", ""),
        "label_ko": d.get("label_ko") or d.get("label") or d.get("term", ""),
        "channels": list(d.get("channels") or []),
        "pillar": d.get("pillar", ""),
        "intent": d.get("intent", ""),
        "audience": d.get("audience", "50-69"),
        "active": d.get("active", True),
        "legacy": d.get("legacy", False),
    }


def records():
    """활성 + 레거시 전부. 정규화됨.

    seeds.json 이 없거나 "seeds" 가 비어 있으면(신규 설치) config.SEEDS 를
    기본값으로 쓴다 — config.SEEDS 는 파일이 없을 때만 쓰이는 값이라는
    원래 설계 그대로다.
    """
    raw = _load().get("seeds")
    if raw:
        out = [_normalize(d) for d in raw if d.get("term")]
        if out:
            return out
    return [_normalize({"term": s, "label_ko": config.SEED_LABELS.get(s, s)})
            for s in config.SEEDS]


def current():
    """지금 실제로 검색에 쓰는 것 = active 인 것만."""
    return [r for r in records() if r["active"]]


def terms(active_only=True):
    """active_only=True(기본): current() 의 term. False: records() 전부의 term.

    collector.py 의 기존 무인자 호출 seeds.terms() 는 그대로 활성 term 만
    돌려받는다.
    """
    return [r["term"] for r in (current() if active_only else records())]


def labels():
    """records() 전부(활성+레거시) 기준 term→label_ko.

    레거시로 내려도 과거에 그 검색어로 모은 영상의 실적 조회(performance())가
    화면에서 사라지면 안 되므로 active 필터를 걸지 않는다.
    """
    return {r["term"]: r["label_ko"] for r in records()}


def get(term):
    """records() 중 단일 term 조회. 없으면 None."""
    return next((r for r in records() if r["term"] == term), None)


def terms_for_channel(channel_id, active_only=True):
    """channels 리스트에 channel_id 를 포함한 시드의 term.

    active_only=True(기본): 지금 실제로 검색 중인 것만.
    """
    pool = current() if active_only else records()
    return [r["term"] for r in pool if channel_id in (r.get("channels") or [])]


def ignored():
    return set(_load().get("ignored") or [])


# ──────────────────────────────────────────────────────────────────
# 쓰기 — atomic write. 대상 레코드 하나만 갱신하고 나머지는 그대로 둔다.
# ──────────────────────────────────────────────────────────────────

def _atomic_write(data):
    """임시 파일에 쓰고 검증한 뒤 os.replace 로 교체한다.

    쓰는 도중 죽거나 디스크가 꽉 차도 seeds.json 자체는 항상 이전 내용이거나
    새 내용이지, 반쯤 쓰인 상태가 되지 않는다.
    """
    STORE.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    json.loads(text)                     # 저장 전 검증 — 깨진 내용을 안 남긴다
    tmp = STORE.with_name(STORE.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, STORE)


def _patch_record(term, fields):
    """term 레코드 하나만 정규화해서 갱신(없으면 신설)하고 저장한다.

    다른 레코드는 저장돼 있던 형태 그대로 둔다.
    """
    raw = _load()
    seeds_raw = list(raw.get("seeds") or [])
    idx = next((i for i, d in enumerate(seeds_raw) if d.get("term") == term), None)
    if idx is None:
        seeds_raw.append(_normalize({"term": term, **fields}))
    else:
        seeds_raw[idx] = {**_normalize(seeds_raw[idx]), **fields, "term": term}
    raw["seeds"] = seeds_raw
    _atomic_write(raw)


def ignore(term):
    """다시 제안하지 않는다."""
    d = _load()
    d["ignored"] = sorted(set(d.get("ignored") or []) | {term})
    _atomic_write(d)
    return True, f"「{term}」 는 다시 제안하지 않습니다."


def unignore(term):
    d = _load()
    d["ignored"] = [x for x in (d.get("ignored") or []) if x != term]
    _atomic_write(d)
    return True, f"「{term}」 를 무시 목록에서 뺐습니다."


def add(term, label="", channels=None, pillar="", intent=""):
    """검색어를 넣는다. (성공여부, 할 말)

    이미 active 면 거부한다. inactive/legacy 로 이미 존재하면 새로 만들지
    않고 그 레코드를 active=True 로 갱신·재활성화한다(넘긴 label/channels/
    pillar/intent 가 있으면 덮어쓰고, 없으면 기존 값을 유지) — 같은 term 이
    중복 레코드로 남지 않는다.
    """
    term = (term or "").strip()
    if not term:
        return False, "검색어가 비었습니다."
    recs = records()
    hit = next((r for r in recs if r["term"] == term), None)
    if hit and hit["active"]:
        return False, f"「{term}」 는 이미 쓰고 있습니다."
    active_n = sum(1 for r in recs if r["active"])
    if active_n >= MAX_SEEDS:
        return False, (f"검색어는 {MAX_SEEDS}개까지입니다. "
                       "성과가 낮은 것을 먼저 빼세요.")
    fields = {"active": True, "legacy": False}
    if label:
        fields["label_ko"] = label
    if channels is not None:
        fields["channels"] = channels
    if pillar:
        fields["pillar"] = pillar
    if intent:
        fields["intent"] = intent
    _patch_record(term, fields)
    if hit:
        return True, f"「{term}」를 다시 활성화했습니다."
    return True, f"「{term}」 추가. 다음 수집부터 쓰입니다."


def remove(term):
    """검색어를 뺀다. 하드삭제가 아니라 active=False 전환 — 이력을 보존한다.

    legacy 플래그는 건드리지 않는다: "방금 사람이 뺀 것"과 "원래부터
    legacy였던 것"을 구분해서 남긴다.
    """
    recs = records()
    hit = next((r for r in recs if r["term"] == term), None)
    if not hit:
        return False, f"「{term}」 를 찾을 수 없습니다."
    if not hit["active"]:
        return False, f"「{term}」 는 이미 비활성 상태입니다."
    if sum(1 for r in recs if r["active"]) <= 1:
        return False, "검색어가 하나뿐이라 뺄 수 없습니다."
    _patch_record(term, {"active": False})
    return True, f"「{term}」 뺐습니다."


def performance(df):
    """검색어별 성과. 어느 것을 뺄지 정하는 근거다.

    active + legacy 전부를 대상으로 한다 — legacy 로 내려도 과거에 그
    검색어로 모은 영상의 실적은 화면에서 계속 보여야 한다. `active`/`legacy`
    필드를 함께 내보내므로, 호출부(예: weakest())가 active 인 것만 골라
    쓸 수 있다.

    **이상치 수로 줄 세운다. 중앙 점수가 아니다.**
    우리가 찾는 것은 «구독자에 비해 유난히 잘 된 영상» 이지 «평균이 높은
    주제» 가 아니다. 편차가 큰 주제가 오히려 사냥터로 좋다. 중앙값으로 줄
    세워 이것을 빼면 가장 잘 잡아내는 검색어를 버리게 된다.

    영상 수가 적으면 둘 다 우연이다. 그래서 건수를 함께 낸다.
    """
    if df.empty or "seed" not in df:
        return []
    out = []
    for r in records():
        term = r["term"]
        g = df[df["seed"] == term]
        out.append({
            "term": term, "label": r["label_ko"],
            "active": r["active"], "legacy": r["legacy"],
            "n": len(g),
            "median_score": float(g["video_score"].median()) if len(g) else None,
            "outliers": int((g["subscriber_view_ratio"] >= OUTLIER_RATIO).sum())
            if len(g) else 0,
        })
    return sorted(out, key=lambda d: (-d["outliers"], -(d["median_score"] or 0)))


def weakest(perf):
    """뺄 만한 검색어 — **active 인 것 중에서만** 고른다.

    이미 legacy/inactive 인 검색어를 "빼는 게 좋겠다"고 다시 추천하면 안
    된다 — 이미 뺀 것이다. 영상이 적으면 «아직 모르는 것» 이지 «성과가
    없는 것» 이 아니다.
    """
    weak = [p for p in perf
            if p.get("active") and p["outliers"] == 0 and p["n"] >= 15]
    return min(weak, key=lambda p: p["median_score"] or 0) if weak else None


def _chunks(title):
    """제목에서 후보가 될 만한 덩어리."""
    out = []
    # 【…】「…」［…］ 안쪽은 대개 형식 표시지만 주제일 때도 있다. 사람이 거른다.
    for m in re.findall(r"[【「\[［]([^】」\]］]{2,12})[】」\]］]", title):
        out.append(m.strip())
    # 한자 2자 이상 / 가타카나 3자 이상 덩어리
    body = re.sub(r"[【「\[［][^】」\]］]*[】」\]］]", " ", title)
    out += re.findall(r"[一-鿿]{2,6}", body)
    # 「・」(U+30FB) 는 가타카나 범위 안에 있지만 말이 아니라 구분점이다.
    # 빼지 않으면 「・シャドウ・」 같은 조각이 후보로 올라온다.
    for run in re.findall(r"[゠-ヿー]{3,}", body):
        out += [w for w in run.split("・") if len(w) >= 3]
    return out


def candidates(df, top=CANDIDATE_TOP):
    """잘 된 영상 제목에서 되풀이되는 말을 뽑는다.

    구독자 대비 5배 넘게 본 영상만 본다 — 평범한 영상 제목에서 뽑으면
    그냥 «흔한 말» 이 나온다. 잘 된 영상에 몰려 있는 말이라야 뜻이 있다.

    제외 대상은 **active + legacy 전부**(records() 전체)다. 한 번이라도
    다뤘던 검색어가 legacy 로 내려갔다고 "새 후보"로 재부상하면 안 된다.
    """
    if df.empty:
        return []
    hot = df[df["subscriber_view_ratio"] >= OUTLIER_RATIO]
    if hot.empty:
        return []

    have = {r["term"] for r in records()}
    skip = ignored()
    seen = Counter()
    where = {}
    for _, r in hot.iterrows():
        title = str(r.get("title") or "")
        for w in set(_chunks(title)):          # 한 영상에서 한 번만 센다
            if w in NOISE or w in have or w in skip or len(w) < 2:
                continue
            seen[w] += 1
            where.setdefault(w, []).append(title)

    return [{"term": w, "count": n, "titles": where[w][:3]}
            for w, n in seen.most_common(top * 3)
            if n >= MIN_APPEARANCES][:top]
