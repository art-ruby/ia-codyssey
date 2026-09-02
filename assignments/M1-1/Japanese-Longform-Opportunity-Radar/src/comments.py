# -*- coding: utf-8 -*-
"""댓글 수집 — **고른 제작 후보만.**

    from src import comments
    r = comments.fetch("DD3gDj8cKGo")
    r["status"]    ok · comments_disabled · no_comments · quota_error …
    r["items"]     [{text, like_count, published_at, reply_count, comment_id}, …]

전체 영상에서 받지 않는다. 300~400건을 자동으로 받으면 읽지도 않을 것을
쌓게 된다. Radar 가 후보를 좁히고, 사람이 «이걸 만들자» 고 고른 것만
받는다. (지시서 §31·§58)

**«댓글이 없다» 와 «지금 못 받았다» 를 반드시 가른다.** (§33)
일시 오류를 «댓글 없음» 으로 저장하면 그 영상은 영영 다시 안 본다.
"""
import json
from datetime import datetime, timezone

from . import config
from .youtube import (Client, CommentsDisabled, QuotaError, VideoNotFound)

RAW = config.DATA_RAW / "comments"

# 다시 받아도 결과가 같은 상태. 캐시를 그대로 쓴다.
FINAL = {"ok", "comments_disabled", "no_comments", "not_found"}

WHY = {
    "ok": "받았습니다",
    "comments_disabled": "이 영상은 댓글을 꺼 두었습니다",
    "no_comments": "댓글이 아직 하나도 없습니다",
    "not_found": "영상이 내려갔거나 비공개입니다",
    "quota_error": "오늘 할당량을 다 썼습니다. 태평양시 자정에 초기화됩니다",
    "temporary_error": "지금 받지 못했습니다. 잠시 뒤 다시 해 보세요",
    "no_key": "YOUTUBE_API_KEY 가 없습니다",
}


def path_for(video_id):
    return RAW / f"{video_id}.json"


def cached(video_id):
    """받아 둔 것. 없거나 깨졌으면 None."""
    p = path_for(video_id)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _save(video_id, data):
    RAW.mkdir(parents=True, exist_ok=True)
    path_for(video_id).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _rows(payload):
    out = []
    for it in payload.get("items", []):
        top = (it.get("snippet", {}).get("topLevelComment", {})
                 .get("snippet", {}))
        text = (top.get("textOriginal") or top.get("textDisplay") or "").strip()
        if not text:
            continue
        out.append({
            "comment_id": it.get("id", ""),
            "text": text,
            "like_count": int(top.get("likeCount") or 0),
            "published_at": top.get("publishedAt", ""),
            "reply_count": int(it.get("snippet", {}).get("totalReplyCount") or 0),
        })
    return out


def fetch(video_id, force=False, client=None, max_count=None):
    """댓글을 받아 캐시에 넣고 결과를 돌려준다. **예외를 올리지 않는다.**

    이미 받아 둔 것이 «다시 받아도 같은» 상태면 API 를 부르지 않는다.
    일시 오류로 남아 있으면 다시 받는다 — 그것이 «없음» 과 다른 이유다.
    """
    old = cached(video_id)
    if old and not force and old.get("status") in FINAL:
        return old

    limit = max_count or config.COMMENTS_MAX_COUNT
    try:
        client = client or Client()
    except RuntimeError:
        return {"video_id": video_id, "status": "no_key",
                "why": WHY["no_key"], "items": []}

    try:
        payload = client.comment_threads(video_id, max_results=limit)
        items = _rows(payload)
        status = "ok" if items else "no_comments"
    except CommentsDisabled:
        items, status = [], "comments_disabled"
    except VideoNotFound:
        items, status = [], "not_found"
    except QuotaError:
        # 캐시에 덮어쓰지 않는다 — 다시 받아야 할 것이다.
        return {"video_id": video_id, "status": "quota_error",
                "why": WHY["quota_error"], "items": []}
    except Exception as e:                       # noqa: BLE001
        return {"video_id": video_id, "status": "temporary_error",
                "why": f"{WHY['temporary_error']} ({type(e).__name__})",
                "items": []}

    data = {
        "video_id": video_id,
        "status": status,
        "why": WHY[status],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items[:limit],
    }
    _save(video_id, data)
    return data


def top_by_likes(items, n=15):
    """좋아요 많은 순. 분석에 넣을 때 전부 넣지 않는다."""
    return sorted(items, key=lambda r: -r.get("like_count", 0))[:n]


# ──────────────────────────────────────────────────────────────────
# 분석 — 감성분석이 아니다. «무엇 때문에 괴로운가» 를 뽑는다. (§34)
# ──────────────────────────────────────────────────────────────────

