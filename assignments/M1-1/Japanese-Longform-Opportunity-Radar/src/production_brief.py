# -*- coding: utf-8 -*-
"""Production Brief — «고른 소재를 이 채널에서 어떤 영상으로 만들 것인가».

    from src import production_brief as brief
    r = brief.build(video_id, "loss_defense")
    r["text"]   붙여넣을 브리프
    r["path"]   data/briefs/{channel_id}/{video_id}.md

Opportunity Card(`export.one_pager`)와 역할이 다르다. (지시서 §39)

    one_pager   이 영상을 «후보로 고를지» 판단한다
    brief       고른 소재를 «어떤 새 영상으로 만들지» 설계한다

**채널을 고르지 않고는 만들 수 없다.** (§40) 같은 소재라도 채널에 따라
잡는 각도가 다르다. 같은 영상으로 두 채널 브리프를 각각 만들 수 있다.

이 파일은 **조립만 한다.** 새로 LLM 을 부르지 않는다 —
판정은 `channel_fit`, 댓글 해석은 `comments.analyze` 가 이미 했고,
제목·썸네일·구성은 `prompts/script_writer.md` 가 내놓는다. 같은 것을
두 번 물으면 돈만 들고 두 답이 어긋난다.
"""
from datetime import datetime, timezone

from . import (analysis, channel_fit, channels, comments, config,
               seeds, subtitles)

BRIEFS = config.ROOT / "data" / "briefs"
PROMPT_VERSION = 1

NEARBY_N = 5


def path_for(video_id, channel_id):
    return BRIEFS / channel_id / f"{video_id}.md"


def _fmt(n, unit=""):
    if n is None or n != n:
        return "?"
    return f"{int(round(n)):,}{unit}"


def _bullets(items, limit=5, indent="  "):
    out = []
    for x in (items or [])[:limit]:
        if isinstance(x, dict):
            x = f"{x.get('ja', '')} — {x.get('ko', '')}".strip(" —")
        out.append(f"{indent}- {x}")
    return out or [f"{indent}- (없음)"]


