# -*- coding: utf-8 -*-
"""1단계 수집 — 검색해서 일본 롱폼 영상을 찾아 videos.csv 에 넣는다.

    python -m src.collector
    python -m src.collector --dry-run     API 를 부르지 않고 계획만 본다

첫 실행 뒤 아래 숫자를 보고 설정을 조정한다 (v5 §12).
문서로 미리 정하지 않는다 — 실측이 나와야 정할 수 있다.

    롱폼 확보율 · 일본어 통과율 · Seed 별 데이터 수
"""
import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

if __package__ in (None, ""):
    sys.exit("python -m src.collector 로 실행하세요")

from . import config, language, seeds, storage, translate
from .youtube import Client, QuotaError, parse_duration


def _utf8():
    """윈도우 콘솔이 cp949 라 한글·일본어에서 죽는다."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def plan():
    """이번 실행이 검색을 몇 번 하고 얼마를 쓰는지."""
    n = len(seeds.terms()) * len(config.SEARCH_ORDERS) * config.MAX_PAGES_PER_QUERY
    return n, n * config.SEARCH_COST


def collect(client, verbose=True):
    since = (datetime.now(timezone.utc) - timedelta(days=config.SEARCH_DAYS)
             ).strftime("%Y-%m-%dT%H:%M:%SZ")

    found = {}          # video_id -> seed (처음 발견한 검색어)
    for seed in seeds.terms():
        for order in config.SEARCH_ORDERS:
            token, pages = None, 0
            while pages < config.MAX_PAGES_PER_QUERY:
                data = client.search(seed, order=order, published_after=since,
                                     video_duration=config.VIDEO_DURATION,
                                     page_token=token)
                for item in data.get("items", []):
                    vid = (item.get("id") or {}).get("videoId")
                    if vid:
                        found.setdefault(vid, seed)
                token = data.get("nextPageToken")
                pages += 1
                if not token:
                    break
        if verbose:
            print(f"  검색 {seed:<6} 누적 후보 {len(found)}건")

    if not found:
        return [], Counter()

    # 검색 결과에는 길이·통계가 없다. videos.list 로 채운다 (50개당 1 unit).
    details = client.videos(found.keys())

    now = datetime.now(timezone.utc).isoformat()
    rows, stat = [], Counter()
    stat["검색으로 찾음"] = len(found)
    stat["상세 조회됨"] = len(details)

    for vid, item in details.items():
        snip = item.get("snippet", {})
        secs = parse_duration(item.get("contentDetails", {}).get("duration"))

        if secs < config.LONGFORM_MIN_SECONDS:
            stat["짧아서 제외"] += 1
            continue
        stat["롱폼"] += 1

        title = snip.get("title", "")
        desc = snip.get("description", "")
        lang, ratio, _ = language.detect(
            title, desc, snip.get("defaultAudioLanguage", ""),
            min_ratio=config.JAPANESE_MIN_RATIO)

        if lang != "ja":
            stat["일본어 아님"] += 1
            continue
        stat["통과"] += 1

        rows.append({
            "video_id": vid,
            "title": title,
            "title_ko": "",          # 아래에서 한 번에 채운다
            "description": desc[:500],
            "channel_id": snip.get("channelId", ""),
            "channel_name": snip.get("channelTitle", ""),
            "published_at": snip.get("publishedAt", ""),
            "duration_seconds": secs,
            "default_audio_language": snip.get("defaultAudioLanguage", ""),
            "detected_language": lang,
            "kana_ratio": round(ratio, 3),
            "seed": found.get(vid, ""),
            "found_at": now,
        })

    # 제목을 한글로 옮긴다. 새로 저장할 것만, 한 번에 묶어서.
    #
    # 이미 있는 영상은 다시 번역하지 않는다 — 제목은 변하지 않는데
    # 매일 327건을 다시 보내면 월 한도가 그냥 닳는다.
    #
    # 번역은 편의 기능이다. 실패해도 원문으로 그대로 저장한다.
    fresh = [r for r in rows if r["video_id"] not in storage.known_video_ids()]
    if fresh:
        ok, why = translate.available()
        if not ok:
            if verbose:
                print(f"\n  제목 번역 건너뜀 — {why}")
        else:
            if verbose:
                print(f"\n  제목 번역 {len(fresh)}건…")
            # 검색은 이미 끝났고 그 값이 비싸다(검색어 12개면 2,400 units).
            # 번역이 어떤 이유로 죽든 **모은 것을 잃지 않는다.**
            # 실제로 읽기 타임아웃 하나 때문에 2,400 units 를 날린 적이 있다.
            try:
                for r, ko in zip(fresh, translate.translate_titles(
                        [r["title"] for r in fresh])):
                    r["title_ko"] = ko
            except Exception as e:               # noqa: BLE001
                if verbose:
                    print(f"  번역이 실패했습니다 ({type(e).__name__}) — "
                          "원문 그대로 저장합니다.")
            done = sum(1 for r in fresh if r["title_ko"])
            if verbose:
                print(f"  번역됨 {done}/{len(fresh)}건")
                if done < len(fresh) and translate.last_error:
                    print(f"  {translate.last_error.splitlines()[0]}")
                if done < len(fresh):
                    print("  빠진 것은 `python tools/backfill_titles.py` 로 채웁니다.")
    return rows, stat


def main():
    _utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="API 를 부르지 않고 계획만 본다")
    ap.add_argument("--force", action="store_true",
                    help="오늘 이미 수집했어도 한 번 더 돌린다")
    args = ap.parse_args()

    calls, units = plan()
    budget = config.SEARCH_CALLS_DAILY_BUDGET
    pct = calls / budget * 100 if budget else 0.0
    print(f"Seed {len(seeds.terms())}개 × order {len(config.SEARCH_ORDERS)}종 "
          f"× {config.MAX_PAGES_PER_QUERY}페이지")
    print(f"  검색(Search Queries) {calls}/{budget} = {pct:.0f}% "
          f"· 약 {units:,} units (하루 상한 {config.DAILY_QUOTA:,})")
    if calls > config.SEARCH_WARN_AT:
        print(f"  ⚠ 검색 {calls}회는 하루 상한에 가깝습니다. Seed 를 줄이세요.")
    if args.dry_run:
        print("\n--dry-run 이라 여기서 멈춥니다.")
        return 0

    # 수집은 하루 한 번이면 된다. 검색 결과는 몇 시간 만에 크게 바뀌지 않는데
    # 한 번이 1,600 units 이라 여섯 번이면 하루치가 사라진다. 그날은 스냅샷도
    # 못 남긴다 — 시계열에 구멍이 나고 그 구멍은 나중에 메울 수 없다.
    spent = Client.spent_today()
    mine = Client.spent_today("collector")
    if mine and not args.force:
        print(f"\n오늘 이미 수집했습니다 ({mine:,} units).")
        print("검색 결과는 몇 시간 만에 크게 바뀌지 않아 다시 돌릴 필요가 거의 없습니다.")
        print("\n  조회수만 새로 받기 (약 12 units)")
        print("    python -m src.snapshot_collector")
        print("\n  그래도 다시 수집하기")
        print("    python -m src.collector --force")
        return 0
    if spent + units > config.DAILY_QUOTA:
        print(f"\n오늘 이미 {spent:,} units 를 썼습니다. {units:,} 를 더 쓰면 상한 "
              f"{config.DAILY_QUOTA:,} 를 넘어\n남은 하루 동안 아무것도 못 받습니다. "
              "내일 다시 돌리세요.")
        return 1

    try:
        client = Client()
    except RuntimeError as e:
        print(f"\n{e}")
        return 1

    print()
    try:
        rows, stat = collect(client)
    except QuotaError as e:
        print(f"\n{e}")
        client.log_quota("quota exceeded")
        return 1
    except Exception as e:                       # noqa: BLE001
        # 검색은 이미 돈을 썼다. 기록하지 않으면 «안 썼다» 로 남아
        # 다음 실행이 상한을 조용히 넘긴다.
        client.log_quota("collector (실패)")
        print(f"\n수집 도중 실패했습니다 — {type(e).__name__}: {e}")
        print(f"  쓴 양은 기록했습니다: {client.report()}")
        return 1

    added = storage.append_videos(rows)
    client.log_quota("collector")

    print()
    for k, v in stat.items():
        print(f"  {k:<14} {v:>5}")
    print(f"\n  새로 저장 {added}건 (이미 있던 것은 건너뜀)")
    print(f"  전체 videos.csv {len(storage.read_videos())}건")
    print(f"  {client.report()}")

    total = stat.get("상세 조회됨", 0)
    if total:
        print(f"\n  롱폼 확보율   {stat.get('롱폼', 0) / total * 100:5.1f}%")
        if stat.get("롱폼"):
            print(f"  일본어 통과율 {stat.get('통과', 0) / stat['롱폼'] * 100:5.1f}%"
                  "   (롱폼 중)")
        if stat.get("롱폼", 0) / total < 0.3:
            print("\n  ⚠ 롱폼이 30% 미만입니다. config.VIDEO_DURATION 을")
            print("    medium + long 으로 나눠 검색하는 편이 낫습니다. (v5 §12)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
