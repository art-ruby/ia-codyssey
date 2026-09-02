# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.getcwd())

from src import language
from src.youtube import parse_duration

fails = []
def check(name, got, want):
    ok = got == want
    if not ok: fails.append(f"{name}: {got!r} != {want!r}")
    print(f"  {'O' if ok else 'X'}  {name:<44} {got}")

print("=== 일본어 판정 ===")
# 실제 일본 롱폼 제목 형태
t1 = "老後2000万円問題は本当だったのか｜年金の現実"
check("일본어 제목", language.detect(t1)[0], "ja")

# 한국어 — 가나가 없으니 걸러져야 한다
check("한국어 제목", language.detect("노후 2000만원 문제는 사실이었나")[0], "other")

# 영어
check("영어 제목", language.detect("Why retirement anxiety is rising")[0], "other")

# 한자만 (중국어와 구별 안 됨) → 가나 없으면 other
check("한자만", language.detect("退職金運用戦略")[0], "other")

# default_audio_language 가 있으면 그것을 믿는다
check("dal=ja 우선", language.detect("Retirement", "", "ja")[0], "ja")
check("dal=ko 우선", language.detect("老後の不安", "", "ko-KR")[0], "ko")

# 비율
r = language.kana_ratio("老後のお金がなくなる")
print(f"     가나 비율 예시: {r:.2f}")

print("\n=== 길이 파싱 ===")
check("PT23M12S", parse_duration("PT23M12S"), 1392)
check("PT1H2M3S", parse_duration("PT1H2M3S"), 3723)
check("PT58S (숏폼)", parse_duration("PT58S"), 58)
check("빈 값", parse_duration(""), 0)
check("이상한 값", parse_duration("나쁜값"), 0)

print("\n=== 롱폼 기준 (600초) ===")
from src import config
for iso, expect in [("PT9M59S", False), ("PT10M0S", True), ("PT45M", True)]:
    s = parse_duration(iso)
    check(f"{iso} → {s}초", s >= config.LONGFORM_MIN_SECONDS, expect)

print("\n=== 키 없을 때 안내 ===")
os.environ.pop("YOUTUBE_API_KEY", None)
from src.youtube import Client
try:
    Client(key="")
    fails.append("키 없는데 예외가 안 났다")
except RuntimeError as e:
    msg = str(e)
    check("안내에 .env 언급", ".env" in msg, True)
    check("안내에 발급처 언급", "Cloud Console" in msg, True)

print()
if fails:
    print(f"실패 {len(fails)}건")
    for f in fails: print("   ", f)
    sys.exit(1)
print("전부 통과")
