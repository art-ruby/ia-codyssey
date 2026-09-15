"""RADAR 제작 브리프 생성 호출 — DA 가 쓰지 않고 RADAR 의 production_brief 를 부른다.

RADAR handoff_ui.py:76 의 순서를 그대로 따른다:
  comments.fetch(video) → comments.analyze(video, row) → production_brief.build(video, channel)
build() 는 «조립만» 한다 — 판정(channel_fit)·댓글 해석은 기존 결과를 재사용하고 새 LLM 을 부르지 않는다.
결과 파일은 RADAR `data/briefs/<channel>/<video>.md`. 이것이 있어야 automaker_intake.package() 가 된다.

RADAR 의 규칙 하나를 그대로 지킨다: 채널 관련성 LOW 면 브리프를 만들지 않는다(예외 검토는 RADAR UI 에서).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

_RUNNER = r"""
import json, sys
args = json.loads(sys.argv[1]); sys.path.insert(0, args["root"])
out = {"ok": False, "steps": {}}
try:
    from src import analysis, config, comments, production_brief, channel_fit, channels
    vid, cid = args["video_id"], args["channel_id"]
    frame = analysis.build(config.ROOT)
    hit = frame[frame["video_id"].astype(str) == vid]
    if hit.empty:
        out["why"] = "analysis 에 이 영상이 없습니다"; raise SystemExit
    row = hit.iloc[0]
    prof = channels.get(cid) or {}
    fit = channel_fit.cached(vid, cid, prof.get("profile_version", 1))
    if fit and fit.get("channel_relevance") == "LOW":
        out["why"] = "채널 관련성 LOW — RADAR 규칙대로 브리프를 만들지 않습니다(예외 검토는 RADAR UI)."
        out["gate"] = "relevance_low"; raise SystemExit
    if args.get("with_comments", True):
        c = comments.fetch(vid)
        out["steps"]["comments_fetch"] = {"status": c.get("status"), "why": c.get("why")}
        if c.get("status") == "ok":
            a = comments.analyze(vid, row)
            out["steps"]["comments_analyze"] = {"ok": bool((a or {}).get("ok", a is not None)),
                                                 "why": (a or {}).get("why") if isinstance(a, dict) else None}
    r = production_brief.build(vid, cid)
    out["steps"]["brief_build"] = {"ok": bool(r.get("ok")), "why": r.get("why")}
    if r.get("ok"):
        out.update({"ok": True, "path": r.get("path"), "chars": len(r.get("text") or ""),
                    "fit": {k: (r.get("fit") or {}).get(k) for k in ("channel_relevance", "audience_fit", "money_impact", "angle_ko")}})
    else:
        out["why"] = r.get("why") or "브리프 생성 실패"
except SystemExit:
    pass
except Exception as exc:
    out["why"] = f"{type(exc).__name__}: {exc}"
print("\n" + json.dumps(out, ensure_ascii=False, default=str))
"""


def build_in_radar(root: str | Path, video_id: str, channel_id: str, *, python: str = "python",
                   with_comments: bool = True) -> dict[str, Any]:
    args = json.dumps({"root": str(root), "video_id": video_id, "channel_id": channel_id, "with_comments": with_comments})
    try:
        proc = subprocess.run([python, "-X", "utf8", "-c", _RUNNER, args], cwd=str(root),
                              capture_output=True, text=True, encoding="utf-8", timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "why": f"RADAR 실행 실패: {exc}"}
    lines = (proc.stdout or "").strip().splitlines()
    if not lines:
        return {"ok": False, "why": f"RADAR 무응답 (exit {proc.returncode}): {(proc.stderr or '')[-300:]}"}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"ok": False, "why": f"RADAR 응답 해석 실패: {lines[-1][:200]}"}