PROCESSED = config.DATA_PROCESSED / "comments"

ANALYZE_TOP = 30          # 좋아요 상위 몇 개를 LLM 에 넣나


def analysis_path(video_id):
    return PROCESSED / f"{video_id}.json"


def cached_analysis(video_id):
    p = analysis_path(video_id)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def analyze(video_id, row=None, force=False):
    """댓글 → 구조화된 요약. **예외를 올리지 않는다.**

    raw 댓글을 대본 작성기에 그대로 넣지 않는다. 여기서 한 번 줄인 뒤
    Production Brief 로 넘긴다. (§36)

    같은 댓글도 채널에 따라 다르게 읽힌다 — `channel_angles` 를 채널마다
    따로 만든다. (§35)
    """
    from . import channels, translate           # 순환 참조를 피해 늦게 부른다

    if not force:
        hit = cached_analysis(video_id)
        if hit:
            return {"ok": True, "cached": True, **hit}

    raw = cached(video_id) or fetch(video_id)
    if raw.get("status") != "ok" or not raw.get("items"):
        return {"ok": False, "why": raw.get("why", "댓글이 없습니다"),
                "status": raw.get("status")}

    ok, why = translate.available()
    if not ok:
        return {"ok": False, "why": f"분석할 수 없습니다 — {why}"}

    picked = top_by_likes(raw["items"], ANALYZE_TOP)
    body = "\n".join(f"[👍{c['like_count']}] {c['text'][:300]}" for c in picked)

    live = channels.records()
    block = "\n".join(
        f"- `{c['id']}` {c['name_ko']} — {c.get('core_question_ko', '')}"
        for c in live) or "- (등록된 채널 없음)"

    def g(k):
        if row is None or not hasattr(row, "get"):
            return ""
        v = row.get(k, "")
        return "" if v is None or v != v else str(v)

    prompt = translate.load_prompt(
        "comment_analyzer",
        title=g("title") or video_id, title_ko=g("title_ko"),
        n=len(picked), comments=body,
        channel_block=block,
        first_channel_id=live[0]["id"] if live else "channel_id",
    )
    if not prompt:
        return {"ok": False, "why": translate.last_error or "프롬프트를 읽지 못했습니다"}

    got = translate.ask_json(prompt)
    if not isinstance(got, dict) or "common_analysis" not in got:
        return {"ok": False,
                "why": translate.last_error or "분석 결과를 읽지 못했습니다"}

    out = {
        "video_id": video_id,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "comment_count": len(raw["items"]),
        "analyzed_count": len(picked),
        "common_analysis": got.get("common_analysis") or {},
        "channel_angles": got.get("channel_angles") or {},
    }
    PROCESSED.mkdir(parents=True, exist_ok=True)
    analysis_path(video_id).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "cached": False, **out}


def analysis_text(video_id, channel_id=None, cap=None):
    """LLM 에 넣을 요약 한 덩어리. 최대 `COMMENT_ANALYSIS_MAX_CHARS`.

    채널을 주면 그 채널 관점(angle)만 붙인다 — 다른 채널 각도까지 넣으면
    대본 작성기가 헷갈린다.
    """
    d = cached_analysis(video_id)
    if not d:
        return ""
    cap = cap or config.COMMENT_ANALYSIS_MAX_CHARS
    c = d.get("common_analysis", {})

    def lines(key, label):
        v = c.get(key) or []
        if not v:
            return ""
        if key == "viewer_phrases":
            body = " / ".join(
                f"{x.get('ja', '')}({x.get('ko', '')})" if isinstance(x, dict) else str(x)
                for x in v[:5])
        else:
            body = " / ".join(str(x) for x in v[:5])
        return f"[{label}] {body}"

    parts = [x for x in [
        lines("top_concerns", "되풀이되는 걱정"),
        lines("questions", "실제 질문"),
        lines("fears", "두려움"),
        lines("desired_outcomes", "원하는 결과"),
        lines("objections", "반론·의심"),
        lines("viewer_phrases", "시청자가 쓰는 표현"),
        lines("unresolved_gaps", "아직 답 안 된 것"),
    ] if x]

    ang = (d.get("channel_angles") or {}).get(channel_id or "")
    if ang:
        parts.append(f"[이 채널 각도] {ang.get('angle', '')}")
        gaps = ang.get("unresolved_gaps") or []
        if gaps:
            parts.append(f"[이 채널이 메울 공백] {' / '.join(str(x) for x in gaps[:4])}")

    text = "\n".join(parts)
    return text[:cap - 1] + "…" if len(text) > cap else text
