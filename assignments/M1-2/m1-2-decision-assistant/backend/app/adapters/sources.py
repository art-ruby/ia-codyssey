"""후보 데이터 소스 어댑터.

명세 14절: 실제 RADAR 연결이 바로 안 되면 표본으로 먼저 요건을 채우되,
표본과 실데이터를 코드와 화면에서 구분할 수 있어야 하고, 나중에 소스만
바꾸면 되도록 한다. 그래서 두 구현이 같은 dict 모양을 돌려주고,
모든 레코드에 source 필드를 강제로 붙인다.

RADAR 저장소는 **읽기만** 한다. 명세 12절에 따라 RADAR 수집·점수 로직을
건드리지 않으며, 점수를 새로 계산하지도 않는다 — RADAR 가 이미 만든 값만
옮긴다. 값이 없으면 지어내지 않고 그 후보를 건너뛴다.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from collections import Counter
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_DECISIONS = {"MAKE", "WATCH", "SKIP"}


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _clamp_score(value: Any) -> float | None:
    """점수는 0~100 으로만 받는다. 범위를 벗어나면 보정하지 않고 버린다."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if 0.0 <= number <= 100.0 else None


class CandidateSource(ABC):
    """모든 소스가 같은 계약을 지킨다: load() 는 저장 가능한 dict 목록을 준다."""

    name: str = "abstract"

    @abstractmethod
    def load(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def describe(self) -> dict[str, Any]:
        """화면과 /api/health 가 '지금 무엇을 보고 있는지' 알리도록 한다."""


class SampleSource(CandidateSource):
    """sample_data/candidates.json 을 읽는다. 형태는 RADAR 를 모사하되 sample 로 표시된다."""

    name = "sample"

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        records = raw.get("candidates", raw) if isinstance(raw, dict) else raw
        out: list[dict[str, Any]] = []
        for item in records:
            date = _parse_dt(item.get("date"))
            score = _clamp_score(item.get("value", item.get("radar_score")))
            if date is None or score is None:
                continue
            decision = item.get("decision")
            out.append(
                {
                    "date": date,
                    "value": score,
                    "memo": (item.get("memo") or "")[:500],
                    "radar_id": item.get("radar_id"),
                    "channel": item.get("channel"),
                    "topic": item.get("topic"),
                    "title": item.get("title"),
                    "radar_score": _clamp_score(item.get("radar_score", score)),
                    "decision": decision if decision in VALID_DECISIONS else None,
                    "decision_reason": (item.get("decision_reason") or "")[:1000],
                    # 표본임을 소스가 직접 못박는다. 파일 내용이 뭐라 하든 여기서 덮어쓴다.
                    "source": "sample",
                }
            )
        return out

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": self.path.is_file(),
            "path": str(self.path),
            "is_real_data": False,
            "note": "RADAR 형태를 모사한 표본이다. 실제 관측이 아니다.",
        }


