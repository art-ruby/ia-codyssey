# -*- coding: utf-8 -*-
"""src/channels.py — 파일 없음/깨진 JSON/정상 파일 검증.

실제 data/config/channels.json 을 건드리지 않는다 — channels.CHANNELS_JSON 을
임시 경로로 바꿔치기한다.
"""
import sys, io, os, json, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.getcwd())

from pathlib import Path
from src import channels

fails = []
def check(name, got, want):
    ok = got == want
    if not ok: fails.append(f"{name}: {got!r} != {want!r}")
    print(f"  {'O' if ok else 'X'}  {name:<48} {got}")

tmpdir = tempfile.TemporaryDirectory()
channels.CHANNELS_JSON = Path(tmpdir.name) / "channels.json"

print("=== 파일 없음 ===")
check("records() 빈 리스트", channels.records(), [])
check("get() None", channels.get("channel_a"), None)
check("enabled_for_discovery() 빈 리스트", channels.enabled_for_discovery(), [])
check("enabled_for_production() 빈 리스트", channels.enabled_for_production(), [])

print("\n=== 깨진 JSON ===")
channels.CHANNELS_JSON.write_text("{이것은 JSON이 아니다", encoding="utf-8")
check("깨진 JSON도 예외 없이 빈 리스트", channels.records(), [])

print("\n=== 정상 파일(합성 데이터) ===")
channels.CHANNELS_JSON.write_text(json.dumps([
    {"id": "channel_a", "name_ko": "테스트 채널 A",
     "discovery_enabled": True, "production_enabled": True},
    {"id": "channel_b", "name_ko": "테스트 채널 B",
     "discovery_enabled": True, "production_enabled": False},
], ensure_ascii=False), encoding="utf-8")

check("records() 2개", len(channels.records()), 2)
check("get() 로 조회", channels.get("channel_b")["name_ko"], "테스트 채널 B")
check("get() 없는 id는 None", channels.get("nope"), None)
check("discovery_enabled 은 둘 다",
      sorted(c["id"] for c in channels.enabled_for_discovery()),
      ["channel_a", "channel_b"])
check("production_enabled 은 A만",
      [c["id"] for c in channels.enabled_for_production()],
      ["channel_a"])

tmpdir.cleanup()

print()
if fails:
    print(f"실패 {len(fails)}건")
    for f in fails: print("   ", f)
    sys.exit(1)
print("전부 통과")
