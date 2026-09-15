"""Channel Fit 상태 모델 — «미평가를 점수가 덮어쓰지 않는다».

RADAR `channel_fit.csv` 는 (video, channel, profile_version) 마다 LLM 판정 한 줄이다.
프로필 버전이 오르면 RADAR 는 옛 판정을 버린다(not_available). 그 자체는 옳다 — 다만 DA 가 그
빈자리를 점수로 채우면 안 된다. 그래서 상태를 명시하고, 필요할 때 **RADAR 의 judge 를 RADAR
런타임에서 다시 부른다.** DA 가 적합성을 계산하지 않는다.

  VALID          현재 profile_version 행 있음 → 사용
  STALE          옛 버전 행만 있음 → 재판정 (basis 해시가 같으면 stale_reason=version_only 로 기록)
  NOT_EVALUATED  행 없음 → 재판정
  INVALID        행 있으나 판정 필드 결손 → 재판정
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .radar_data import RadarData

# RADAR prompts/channel_fit 이 실제로 읽는 프로필 필드 (src/channel_fit.py:judge). 이 값이 그대로면
# 버전만 올라도 판정 근거는 같다 — 그 사실을 stale_reason 에 남긴다.
BASIS_FIELDS = ("name_ko", "audience", "promise_ko", "core_question_ko", "lenses")
LEVEL_FIELDS = ("audience_fit", "channel_relevance", "money_impact", "problem_strength",
                "longform_potential", "news_risk", "evergreen_potential")


def basis_hash(profile: dict[str, Any]) -> str:
    blob = json.dumps({k: profile.get(k) for k in BASIS_FIELDS}, ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def evaluate(data: RadarData, video_id: str, channel_id: str) -> dict[str, Any]:
    profile = data.profile(channel_id) or {}
    current = str(profile.get("profile_version", 1))
    rows = data.fit_rows(video_id, channel_id)
    out: dict[str, Any] = {
        "state": "NOT_EVALUATED", "profile_version": int(current) if current.isdigit() else current,
        "evaluated_at": None, "evaluated_profile_version": None,
        "evaluation_basis": basis_hash(profile) if profile else None, "stale_reason": None,
    }
    if not rows:
        return out
    # 같은 버전 중 마지막 줄이 최신 판정. 없으면 가장 최근 줄(옛 버전).
    same = [r for r in rows if str(r.get("profile_version")) == current]
    row = (same or rows)[-1]
    out["evaluated_at"] = row.get("analyzed_at")
    out["evaluated_profile_version"] = row.get("profile_version")
    for k in LEVEL_FIELDS:
        out[k] = (row.get(k) or "").strip() or None
    out["reason"] = row.get("reason")
    out["angle_ko"] = row.get("angle_ko")
    if not same:
        out["state"] = "STALE"
        # 옛 판정 시점의 프로필은 남아 있지 않다. 근거가 같은지는 알 수 없으므로 version_changed 로 둔다.
        out["stale_reason"] = f"profile_version {row.get('profile_version')} → {current}"
        return out
    missing = [k for k in ("audience_fit", "channel_relevance", "money_impact") if not out.get(k)]
    out["state"] = "INVALID" if missing else "VALID"
    if missing:
        out["stale_reason"] = "필드 결손: " + ", ".join(missing)
    return out


# RADAR 런타임에서 실행. channel_fit.judge 는 analysis.build() 의 행을 요구한다.
_RUNNER = r"""
import json, sys
args = json.loads(sys.argv[1])
sys.path.insert(0, args["root"])
out = {"ok": False}
try:
    from src import analysis, channel_fit, config
    frame = analysis.build(config.ROOT)
    hit = frame[frame["video_id"].astype(str) == args["video_id"]]
    if hit.empty:
        out["why"] = "analysis 에 이 영상이 없습니다 (videos.csv 확인)"
    else:
        r = channel_fit.judge(args["video_id"], args["channel_id"], hit.iloc[0].to_dict(), force=args.get("force", False))
        out.update({k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)) for k, v in r.items()})
        out["ok"] = bool(r.get("ok"))
except Exception as exc:
    out["why"] = f"{type(exc).__name__}: {exc}"
print("\n" + json.dumps(out, ensure_ascii=False, default=str))
"""


def reevaluate_in_radar(root: str | Path, video_id: str, channel_id: str, *, python: str = "python",
                        force: bool = True) -> dict[str, Any]:
    """RADAR channel_fit.judge(force) — RADAR 의 프롬프트·모델·CSV 로. 결과 행을 돌려준다."""
    args = json.dumps({"root": str(root), "video_id": video_id, "channel_id": channel_id, "force": force})
    try:
        proc = subprocess.run([python, "-X", "utf8", "-c", _RUNNER, args], cwd=str(root),
                              capture_output=True, text=True, encoding="utf-8", timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "why": f"RADAR 실행 실패: {exc}"}
    lines = (proc.stdout or "").strip().splitlines()
    if not lines:
        return {"ok": False, "why": f"RADAR 무응답 (exit {proc.returncode}): {(proc.stderr or '')[-300:]}"}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return {"ok": False, "why": f"RADAR 응답 해석 실패: {lines[-1][:200]}"}