def build(video_id, channel_id, with_comments=True):
    """브리프를 만들어 파일로 남기고 본문을 돌려준다. 예외를 올리지 않는다."""
    ch = channels.get(channel_id)
    if not ch:
        return {"ok": False, "why": f"모르는 채널 id '{channel_id}'"}

    df = analysis.build()
    hit = df[df["video_id"] == video_id]
    if hit.empty:
        return {"ok": False, "why": f"videos.csv 에 {video_id} 가 없습니다"}
    v = hit.iloc[0]

    def g(k, d=""):
        val = v.get(k, d)
        return d if val is None or val != val else val

    fit = channel_fit.judge(video_id, channel_id, v)
    dig = subtitles.digest_text(video_id)
    ca = comments.cached_analysis(video_id) if with_comments else None
    ang = (ca or {}).get("channel_angles", {}).get(channel_id, {})
    common = (ca or {}).get("common_analysis", {})

    ko = str(g("title_ko")).strip()
    L = []
    add = L.append

    add("# Production Brief")
    add("")
    add(f"- Generated At: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    add(f"- Channel Profile Version: {ch.get('profile_version', 1)}")
    add(f"- Comment Analysis: "
        + (f"{ca['analyzed_count']}건 ({ca['analyzed_at'][:16]})" if ca else "없음"))
    add(f"- Prompt Version: {PROMPT_VERSION}")
    add("")

    # ── 채널 ──
    add("## ■ Channel Profile")
    add("")
    add(f"- Channel ID: `{ch['id']}`")
    add(f"- 채널명: {ch.get('emoji', '')} {ch['name_ko']} ({ch.get('name_ja', '')})")
    add(f"- 핵심 시청자: {ch.get('audience', '')}")
    add(f"- 채널 약속: {ch.get('promise_ko', '')}")
    add(f"- 핵심 질문: {ch.get('core_question_ko', '')}")
    add(f"- 주요 Lens: {', '.join(ch.get('lenses', []))}")
    if not ch.get("production_enabled"):
        add("- ⚠️ 이 채널은 **아직 실제 업로드 전**입니다 (연구·후보 축적 단계).")
    add("")

    # ── 소재 ──
    add("## ■ 주제 (원 소재)")
    add("")
    add(f"- {ko or g('title')}")
    if ko:
        add(f"- 원문: {g('title')}")
    add(f"- {int(float(g('duration_seconds', 0)) // 60)}분 · "
        f"{str(g('published_at'))[:10]} 게시 · 게시 후 {_fmt(g('age_days'))}일")
    add(f"- 채널 {g('channel_name')} · https://www.youtube.com/watch?v={video_id}")
    add("")
    add("> 이 영상을 다시 쓰지 않는다. **수요가 있다는 증거**로만 쓴다.")
    add("")

    # ── 시장 데이터 ──
    add("## ■ 시장 데이터")
    add("")
    ratio = g("subscriber_view_ratio")
    add(f"- 구독자 {_fmt(g('channel_subscribers'))}명 → 조회 {_fmt(g('views'))}회"
        + (f" (구독자의 {ratio:.1f}배)" if ratio == ratio else ""))
    add(f"- 채널 전체 영상 {_fmt(g('channel_video_count'))}편")
    add(f"- Video Score {float(g('video_score', 0)):.1f} "
        f"· 같은 나이대({g('age_bucket')}) {int(float(g('age_bucket_n', 0)))}건 중")
    add(f"- 하루 평균 {_fmt(g('adviews'))}회")
    st = _seed_standing(df, g("seed"))
    if st:
        add(f"- 검색어 「{g('seed')}」 — 성과 {st['rank']}/{st['of']}위 "
            f"· 공급 이전 {st['before']}건 → 최근 30일 {st['recent']}건")
    add("")

    # ── Channel Fit ──
    add("## ■ Channel Fit")
    add("")
    if fit.get("ok"):
        for key, label in channel_fit.ASPECTS:
            add(f"- {label}: **{fit.get(key, '—')}**")
        add("")
        add(f"근거 — {fit.get('reason', '')}")
        if fit.get("angle_ko"):
            add("")
            add(f"**이 채널에서 잡을 각도** — {fit['angle_ko']}")
    else:
        add(f"- 판정하지 못했습니다 — {fit.get('why', '')}")
    add("")

    # ── 댓글 ──
    add("## ■ 시청자가 실제로 말한 것")
    add("")
    if not ca:
        add("  - (댓글을 아직 받지 않았습니다)")
        add("")
        add("  `python -c \"from src import comments; comments.analyze('%s')\"`"
            % video_id)
    else:
        add(f"댓글 {ca.get('comment_count', 0)}건 중 "
            f"{ca.get('analyzed_count', 0)}건 분석")
        add("")
        add("**되풀이되는 걱정**")
        L.extend(_bullets(common.get("top_concerns")))
        add("")
        add("**실제로 묻는 질문**")
        L.extend(_bullets(common.get("questions")))
        add("")
        add("**두려움·불안**")
        L.extend(_bullets(common.get("fears")))
        add("")
        add("**원하는 결과**")
        L.extend(_bullets(common.get("desired_outcomes")))
        add("")
        add("**반론·의심**")
        L.extend(_bullets(common.get("objections")))
        add("")
        add("**시청자가 실제 쓰는 일본어 표현** (한국어 뜻 병기)")
        L.extend(_bullets(common.get("viewer_phrases")))
        add("")
        add("**기존 영상이 답하지 않은 것** ← 가장 중요")
        L.extend(_bullets(common.get("unresolved_gaps")))
    add("")

    # ── 이 채널 각도 ──
    if ang:
        add("## ■ 이 채널 관점의 재정의")
        add("")
        add(f"{ang.get('angle', '')}")
        add("")
        add("**이 채널이 메울 공백**")
        L.extend(_bullets(ang.get("unresolved_gaps")))
        add("")

    # ── 자막 ──
    add("## ■ 원 영상은 어떻게 풀었나 (자막 발췌)")
    add("")
    if dig.get("ok"):
        add("```")
        add(dig["text"])
        add("```")
        add(f"(전체 {dig.get('chars', 0):,}자 중 {dig.get('digest_chars', 0)}자만)")
    else:
        add(f"  - 자막 없음 — {dig.get('why', '')}")
    add("")

    # ── 경쟁 ──
    add("## ■ 경쟁 콘텐츠")
    add("")
    same = df[(df["seed"] == g("seed")) & (df["video_id"] != video_id)]
    add(f"**같은 검색어 「{g('seed')}」 상위**")
    L.extend(_bullets(
        [f"{_titleof(r)} (구독 {_fmt(r['channel_subscribers'])} · "
         f"조회 {_fmt(r['views'])})"
         for _, r in same.nlargest(NEARBY_N, "video_score").iterrows()]))
    add("")
    mine = df[(df["channel_id"] == g("channel_id")) & (df["video_id"] != video_id)]
    if not mine.empty:
        add("**이 채널에서 함께 수집된 영상**")
        L.extend(_bullets([_titleof(r) for _, r in
                           mine.sort_values("published_at", ascending=False)
                               .head(NEARBY_N).iterrows()]))
        add("")

    # ── 다음 단계 ──
    add("## ■ 다음 단계")
    add("")
    add("이 브리프를 `prompts/script_writer.md` 와 함께 Claude 웹에 넣으면")
    add("제목 후보·썸네일 문구·15~30분 일본어 대본·FACT CHECK 목록이 나온다.")
    add("")
    add("## ■ 금지")
    add("")
    add("- 원본 대본 장문 복사")
    add("- 댓글 장문 복사")
    add("- 사실 검증 없이 단정 (숫자·제도·법률은 [FACT CHECK] 표시)")
    add("- 같은 사실과 구성을 제목만 바꿔 두 채널에 올리기")

    text = "\n".join(L)
    cap = config.PRODUCTION_BRIEF_MAX_CHARS
    if len(text) > cap:
        text = text[:cap - 40] + "\n\n… (길이 상한으로 잘림)"

    p = path_for(video_id, channel_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return {"ok": True, "text": text, "path": str(p),
            "chars": len(text), "fit": fit, "has_comments": bool(ca)}


def _titleof(r):
    ko = str(r.get("title_ko") or "").strip()
    return (ko or str(r.get("title") or ""))[:52]


def _seed_standing(df, seed):
    if not seed:
        return None
    med = df.groupby("seed")["video_score"].median().sort_values(ascending=False)
    if seed not in med.index:
        return None
    same = df[df["seed"] == seed]
    return {"rank": list(med.index).index(seed) + 1, "of": len(med),
            "recent": int((same["age_days"] <= 30).sum()),
            "before": int((same["age_days"] > 30).sum())}


def script_package(video_id, channel_id):
    """Claude 대본용 자료 한 덩어리. (§53)

    `script_writer.md` + Channel Profile + Brief + Digest + Comment Analysis.
    **raw 자막·댓글 전체는 넣지 않는다.**
    """
    ch = channels.get(channel_id)
    if not ch:
        return {"ok": False, "why": f"모르는 채널 id '{channel_id}'"}

    b = build(video_id, channel_id)
    if not b.get("ok"):
        return b

    dig = subtitles.digest_text(video_id)
    from . import translate
    text = translate.load_prompt(
        "script_writer",
        CHANNEL_ID=ch["id"], CHANNEL_NAME=ch["name_ko"],
        CHANNEL_AUDIENCE=ch.get("audience", ""),
        CHANNEL_PROMISE=ch.get("promise_ko", ""),
        CHANNEL_CORE_QUESTION=ch.get("core_question_ko", ""),
        CHANNEL_LENSES=", ".join(ch.get("lenses", [])),
        PRODUCTION_BRIEF=b["text"],
        TRANSCRIPT_DIGEST=dig.get("text", "(자막 없음)") if dig.get("ok")
        else f"(자막 없음 — {dig.get('why', '')})",
        COMMENT_ANALYSIS=comments.analysis_text(video_id, channel_id)
        or "(댓글 분석 없음)",
    )
    if not text:
        return {"ok": False, "why": translate.last_error or "프롬프트를 읽지 못했습니다"}
    return {"ok": True, "text": text, "chars": len(text)}
