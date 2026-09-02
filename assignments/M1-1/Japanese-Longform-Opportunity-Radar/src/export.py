# -*- coding: utf-8 -*-
"""고른 영상 하나를 «Claude 웹에 붙여넣을 한 장» 으로 만든다.

    from src import export
    print(export.one_pager("DD3gDj8cKGo"))

이 프로그램은 대본을 쓰지 않는다. **재료만 모아 준다.** 판단과 집필은
Claude 웹에서 사람이 대화하며 한다. 그래서 이 한 장에는 «무엇을 봤고 왜
눈에 띄었는가» 가 숫자와 함께 들어가야 한다. (prd F-3)

숫자는 여기서 다시 계산하지 않는다. `analysis.build()` 가 이미 낸 값을
가져다 쓴다 — 두 곳에서 따로 계산하면 화면과 한 장이 어긋난다. (tech §2)
"""
import re

import pandas as pd

from . import analysis, config, subtitles

CHANNELS_CSV = config.DATA_PROCESSED / "channels.csv"

NEARBY_N = 5          # ■ 주변 에 넣을 편수
RECENT_DAYS = 30      # 검색어 공급량을 «최근» 과 «이전» 으로 가르는 선


WRAP = 44             # 자막 한 줄 글자수


def _wrap_ja(text, indent="    "):
    """일본어를 읽을 만한 길이로 접는다.

    일본어에는 띄어쓰기가 없어 `textwrap` 이 못 접는다. 한 줄로 두면 화면에서
    오른쪽이 잘려 보내기 전에 확인할 수가 없다. 「。」 뒤에서 끊고, 그래도
    길면 글자 수로 자른다.
    """
    out, line = [], ""
    for part in re.split(r"(?<=。)", text):
        while len(part) > WRAP:
            if line:
                out.append(line)
                line = ""
            out.append(part[:WRAP])
            part = part[WRAP:]
        if len(line) + len(part) > WRAP:
            out.append(line)
            line = part
        else:
            line += part
    if line:
        out.append(line)
    return "\n".join(indent + x for x in out if x)


def _fmt(n, unit=""):
    """결측을 «?» 로. 0 으로 바꾸면 «구독자 0명» 처럼 거짓말이 된다."""
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "?"
    return f"{int(round(n)):,}{unit}"


def _channel_row(channel_id):
    """channels.csv 에서 이 채널 줄. 아직 검증 안 된 채널이면 None."""
    if not CHANNELS_CSV.exists():
        return None
    try:
        c = pd.read_csv(CHANNELS_CSV)
    except Exception:
        return None
    hit = c[c["channel_id"] == channel_id]
    return None if hit.empty else hit.iloc[0]


def _seed_standing(df, seed):
    """검색어의 성과 순위와 공급 추이.

    성과 — 검색어별 Video Score 중앙값 순위
    공급 — 최근 30일에 올라온 편수 vs 그 이전. 늘고 있으면 남들도 파는 중이다.
    """
    if not seed:
        return None
    med = df.groupby("seed")["video_score"].median().sort_values(ascending=False)
    if seed not in med.index:
        return None
    rank = list(med.index).index(seed) + 1

    same = df[df["seed"] == seed]
    recent = int((same["age_days"] <= RECENT_DAYS).sum())
    before = int((same["age_days"] > RECENT_DAYS).sum())
    return {"rank": rank, "of": len(med), "recent": recent, "before": before}


def _titles(rows, exclude_id):
    out = []
    for _, r in rows.iterrows():
        if r["video_id"] == exclude_id:
            continue
        ko = str(r.get("title_ko") or "").strip()
        line = f"    · {ko or r['title']}"
        if ko:
            # 주변 제목은 맥락일 뿐이다. 뜻은 한글이 이미 전하므로 원문이
            # 길면 줄인다 — 화면에서 옆으로 잘려 나가는 편이 더 나쁘다.
            orig = str(r["title"])
            if len(orig) > 60:
                orig = orig[:60] + "…"
            line += f"\n        {orig}"
        out.append(line)
        if len(out) >= NEARBY_N:
            break
    return out


