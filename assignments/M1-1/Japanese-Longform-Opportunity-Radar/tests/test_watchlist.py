# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.getcwd())
from datetime import datetime, timedelta, timezone
from src import config, snapshot_collector as sc

fails = []
def check(name, got, want):
    ok = got == want
    if not ok: fails.append(f"{name}: {got!r} != {want!r}")
    print(f"  {'O' if ok else 'X'}  {name:<46} {got}")

now = datetime.now(timezone.utc)
def ago(days): return (now - timedelta(days=days)).isoformat()

print("=== 졸업 조건 ===")
videos = [
    {"video_id": "fresh", "published_at": ago(5),  "found_at": ago(1)},
    {"video_id": "old",   "published_at": ago(70), "found_at": ago(1)},   # 60일 초과
    {"video_id": "flat",  "published_at": ago(20), "found_at": ago(9)},   # 증가 없음
    {"video_id": "new2",  "published_at": ago(3),  "found_at": ago(2)},   # 관측 2회뿐
]
history = {
    # 7회 관측 · 조회수 변화 없음 → 졸업
    "flat": [{"collected_at": ago(7-i), "views": "5000"} for i in range(7)],
    # 관측 2회뿐 → 아직 판정하지 않는다 (막 등록한 영상이 바로 졸업하면 안 된다)
    "new2": [{"collected_at": ago(2), "views": "100"},
             {"collected_at": ago(1), "views": "100"}],
}
active, dropped = sc.build_watchlist(videos, history)
ids = {v["video_id"] for v in active}
drop = {v: r for v, r in dropped}
check("최근 영상 유지",        "fresh" in ids, True)
check("60일 초과 졸업",        drop.get("old"), "60일 초과")
check("7회 관측 + 정체 졸업",   drop.get("flat"), "증가 없음")
check("관측 2회는 판정 보류",   "new2" in ids, True)

print("\n=== 상한 초과 ===")
many = [{"video_id": f"v{i}", "published_at": ago(5), "found_at": ago(i)}
        for i in range(config.WATCHLIST_MAX + 20)]
a2, d2 = sc.build_watchlist(many, {})
check("상한만큼만 남김", len(a2), config.WATCHLIST_MAX)
check("초과분은 제외",   len(d2), 20)
check("최근 발견을 남김", a2[0]["video_id"], "v0")

print("\n=== Gain — 하루를 빠뜨렸을 때 (핵심) ===")
# 직전 관측이 2일 전. 그 사이 조회수가 20,000 늘었다.
# «전날 대비» 로 계산하면 20,000/일 로 2배 부풀려진다.
hist = {"x": [{"collected_at": (now - timedelta(days=2)).isoformat(),
               "views": "10000"}]}
rows = [{"collected_at": now.isoformat(), "video_id": "x",
         "views": "30000", "watch_status": "active"}]
g = sc.report_gain(hist, rows)
vid, per_day, days = g[0]
check("경과 일수를 2일로 잡음", round(days), 2)
check("하루치로 나눔 (10,000)", round(per_day), 10000)
print("       → 나누지 않았다면 20,000/일 로 2배 부풀 뻔했다")

print("\n=== 첫 관측은 Gain 없음 ===")
g2 = sc.report_gain({}, [{"collected_at": now.isoformat(), "video_id": "y",
                          "views": "500", "watch_status": "active"}])
check("직전 값 없으면 제외", len(g2), 0)

print("\n=== unavailable 은 Gain 계산 제외 ===")
g3 = sc.report_gain(hist, [{"collected_at": now.isoformat(), "video_id": "x",
                            "views": "", "watch_status": "unavailable"}])
check("삭제 영상 제외", len(g3), 0)

print()
if fails:
    print(f"실패 {len(fails)}건")
    for f in fails: print("   ", f)
    sys.exit(1)
print("전부 통과")
