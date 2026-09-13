"""RADAR `data/decisions.jsonl` 에 결정을 쓴다 — 결정의 단일 정본.

왜 DA 자체 저장이 아니라 RADAR 파일인가 (2026-09-11 감사 §H·§Q):
  · RADAR `automaker_intake.package()` 가 이 파일의 마지막 줄을 `payload.decision` 으로
    실어 AutoMaker 에 보낸다. 여기 쓰면 별도 채널 없이 AutoMaker 까지 닿는다.
  · RADAR `outcomes.build()` 가 같은 키 (video_id, channel_id) 로 성과와 맞댄다.
  · DA 메모리 저장소는 재시작하면 사라진다. 이 파일은 남는다.

형식은 RADAR `src/decisions.py:freeze()` 와 **같은 키·같은 규칙**을 쓴다:
  · append-only. 마음이 바뀌면 새 줄.
  · revision  = 같은 (video_id, channel_id) 의 기존 줄 수 기준 +1
  · decision_id = 'dec_' + sha256(json.dumps([channel_id, video_id, revision],
                                  ensure_ascii=False, separators=(',',':')))[:32]
  · 잠금 파일 `decisions.jsonl.lock` — RADAR 와 같은 프로세스 간 잠금 프로토콜.

RADAR 의 freeze() 는 analysis 행 전체를 얼리지만 DA 는 그 행이 없다. DA 가 가진
«그때 본 숫자» 는 RADAR 패키지(payload_hash 로 고정된) 의 production_signals 다.
그래서 metrics 는 패키지에서 옮기고, code_version/config_digest 자리에는 지어내지 않고
`producer: decision-assistant` + `package_id` + `payload_hash` 를 남긴다.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = ("MAKE", "WATCH", "SKIP")
PRODUCER = "decision-assistant"
_LOCK = threading.RLock()


def decision_id_for(channel_id: str, video_id: str, revision: int) -> str:
    """RADAR decisions.py 와 바이트 단위로 같은 식. 바꾸면 두 시스템의 id 가 갈린다."""
    identity = json.dumps([channel_id, video_id, revision], ensure_ascii=False, separators=(",", ":"))
    return "dec_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]


class DecisionsLedger:
    REL_PATH = Path("data") / "decisions.jsonl"

    def __init__(self, root: str | Path | None, *, enabled: bool) -> None:
        self.root = Path(root) if root else None
        self.enabled = bool(enabled and self.root)

    @property
    def path(self) -> Path | None:
        return (self.root / self.REL_PATH) if self.root else None

    # ── 읽기 ──────────────────────────────────────
    def records(self) -> list[dict[str, Any]]:
        path = self.path
        if path is None or not path.is_file():
            return []
        out: list[dict[str, Any]] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # 한 줄이 깨져도 나머지는 살린다 (RADAR 와 같은 태도)
        return out

    def latest_by_key(self) -> dict[tuple[str, str], dict[str, Any]]:
        """(video_id, channel_id) → 마지막 줄. RADAR latest()/automaker_intake 와 같은 규칙."""
        by: dict[tuple[str, str], dict[str, Any]] = {}
        for r in self.records():
            if isinstance(r, dict):
                by[(str(r.get("video_id") or ""), str(r.get("channel_id") or ""))] = r
        return by

    # ── 쓰기 ──────────────────────────────────────
    @contextmanager
    def _writer(self):
        path = self.path
        assert path is not None
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(path) + ".lock", "a+b") as lock:
                if os.name == "nt":
                    import msvcrt

                    if lock.tell() == 0:
                        lock.write(b"0")
                        lock.flush()
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    if os.name == "nt":
                        lock.seek(0)
                        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        fcntl.flock(lock, fcntl.LOCK_UN)

    def append(
        self, candidate: dict[str, Any], decision: str, note: str = ""
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """(썼는가, 이유, 레코드). 쓰지 않은 이유는 숨기지 않고 돌려준다."""
        if not self.enabled:
            return False, "RADAR_DECISIONS_WRITE 가 꺼져 있어 RADAR 에 기록하지 않았습니다.", None
        source = getattr(candidate.get("source"), "value", candidate.get("source"))
        if source != "radar":
            return False, f"[{source}] 후보는 RADAR 실측이 아니므로 RADAR 원장에 쓰지 않습니다.", None
        video_id = str(candidate.get("radar_id") or "")
        channel_id = str(candidate.get("channel") or "")
        if not video_id or not channel_id:
            return False, "radar_id 또는 channel 이 없어 RADAR 키를 만들 수 없습니다.", None
        if decision not in VALID:
            return False, "MAKE / WATCH / SKIP 중 하나여야 합니다.", None

        now = datetime.now(timezone.utc).isoformat()
        metrics = dict(candidate.get("radar_metrics") or {})
        if "video_score" not in metrics and candidate.get("radar_score") is not None:
            metrics["video_score"] = candidate.get("radar_score")
        rec: dict[str, Any] = {
            "video_id": video_id,
            "channel_id": channel_id,
            "frozen_at": now,
            "decided_at": now,
            # RADAR freeze() 가 채우는 두 칸 — DA 는 그 값을 모른다. 지어내지 않는다.
            "code_version": "",
            "config_digest": None,
            "producer": PRODUCER,
            "package_id": candidate.get("radar_package_id"),
            "payload_hash": candidate.get("radar_payload_hash"),
            "da_candidate_id": candidate.get("id"),
            "title": candidate.get("title"),
            "metrics": metrics,
            "population": {},
            "note": note or "",
            "decision": decision,
            "signals": {},
        }
        with self._writer():
            previous = [
                r for r in self.records()
                if isinstance(r, dict)
                and r.get("video_id") == video_id
                and r.get("channel_id") == channel_id
            ]
            rec["revision"] = max([len(previous)] + [int(r.get("revision") or 0) for r in previous]) + 1
            rec["decision_id"] = decision_id_for(channel_id, video_id, rec["revision"])
            line = json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n"
            with open(self.path, "a", encoding="utf-8") as f:  # type: ignore[arg-type]
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
        return True, f"RADAR decisions.jsonl 에 기록 — {rec['decision_id']} (rev {rec['revision']})", rec
