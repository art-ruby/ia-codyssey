# -*- coding: utf-8 -*-
"""src/seeds.py — 스키마(active/legacy)·add/remove/weakest/candidates 검증.

실제 data/raw/seeds.json 을 절대 건드리지 않는다 — seeds.STORE/BACKUP 을
임시 디렉터리로 바꿔치기한 뒤 그 안에서만 읽고 쓴다.
"""
import sys, io, os, json, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.getcwd())

from pathlib import Path
import pandas as pd
from src import config, seeds

fails = []
def check(name, got, want):
    ok = got == want
    if not ok: fails.append(f"{name}: {got!r} != {want!r}")
    print(f"  {'O' if ok else 'X'}  {name:<48} {got}")

tmpdir = tempfile.TemporaryDirectory()
seeds.STORE = Path(tmpdir.name) / "seeds.json"
seeds.BACKUP = Path(tmpdir.name) / "seeds.json.bak"


def reset(content=None):
    """STORE 를 주어진 내용으로 초기화(None 이면 파일 자체를 지운다)."""
    if seeds.STORE.exists():
        seeds.STORE.unlink()
    if seeds.BACKUP.exists():
        seeds.BACKUP.unlink()
    if content is not None:
        seeds.STORE.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")


print("=== _normalize — 필드 누락(구 스키마) 기본값 ===")
n = seeds._normalize({"term": "老後", "label": "노후"})
check("label→label_ko 승계", n["label_ko"], "노후")
check("active 없으면 True", n["active"], True)
check("legacy 없으면 False", n["legacy"], False)
check("channels 없으면 []", n["channels"], [])

print("\n=== _normalize — 신 스키마는 그대로 보존 ===")
n2 = seeds._normalize({"term": "住宅", "label_ko": "주택", "active": False,
                       "legacy": True, "channels": ["channel_b"]})
check("active 보존", n2["active"], False)
check("legacy 보존", n2["legacy"], True)
check("channels 보존", n2["channels"], ["channel_b"])

print("\n=== records() — 파일이 없으면 config.SEEDS 기본값 ===")
reset(None)
recs = seeds.records()
check("config.SEEDS 개수와 일치", len(recs), len(config.SEEDS))
check("전부 active", all(r["active"] for r in recs), True)
check("legacy 는 하나도 없음", any(r["legacy"] for r in recs), False)
check("라벨이 SEED_LABELS 에서 옴",
      seeds.get(config.SEEDS[0])["label_ko"],
      config.SEED_LABELS.get(config.SEEDS[0], config.SEEDS[0]))

print("\n=== current()/terms() — active 필터 ===")
reset({"seeds": [
    {"term": "老後", "label_ko": "노후", "active": False, "legacy": True},
    {"term": "AI",   "label_ko": "AI",   "active": True,  "legacy": False},
]})
check("current() 는 active만", [r["term"] for r in seeds.current()], ["AI"])
check("terms() 기본값도 active만", seeds.terms(), ["AI"])
check("terms(active_only=False) 는 전부",
      sorted(seeds.terms(active_only=False)), ["AI", "老後"])

print("\n=== labels() — legacy 포함 전부 ===")
check("老後 라벨도 조회됨(레거시 실적 표시용)", seeds.labels().get("老後"), "노후")

print("\n=== get()/terms_for_channel() ===")
reset({"seeds": [
    {"term": "A1", "label_ko": "a1", "active": True, "legacy": False,
     "channels": ["channel_a"]},
    {"term": "A2", "label_ko": "a2", "active": False, "legacy": False,
     "channels": ["channel_a"]},
    {"term": "B1", "label_ko": "b1", "active": True, "legacy": False,
     "channels": ["channel_b"]},
]})
check("get 존재", seeds.get("A1")["label_ko"], "a1")
check("get 없음", seeds.get("Z"), None)
check("terms_for_channel 기본(active만)",
      seeds.terms_for_channel("channel_a"), ["A1"])
check("terms_for_channel active_only=False",
      sorted(seeds.terms_for_channel("channel_a", active_only=False)),
      ["A1", "A2"])