def one_pager(video_id, with_subtitles=True):
    """붙여넣을 한 장. 어떤 이유로도 예외를 올리지 않는다."""
    df = analysis.build()
    hit = df[df["video_id"] == video_id]
    if hit.empty:
        return f"videos.csv 에 {video_id} 가 없습니다."
    v = hit.iloc[0]

    ko = str(v.get("title_ko") or "").strip()
    L = []
    add = L.append

    add("다음은 일본어 유튜브 롱폼 중 «작은 채널인데 잘 된 영상» 을 찾는")
    add("개인 도구가 오늘 뽑아낸 한 편입니다. 숫자와 자막 발췌를 함께 넣었습니다.")
    add("")

    # ── ■ 소재 ────────────────────────────────────────────────────
    add("■ 소재")
    add(f"  {ko or v['title']}")
    if ko:
        add(f"  원문 {v['title']}")
    mins = (v["duration_seconds"] or 0) / 60
    add(f"  {mins:.0f}분 · {str(v['published_at'])[:10]} 게시 "
        f"· 게시 후 {_fmt(v.get('age_days'))}일")
    add(f"  채널 {v['channel_name']}")
    add(f"  https://www.youtube.com/watch?v={video_id}")
    add("")

    # ── ■ 왜 이 영상인가 ──────────────────────────────────────────
    add("■ 왜 이 영상인가")
    ratio = v.get("subscriber_view_ratio")
    add(f"  구독자 {_fmt(v.get('channel_subscribers'))}명 "
        f"→ 조회 {_fmt(v.get('views'))}회"
        + (f"  (구독자의 {ratio:.1f}배)" if pd.notna(ratio) else ""))
    add(f"  하루 평균 {_fmt(v.get('adviews'))}회")

    # Channel Score 는 비어 있을 수 있다. «점수가 낮다» 가 아니라 «모른다» 다.
    # nan 을 그대로 내보내면 읽는 쪽이 나쁜 채널로 오해한다.
    ch = _channel_row(v["channel_id"])
    if ch is None:
        cs, note = "미검증", "  (아직 채널 검증을 돌리지 않았습니다)"
    elif pd.isna(ch["channel_score"]):
        cs = "판정 못 함"
        note = (f"  (이 채널에서 찾은 롱폼이 {int(ch['longform_found'])}편뿐이라 "
                "비교할 과거 영상이 모자랍니다)")
    else:
        cs, note = f"{ch['channel_score']:.1f}", ""
    add(f"  Video Score {v['video_score']:.1f} / Channel Score {cs}")
    if note:
        add(note)

    pct = v.get("age_adjusted_percentile")
    if pd.notna(pct):
        add(f"  같은 나이대({v['age_bucket']}) {int(v['age_bucket_n'])}건 중 "
            f"상위 {100 - pct:.0f}%")

    if ch is not None and pd.notna(ch["channel_baseline"]):
        line = f"    ↳ 이 채널 평소보다 {ch['channel_baseline']:.2f}배"
        if pd.notna(ch["channel_momentum"]):
            line += f" · 최근 흐름 {ch['channel_momentum']:.2f}배"
        add(line)

    st = _seed_standing(df, v.get("seed"))
    if st:
        add(f"  검색어 「{v['seed']}」 — 성과 {st['rank']}/{st['of']}위, "
            f"공급 이전 {st['before']}건 → 최근 30일 {st['recent']}건")
    add("")

    # ── ■ 자막 발췌 ──────────────────────────────────────────────
    add("■ 자막 발췌")
    if not with_subtitles:
        add("  (자막 없이 뽑음)")
    else:
        d = subtitles.digest(video_id)
        if not d["ok"]:
            add(f"  자막 없음 — {d['why']}")
        else:
            add(f"  [앞 3분]")
            add(_wrap_ja(d["head"]))
            add("")
            add(f"  [반복 키워드]")
            kw = [f"{w}({n})" for w, n in d["keywords"]]
            for i in range(0, len(kw), 6):
                add("    " + " · ".join(kw[i:i + 6]))
            add("")
            add(f"  [마지막 1분]")
            add(_wrap_ja(d["tail"]))
            add("")
            add(f"  (전체 {d['chars']:,}자 중 앞뒤만 발췌. "
                f"가운데는 반복 키워드로 대신했습니다.)")
    add("")

    # ── ■ 주변 ───────────────────────────────────────────────────
    add("■ 주변")
    same_seed = df[df["seed"] == v.get("seed")].nlargest(NEARBY_N + 1, "video_score")
    lines = _titles(same_seed, video_id)
    if lines:
        add(f"  같은 검색어 「{v['seed']}」 상위 {len(lines)}편")
        L.extend(lines)

    # channels.csv 는 채널당 한 줄뿐이라 «채널의 최근 영상 목록» 이 없다.
    # 우리가 모은 것만 보여 주고, 그렇게 이름 붙인다. 없는 것을 있는 척하지 않는다.
    mine = df[df["channel_id"] == v["channel_id"]].sort_values(
        "published_at", ascending=False)
    lines = _titles(mine, video_id)
    if lines:
        add("")
        add(f"  이 채널에서 함께 수집된 영상 {len(lines)}편")
        L.extend(lines)
    elif ch is not None:
        add("")
        add(f"  이 채널에서 수집된 영상은 이 한 편뿐입니다 "
            f"(채널 전체 롱폼 {int(ch['longform_found'])}편은 검증에만 씀)")

    return "\n".join(L)
