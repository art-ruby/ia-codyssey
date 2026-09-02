# -*- coding: utf-8 -*-
"""아직 번역 안 된 제목을 채운다.

    python tools/backfill_titles.py            비어 있는 것만
    python tools/backfill_titles.py --limit 50 50건만 (시험용)

수집기는 새 영상만 번역한다. 번역을 나중에 붙였거나 잠시 꺼 뒀다면
그 사이 쌓인 것들이 비어 있다. 이 도구로 메운다.

이미 번역된 것은 건드리지 않는다 — 제목은 변하지 않는데 다시 보내면
월 한도만 닳는다.
"""
import argparse
import csv
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config, storage, translate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="몇 건만 (0=전부)")
    args = ap.parse_args()

    rows = storage.read_videos()
    if not rows:
        print("videos.csv 가 비어 있습니다.")
        return 1

    todo = [r for r in rows if not (r.get("title_ko") or "").strip()]
    print(f"전체 {len(rows)}건 · 번역 안 된 것 {len(todo)}건")
    if not todo:
        print("채울 것이 없습니다.")
        return 0

    ok, why = translate.available()
    if not ok:
        print(f"번역할 수 없습니다 — {why}")
        return 1

    if args.limit:
        todo = todo[:args.limit]
        print(f"이번에 {len(todo)}건만 처리합니다 (--limit)")

    print(f"{config.TRANSLATE_MODEL} 로 {config.TRANSLATE_BATCH}건씩 묶어 보냅니다…")
    got = translate.translate_titles([r["title"] for r in todo])

    filled = 0
    by_id = {r["video_id"]: r for r in rows}
    for r, ko in zip(todo, got):
        if ko:
            by_id[r["video_id"]]["title_ko"] = ko
            filled += 1

    if not filled:
        print(f"하나도 번역되지 않았습니다.\n  {translate.last_error}")
        return 1

    # 통째로 다시 쓴다. 열이 늘었을 수 있으므로 헤더도 새로 쓴다.
    with open(config.VIDEOS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=storage.VIDEO_FIELDS,
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    print(f"\n채움 {filled}/{len(todo)}건")
    if filled < len(todo) and translate.last_error:
        print(f"  일부 실패: {translate.last_error.splitlines()[0]}")

    print("\n예시")
    for r in [x for x in rows if x.get("title_ko")][:5]:
        print(f"  {r['title_ko'][:44]}")
        print(f"    {r['title'][:44]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
