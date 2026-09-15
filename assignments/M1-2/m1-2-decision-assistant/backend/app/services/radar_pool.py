"""RADAR 후보 풀 — 깔때기의 «끝» 이 아니라 «판단이 필요한 지점» 을 읽는다.

DA v2 는 outbox.sqlite3(AutoMaker 로 보내기로 한 패키지)만 읽었다. 그건 RADAR 깔때기의 맨 끝이라
판단 보조가 판단이 끝난 뒤에 앉아 있었다(실측: 수집 1,870 → fit 판정 9 → 브리프 5 → 패키지 1).

여기서는 RADAR 런타임에서 채널마다 다음을 내보낸다:
  packaged   outbox 에 있는 것
  briefed    data/briefs/<channel>/<video>.md 가 있는 것
  fit_judged channel_fit.csv 에 (video, channel) 판정이 있는 것
  scored     analysis.build() 점수 상위 N — 아직 채널 판정이 없는 후보 (Gate 1 에서 REVIEW → 재판정)
점수·지표는 analysis.build() 의 값 그대로다(재계산 없음). 결과는 data/decision_assistant/candidate_pool.json.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REL_PATH = Path("data") / "decision_assistant" / "candidate_pool.json"

_RUNNER = r"""
import json, sys, csv, glob, os, sqlite3, math
args = json.loads(sys.argv[1]); root = args["root"]; top = int(args.get("top", 20))
sys.path.insert(0, root)
out = {"ok": False}
try:
    from src import analysis, config
    try:
        from src import seeds as _seeds
        seed_tags = {str(r.get("term")): set(r.get("channels") or ()) for r in _seeds.records()}
    except Exception:
        seed_tags = {}
    frame = analysis.build(config.ROOT).reset_index(drop=True)
    by_vid = {str(r["video_id"]): r for r in frame.to_dict("records")}
    profiles = json.load(open(os.path.join(root, "data/config/channels.json"), encoding="utf-8-sig"))
    channels = [p["id"] for p in profiles if p.get("id")]
    fit_rows = list(csv.DictReader(open(os.path.join(root, "data/processed/channel_fit.csv"), encoding="utf-8-sig"))) \
        if os.path.isfile(os.path.join(root, "data/processed/channel_fit.csv")) else []
    fit_latest = {}
    for r in fit_rows:
        fit_latest[(r["video_id"], r["channel_id"])] = r
    briefs = set()
    for md in glob.glob(os.path.join(root, "data/briefs/*/*.md")):
        briefs.add((os.path.basename(md)[:-3], os.path.basename(os.path.dirname(md))))
    packaged = {}
    db = os.path.join(root, "data/automaker-outbox/outbox.sqlite3")
    if os.path.isfile(db):
        for (body,) in sqlite3.connect(db).execute("select body from packages order by revision"):
            e = json.loads(body); p = e.get("payload") or {}
            packaged[(p.get("opportunity_id"), (p.get("target_channel") or {}).get("id"))] = e.get("package_id")
    def num(v):
        try:
            f = float(v); return None if math.isnan(f) else f
        except (TypeError, ValueError): return None
    def s(v):
        return None if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)
    rows = []
    for ch in channels:
        keys = {k for k in fit_latest if k[1] == ch} | {k for k in briefs if k[1] == ch} | {k for k in packaged if k[1] == ch}
        # 미판정 상위 N 은 «이 채널로 태그된 seed 로 찾은 영상» 만. 태그 없는 영상(예: AI, 仕事)은 어느 채널의
        # 후보도 아니다 — 세 채널에 같은 20건을 복제하던 문제의 원인. RADAR handoff_ui 와 같은 규칙.
        scored = frame.sort_values("video_score", ascending=False)
        n = 0
        for r in scored.to_dict("records"):
            if n >= top: break
            if ch not in seed_tags.get(str(r.get("seed")), set()): continue
            k = (str(r["video_id"]), ch)
            if k in keys: continue
            keys.add(k); n += 1
        for (vid, cid) in keys:
            r = by_vid.get(vid)
            if r is None:
                continue  # analysis 에 없는 영상(수집 누락)은 점수를 지어낼 수 없어 뺀다
            stage = ("packaged" if (vid, cid) in packaged else "briefed" if (vid, cid) in briefs
                     else "fit_judged" if (vid, cid) in fit_latest else "scored")
            f = fit_latest.get((vid, cid))
            rows.append({
                "video_id": vid, "channel_id": cid, "stage": stage, "package_id": packaged.get((vid, cid)),
                "seed": s(r.get("seed")),
                "title": s(r.get("title")), "title_ko": s(r.get("title_ko")), "source_channel_name": s(r.get("channel_name")),
                "video_score": num(r.get("video_score")), "opportunity_grade": s(r.get("opportunity_grade")),
                "found_at": s(r.get("found_at")), "published_at": s(r.get("published_at")), "collected_at": s(r.get("collected_at")),
                "age_days": num(r.get("age_days")), "views": num(r.get("views")),
                "metrics": {k: num(r.get(k)) for k in ("video_score", "age_adjusted_percentile", "subscriber_view_ratio", "svr_percentile")},
                "fit": ({"channel_relevance": f.get("channel_relevance"), "audience_fit": f.get("audience_fit"),
                         "money_impact": f.get("money_impact"), "profile_version": f.get("profile_version"),
                         "angle_ko": f.get("angle_ko")} if f else None),
                "has_brief": (vid, cid) in briefs,
            })
    out = {"ok": True, "rows": rows, "n_scored_total": int(len(frame)), "channels": channels}
except Exception as exc:
    out["why"] = f"{type(exc).__name__}: {exc}"
print("\n" + json.dumps(out, ensure_ascii=False, default=str))
"""


def refresh(root: str | Path, *, python: str = "python", top: int = 20) -> dict[str, Any]:
    """RADAR 런타임에서 풀을 다시 내보내 파일로 굳힌다."""
    root = Path(root)
    args = json.dumps({"root": str(root), "top": top})
    try:
        proc = subprocess.run([python, "-X", "utf8", "-c", _RUNNER, args], cwd=str(root),
                              capture_output=True, text=True, encoding="utf-8", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "why": f"RADAR 실행 실패: {exc}"}
    lines = (proc.stdout or "").strip().splitlines()
    if not lines:
        return {"ok": False, "why": f"RADAR 무응답 (exit {proc.returncode}): {(proc.stderr or '')[-300:]}"}
    try:
        res = json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"ok": False, "why": f"RADAR 응답 해석 실패: {lines[-1][:200]}"}
    if not res.get("ok"):
        return res
    doc = {"generated_at": datetime.now(timezone.utc).isoformat(), "top_per_channel": top,
           "n_scored_total": res.get("n_scored_total"), "channels": res.get("channels"), "rows": res["rows"]}
    path = root / REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    stages = {}
    for r in res["rows"]:
        stages[r["stage"]] = stages.get(r["stage"], 0) + 1
    return {"ok": True, "path": str(path), "rows": len(res["rows"]), "stages": stages,
            "n_scored_total": res.get("n_scored_total"), "generated_at": doc["generated_at"]}


def load(root: str | Path | None) -> dict[str, Any] | None:
    if not root:
        return None
    path = Path(root) / REL_PATH
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