print("\n=== add() — 신규 / 중복 / 재활성화 / 상한 ===")
reset({"seeds": [{"term": "OLD", "label_ko": "옛것", "active": False, "legacy": True}]})
ok, msg = seeds.add("NEW", "새것")
check("신규 추가 성공", ok, True)
check("신규 추가 메시지", "추가" in msg, True)
ok2, msg2 = seeds.add("NEW", "새것")
check("이미 active면 거부", ok2, False)
ok3, msg3 = seeds.add("OLD", "옛것-갱신")
check("legacy 재활성화 성공", ok3, True)
check("재활성화 메시지", "다시 활성화" in msg3, True)
recs2 = seeds.records()
check("재활성화는 레코드 수 불변(2개, 중복 생성 안 함)", len(recs2), 2)
check("OLD 가 active 로 바뀜", seeds.get("OLD")["active"], True)
check("OLD 라벨도 갱신됨", seeds.get("OLD")["label_ko"], "옛것-갱신")

reset({"seeds": [{"term": f"S{i}", "label_ko": str(i), "active": True,
                  "legacy": False} for i in range(seeds.MAX_SEEDS)]})
ok4, msg4 = seeds.add("OVER", "초과")
check("활성 상한 도달 시 거부", ok4, False)
check("상한 메시지", str(seeds.MAX_SEEDS) in msg4, True)

reset({"seeds": [{"term": f"S{i}", "label_ko": str(i), "active": False,
                  "legacy": True} for i in range(seeds.MAX_SEEDS)]})
ok5, _ = seeds.add("NEWACTIVE", "새로운거")
check("레거시가 많아도 활성 0개면 추가 가능(레거시는 상한 계산 제외)", ok5, True)

print("\n=== remove() — 하드삭제 대신 비활성화 ===")
reset({"seeds": [
    {"term": "X", "label_ko": "x", "active": True, "legacy": False},
    {"term": "Y", "label_ko": "y", "active": True, "legacy": False},
]})
ok6, msg6 = seeds.remove("X")
check("제거 성공 메시지", "뺐습니다" in msg6, True)
check("레코드는 삭제되지 않고 남아있음", seeds.get("X") is not None, True)
check("active만 False", seeds.get("X")["active"], False)
check("legacy는 건드리지 않음(False 그대로)", seeds.get("X")["legacy"], False)

reset({"seeds": [{"term": "ONLY", "label_ko": "only", "active": True, "legacy": False}]})
ok7, _ = seeds.remove("ONLY")
check("active 1개뿐이면 거부", ok7, False)

reset({"seeds": [{"term": "Z", "label_ko": "z", "active": False, "legacy": True}]})
ok8, _ = seeds.remove("Z")
check("이미 비활성이면 거부", ok8, False)

print("\n=== weakest() — active 인 것만 제거 후보로 추천 ===")
perf = [
    {"term": "L", "label": "레거시", "active": False, "legacy": True,
     "n": 20, "median_score": 10.0, "outliers": 0},
    {"term": "A", "label": "활성", "active": True, "legacy": False,
     "n": 20, "median_score": 30.0, "outliers": 0},
]
w = seeds.weakest(perf)
check("legacy는 추천 대상에서 제외되고 active(A)만 나옴",
      w["term"] if w else None, "A")

print("\n=== candidates() — active+legacy 전부 제외 ===")
df = pd.DataFrame([
    {"title": "老後の資金がヤバい件について", "subscriber_view_ratio": 10.0},
    {"title": "老後の生活費が足りない理由", "subscriber_view_ratio": 8.0},
])
reset({"seeds": [{"term": "老後", "label_ko": "노후", "active": False, "legacy": True}]})
cand_terms = {c["term"] for c in seeds.candidates(df)}
check("legacy 인 老後 는 후보로 재부상하지 않음", "老後" in cand_terms, False)

print("\n=== _atomic_write / _patch_record — 다른 최상위 필드 보존 ===")
reset({"seeds": [{"term": "X", "label_ko": "x", "active": True, "legacy": False}],
      "ignored": ["SNS"]})
seeds.add("Y", "y")
saved = json.loads(seeds.STORE.read_text(encoding="utf-8"))
check("ignored 필드는 add() 후에도 보존됨", saved.get("ignored"), ["SNS"])
check("건드리지 않은 레코드(X)는 그대로", seeds.get("X")["label_ko"], "x")

tmpdir.cleanup()

print()
if fails:
    print(f"실패 {len(fails)}건")
    for f in fails: print("   ", f)
    sys.exit(1)
print("전부 통과")