class RadarSource(CandidateSource):
    """실제 RADAR 저장소를 읽는다(읽기 전용).

    우선순위:
      1) outbox/*.json  — AutoMaker 로 보낸 패키지. payload 에 점수·결정이 함께 있다.
      2) data/decisions.jsonl — 사용자가 남긴 결정 이벤트(당시 metrics 포함).

    둘 다 없으면 빈 목록을 준다. 점수를 새로 계산해 채우지 않는다.
    """

    name = "radar"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root) if root else None
        # 왜 후보가 안 나왔는지 남긴다. 표시 없이 0건만 주면 원인을 알 수 없다.
        self._skipped: Counter[str] = Counter()

    # ── 내부 파서 ─────────────────────────────────
    def _titles(self) -> dict[str, str]:
        """videos.csv 에서 video_id → title 만 가져온다. 없으면 빈 map."""
        if self.root is None:
            return {}
        path = self.root / "data" / "raw" / "videos.csv"
        if not path.is_file():
            return {}
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            return {}
        return {
            row["video_id"]: (row.get("title") or "").strip()
            for row in csv.DictReader(text.splitlines())
            if row.get("video_id")
        }

    # RADAR 가 AutoMaker 로 보내는 패키지의 실제 저장소. 2026-09-11 감사(§G-3)에서
    # 이 어댑터가 `{root}/outbox/*.json` 을 기대하는 동안 RADAR 실물은 여기였다.
    OUTBOX_DB = Path("data") / "automaker-outbox" / "outbox.sqlite3"

    def _iter_envelopes(self):
        """RADAR 패키지 봉투를 차례로 낸다. sqlite 실물이 있으면 그것만 읽는다.

        테이블은 packages(id, revision, body). 같은 id 의 여러 revision 은 오름차순으로
        나오므로 호출자가 «나중 것이 이긴다» 로 덮어쓰면 최신 revision 이 남는다.
        json 디렉터리는 RADAR 에 없지만 픽스처·수동 투입용으로 남겨 둔다.
        """
        db = self.root / self.OUTBOX_DB
        if db.is_file():
            try:
                with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
                    rows = conn.execute(
                        "SELECT body FROM packages ORDER BY id, revision"
                    ).fetchall()
            except sqlite3.Error as exc:
                self._skipped[f"outbox.sqlite3 읽기 실패: {exc}"] += 1
                return
            for (body,) in rows:
                try:
                    yield json.loads(body)
                except (TypeError, json.JSONDecodeError):
                    self._skipped["outbox.sqlite3 body 가 JSON 이 아님"] += 1
            return
        outbox = self.root / "outbox"
        if not outbox.is_dir():
            return
        for path in sorted(outbox.glob("*.json")):
            try:
                yield json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue

    def _from_outbox(self, titles: dict[str, str]) -> list[dict[str, Any]]:
        found: dict[str, dict[str, Any]] = {}
        for envelope in self._iter_envelopes():
            payload = envelope.get("payload") if isinstance(envelope, dict) else None
            if not isinstance(payload, dict):
                continue
            record = self._from_payload(payload, envelope, titles)
            if record and record["radar_id"]:
                # 같은 소재의 여러 revision 중 나중 것이 이긴다. 키는 (영상, 채널) — 한 영상이 두 채널의 후보일 수 있다.
                record["radar_stage"] = "packaged"
                found[(record["radar_id"], record.get("channel") or "")] = record
        return list(found.values())

    def _from_pool(self, existing: dict[tuple[str, str], dict[str, Any]], titles: dict[str, str]) -> list[dict[str, Any]]:
        """candidate_pool.json — RADAR 깔때기의 판정·브리프·점수 상위 단계. 패키지와 겹치면 패키지가 이긴다."""
        from ..services.radar_pool import load as load_pool

        pool = load_pool(self.root)
        if not pool:
            return []
        out = []
        for row in pool.get("rows") or []:
            key = (str(row.get("video_id") or ""), str(row.get("channel_id") or ""))
            if not key[0] or key in existing:
                continue
            score = _clamp_score(row.get("video_score"))
            date = _parse_dt(row.get("found_at")) or _parse_dt(row.get("collected_at")) or _parse_dt(row.get("published_at"))
            if score is None or date is None:
                self._skipped["풀 행에 점수/시점 없음"] += 1
                continue
            metrics = {k: v for k, v in (row.get("metrics") or {}).items() if v is not None}
            out.append({
                "date": date, "value": score, "memo": "",
                "radar_id": key[0], "channel": key[1],
                "topic": row.get("title_ko") or row.get("title"),
                "title": titles.get(key[0]) or row.get("title"),
                "radar_score": score, "radar_package_id": row.get("package_id"), "radar_payload_hash": None,
                "radar_metrics": metrics or {"video_score": score},
                "radar_stage": row.get("stage") or "scored",
                "decision": None, "decision_reason": "", "source": "radar",
            })
        return out

    def _from_payload(
        self, payload: dict[str, Any], envelope: dict[str, Any], titles: dict[str, str]
    ) -> dict[str, Any] | None:
        radar_id = payload.get("opportunity_id")
        if not radar_id:
            self._skipped["opportunity_id 없음"] += 1
            return None
        if int(envelope.get("schema_version") or 0) < 2:
            # v1 envelope 에는 demand/discovery 가 아예 없다. 점수를 지어낼 수
            # 없으므로 건너뛰되, v1 이라서 건너뛴 것임을 분명히 남긴다.
            self._skipped["schema_version 1 — 점수·시점 필드 없음 (v2 필요)"] += 1
            return None
        # RADAR v2 실물은 demand/discovery 를 payload.production_signals 아래에 둔다
        # (production_signals.py:74-77). 최상위 demand/discovery 는 초기 픽스처 형태 —
        # 실물이 없을 때만 본다. 두 자리를 모두 보되 실물을 먼저 본다.
        signals = payload.get("production_signals") or {}
        demand = signals.get("demand") or payload.get("demand") or {}
        discovery = signals.get("discovery") or payload.get("discovery") or {}
        decision_block = payload.get("decision") or {}
        metrics = decision_block.get("metrics") or {}
        # RADAR 가 계산해 둔 점수만 쓴다. 먼저 있는 것.
        score = (
            _clamp_score(demand.get("video_score"))
            or _clamp_score(metrics.get("video_score"))
            or _clamp_score(signals.get("video_score"))
        )
        if score is None:
            self._skipped['RADAR 점수(video_score) 없음'] += 1
            return None
        date = (
            _parse_dt(discovery.get("observed_at"))
            or _parse_dt(discovery.get("collected_at"))
            or _parse_dt(discovery.get("found_at"))
            or _parse_dt(envelope.get("created_at"))
        )
        if date is None:
            self._skipped['관측 시점 없음'] += 1
            return None
        decision = decision_block.get("decision")
        target = payload.get("target_channel") or {}
        # 결정 원장(decisions.jsonl)에 «그때 본 숫자» 로 남길 값. RADAR freeze() 의 FROZEN 가운데
        # 패키지에 실제로 있는 것만 — 없는 칸을 0 으로 채우지 않는다.
        components = demand.get("components") or {}
        metrics = {"video_score": score}
        for key in ("age_adjusted_percentile", "subscriber_view_ratio", "svr_percentile"):
            if components.get(key) is not None:
                metrics[key] = components[key]
        return {
            "date": date,
            "value": score,
            "memo": (payload.get("rationale") or "")[:500],
            "radar_id": radar_id,
            "channel": target.get("id"),
            "topic": payload.get("topic"),
            "title": titles.get(radar_id) or payload.get("topic"),
            "radar_score": score,
            "radar_package_id": envelope.get("package_id"),
            "radar_payload_hash": envelope.get("payload_hash"),
            "radar_metrics": metrics,
            "decision": decision if decision in VALID_DECISIONS else None,
            "decision_reason": (decision_block.get("note") or "")[:1000],
            "source": "radar",
        }

    def _from_decisions(self, titles: dict[str, str]) -> list[dict[str, Any]]:
        path = self.root / "data" / "decisions.jsonl"
        if not path.is_file():
            return []
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            return []
        latest: dict[str, dict[str, Any]] = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            radar_id = event.get("video_id")
            score = _clamp_score((event.get("metrics") or {}).get("video_score"))
            date = _parse_dt(event.get("decided_at") or event.get("frozen_at"))
            if not radar_id or score is None or date is None:
                continue
            decision = event.get("decision")
            latest[radar_id] = {
                "date": date,
                "value": score,
                "memo": (event.get("note") or "")[:500],
                "radar_id": radar_id,
                "channel": event.get("channel_id"),
                "topic": event.get("topic"),
                "title": titles.get(radar_id) or event.get("topic"),
                "radar_score": score,
                "decision": decision if decision in VALID_DECISIONS else None,
                "decision_reason": (event.get("note") or "")[:1000],
                "source": "radar",
            }
        return list(latest.values())

    def _overlay_ledger(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """decisions.jsonl 의 마지막 줄이 결정의 정본이다.

        패키지 안의 payload.decision 은 패키징 «시점» 의 스냅샷이라, 그 뒤 DA 가 내린
        결정은 원장에만 있다. 원장이 있으면 원장이 이긴다. 서버를 재시작해도 결정이
        사라지지 않는 이유가 이 한 줄이다.
        """
        from ..services.decisions_ledger import DecisionsLedger

        latest = DecisionsLedger(self.root, enabled=False).latest_by_key()
        if not latest:
            return records
        for rec in records:
            hit = latest.get((str(rec.get("radar_id") or ""), str(rec.get("channel") or "")))
            if not hit:
                continue
            decision = hit.get("decision")
            if decision in VALID_DECISIONS:
                rec["decision"] = decision
                rec["decision_reason"] = (hit.get("note") or "")[:1000]
        return records

    def load(self) -> list[dict[str, Any]]:
        self._skipped.clear()
        if self.root is None or not self.root.is_dir():
            return []
        titles = self._titles()
        records = self._from_outbox(titles)
        existing = {(r["radar_id"], r.get("channel") or ""): r for r in records}
        records += self._from_pool(existing, titles)
        if records:
            return self._overlay_ledger(records)
        return self._from_decisions(titles)

    def describe(self) -> dict[str, Any]:
        if self.root is None:
            return {"name": self.name, "available": False, "path": None, "is_real_data": True,
                    "note": "RADAR_ROOT 가 설정되지 않았다."}
        outbox_db = (self.root / self.OUTBOX_DB).is_file()
        outbox_dir = (self.root / "outbox").is_dir()
        decisions = (self.root / "data" / "decisions.jsonl").is_file()
        pool = (self.root / "data" / "decision_assistant" / "candidate_pool.json").is_file()
        return {
            "name": self.name,
            "available": self.root.is_dir() and (outbox_db or outbox_dir or decisions or pool),
            "has_pool": pool,
            "path": str(self.root),
            "is_real_data": True,
            "has_outbox": outbox_db or outbox_dir,
            "outbox_backend": "sqlite" if outbox_db else "json-dir" if outbox_dir else None,
            "has_decisions": decisions,
            "note": "RADAR 가 계산한 점수만 읽는다. 없으면 후보를 만들지 않는다.",
            "skipped": dict(self._skipped),
        }


def build_source(name: str, settings) -> CandidateSource:
    """이름으로 소스를 고른다. 실제 RADAR 로 갈아탈 때 바꾸는 지점은 여기 하나뿐이다."""
    if name == "radar":
        return RadarSource(settings.radar_root)
    return SampleSource(settings.sample_data_path)
