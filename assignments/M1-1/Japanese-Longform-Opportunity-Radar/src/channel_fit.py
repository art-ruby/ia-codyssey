# -*- coding: utf-8 -*-
"""Channel Fit — «이 시장 신호가 우리 채널에서 만들 가치가 있는가».

    from src import channel_fit
    r = channel_fit.judge(video_id, "loss_defense", row)
    r["verdict"]        HIGH · MEDIUM · LOW  (항목별)
    r["reason"]         왜 그렇게 봤는지
    r["angle_ko"]       이 채널이라면 어떤 각도로

Video Score 는 «이 영상이 강한가», Channel Score 는 «이 채널이 오르는가» 를
묻는다. 둘 다 **시장** 이야기다. Channel Fit 은 다른 질문이다 —
그 시장 신호를 **우리가** 만들 만한가. (지시서 §17)

**0~100 점수를 만들지 않는다.** (§18·§77)
HIGH/MEDIUM/LOW 와 근거 문장만 쓴다. 가짜 소수점은 없는 정밀도를 꾸며 낸다.

LLM 을 부르므로 전체 영상에 돌리지 않는다. Video Score 상위 후보만. (§23)
결과는 `data/processed/channel_fit.csv` 에 캐시한다 — 같은 영상·같은 채널·
같은 프로필 버전이면 다시 묻지 않는다.
"""
import csv
from datetime import datetime, timezone

from . import channels, config, subtitles, translate

STORE = config.DATA_PROCESSED / "channel_fit.csv"

FIELDS = [
    "video_id", "channel_id", "profile_version",
    "audience_fit", "channel_relevance", "money_impact", "problem_strength",
    "longform_potential", "news_risk", "evergreen_potential",
    "reason", "angle_ko", "analyzed_at",
]

LEVELS = {"HIGH", "MEDIUM", "LOW"}

# 판정 항목만 모아 둔다. 화면과 브리프가 같은 순서로 보여 주도록.
ASPECTS = [
    ("audience_fit", "시청자 적합"),
    ("channel_relevance", "채널 관련성"),
    ("money_impact", "돈 영향"),
    ("problem_strength", "문제 강도"),
    ("longform_potential", "롱폼 가능성"),
    ("news_risk", "뉴스 의존"),
    ("evergreen_potential", "오래 감"),
]


def _read():
    if not STORE.exists():
        return []
    with open(STORE, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _key(row):
    return (row.get("video_id"), row.get("channel_id"),
            str(row.get("profile_version")))


def cached(video_id, channel_id, profile_version):
    want = (video_id, channel_id, str(profile_version))
    return next((r for r in _read() if _key(r) == want), None)


def _save(row):
    """한 줄 덧붙인다. 같은 열쇠의 옛 줄은 남겨 둔다 —

    프로필이 바뀌면 판정도 달라진다. 옛 판정을 지우면 «왜 그때는 이렇게
    봤나» 를 나중에 알 수 없다. 읽을 때 최신 것만 고르면 된다.
    """
    STORE.parent.mkdir(parents=True, exist_ok=True)
    new = not STORE.exists()
    with open(STORE, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def _level(v):
    """모델이 소문자나 «높음» 을 줘도 받아 준다. 모르면 빈 값."""
    s = str(v or "").strip().upper()
    if s in LEVELS:
        return s
    return {"높음": "HIGH", "보통": "MEDIUM", "중간": "MEDIUM",
            "낮음": "LOW"}.get(str(v or "").strip(), "")


def judge(video_id, channel_id, row, force=False, with_digest=True):
    """한 영상 × 한 채널. **예외를 올리지 않는다.**

    `row` 는 `analysis.build()` 의 한 줄(pandas Series 또는 dict).
    """
    ch = channels.get(channel_id)
    if not ch:
        return {"ok": False, "why": f"모르는 채널 id '{channel_id}'"}

    ver = ch.get("profile_version", 1)
    if not force:
        hit = cached(video_id, channel_id, ver)
        if hit:
            return {"ok": True, "cached": True, **hit}

    ok, why = translate.available()
    if not ok:
        return {"ok": False, "why": f"판정할 수 없습니다 — {why}"}

    def g(k, default=""):
        v = row.get(k, default) if hasattr(row, "get") else default
        return "" if v is None or v != v else v      # NaN 은 빈 값으로

    digest = ""
    if with_digest:
        d = subtitles.digest_text(video_id)
        digest = d.get("text", "") if d.get("ok") else f"(자막 없음 — {d.get('why', '')})"

    prompt = translate.load_prompt(
        "channel_fit",
        channel_id=ch["id"], channel_name=ch["name_ko"],
        channel_audience=ch.get("audience", ""),
        channel_promise=ch.get("promise_ko", ""),
        channel_question=ch.get("core_question_ko", ""),
        channel_lenses=", ".join(ch.get("lenses", [])),
        title=g("title"), title_ko=g("title_ko"),
        video_channel=g("channel_name"),
        subscribers=f"{int(g('channel_subscribers', 0) or 0):,}",
        views=f"{int(g('views', 0) or 0):,}",
        ratio=f"{float(g('subscriber_view_ratio', 0) or 0):.1f}",
        age=int(float(g("age_days", 0) or 0)),
        minutes=int(float(g("duration_seconds", 0) or 0) // 60),
        seed=g("seed"), digest=digest or "(자막 없음)",
    )
    if not prompt:
        return {"ok": False, "why": translate.last_error or "프롬프트를 읽지 못했습니다"}

    got = translate.ask_json(prompt)
    if not isinstance(got, dict):
        return {"ok": False,
                "why": translate.last_error or "판정 결과를 읽지 못했습니다"}

    out = {"video_id": video_id, "channel_id": channel_id,
           "profile_version": ver,
           "reason": str(got.get("reason", ""))[:500],
           "angle_ko": str(got.get("angle_ko", ""))[:300],
           "analyzed_at": datetime.now(timezone.utc).isoformat()}
    for k, _ in ASPECTS:
        out[k] = _level(got.get(k))

    if not out["channel_relevance"]:
        # 핵심 항목이 비면 판정으로 쓸 수 없다. 저장하지 않는다 —
        # 빈 판정을 캐시하면 다시 물어보지도 않게 된다.
        return {"ok": False, "why": "판정이 비어 있습니다 (모델 응답 형식 확인 필요)"}

    _save(out)
    return {"ok": True, "cached": False, **out}


def is_crossover(fits):
    """두 채널 모두 채널 관련성이 HIGH 면 교차 후보. (§21)

    `fits` 는 {channel_id: judge() 결과}.
    """
    high = [c for c, f in fits.items()
            if f.get("ok") and f.get("channel_relevance") == "HIGH"]
    return len(high) >= 2, high


def summary(fit):
    """화면에 한 줄로. «HIGH 5 · MEDIUM 1 · LOW 1» 처럼."""
    if not fit.get("ok"):
        return fit.get("why", "판정 없음")
    n = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for k, _ in ASPECTS:
        v = fit.get(k)
        if v in n:
            n[v] += 1
    return " · ".join(f"{k} {v}" for k, v in n.items() if v)
