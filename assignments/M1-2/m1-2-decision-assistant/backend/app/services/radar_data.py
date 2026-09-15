"""RADAR 저장소 읽기 전용 접근. DA 가 판단에 쓰는 RADAR 실물을 한 곳에서 읽는다.

여기서 계산하지 않는다. RADAR 가 이미 낸 값(프로필·DNA·channel_fit·패키지 signals·결정 이력)을
그대로 옮긴다. 없는 것은 없다고 돌려준다 — 채워 넣지 않는다.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any


class RadarData:
    def __init__(self, root: str | Path | None) -> None:
        self.root = Path(root) if root else None

    @property
    def available(self) -> bool:
        return bool(self.root and self.root.is_dir())

    def _text(self, rel: str) -> str | None:
        if not self.root:
            return None
        p = self.root / rel
        try:
            return p.read_text(encoding="utf-8-sig") if p.is_file() else None
        except OSError:
            return None

    # ── 채널 프로필 (channels.json — RADAR 가 사람 손으로 관리) ──
    def profiles(self) -> list[dict[str, Any]]:
        text = self._text("data/config/channels.json")
        try:
            return json.loads(text) if text else []
        except json.JSONDecodeError:
            return []

    def profile(self, channel_id: str) -> dict[str, Any] | None:
        return next((p for p in self.profiles() if p.get("id") == channel_id), None)

    # ── 벤치마크 DNA (data/dna/<yt_channel>.json) ──
    def dna_files(self) -> list[dict[str, Any]]:
        if not self.root:
            return []
        out = []
        for p in sorted((self.root / "data" / "dna").glob("*.json")):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8-sig")))
            except (OSError, json.JSONDecodeError):
                continue
        return out

    # ── channel_fit.csv — (video, channel, profile_version) 별 LLM 판정 ──
    def fit_rows(self, video_id: str, channel_id: str) -> list[dict[str, str]]:
        text = self._text("data/processed/channel_fit.csv")
        if not text:
            return []
        return [r for r in csv.DictReader(text.splitlines())
                if r.get("video_id") == video_id and r.get("channel_id") == channel_id]

    # ── outbox 패키지 (최신 revision) — production_signals 전체가 여기 있다 ──
    def latest_package(self, video_id: str, channel_id: str) -> dict[str, Any] | None:
        if not self.root:
            return None
        db = self.root / "data" / "automaker-outbox" / "outbox.sqlite3"
        if not db.is_file():
            return None
        try:
            with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
                rows = conn.execute("SELECT body FROM packages ORDER BY revision DESC").fetchall()
        except sqlite3.Error:
            return None
        for (body,) in rows:
            try:
                env = json.loads(body)
            except (TypeError, json.JSONDecodeError):
                continue
            p = env.get("payload") or {}
            if p.get("opportunity_id") == video_id and (p.get("target_channel") or {}).get("id") == channel_id:
                return env
        return None

    # ── 브리프 (data/briefs/<channel>/<video>.md) ──
    def brief(self, channel_id: str, video_id: str, limit: int = 2500) -> str | None:
        text = self._text(f"data/briefs/{channel_id}/{video_id}.md")
        return text[:limit] if text else None

    # ── videos.csv 한 행 ──
    def video_row(self, video_id: str) -> dict[str, str] | None:
        text = self._text("data/raw/videos.csv")
        if not text:
            return None
        return next((r for r in csv.DictReader(text.splitlines()) if r.get("video_id") == video_id), None)

    # ── 성과 (있으면). RADAR outcomes 의 입력 파일들 — 지금은 비어 있다 ──
    def performance_rows(self) -> list[dict[str, str]]:
        text = self._text("data/raw/own_snapshots.csv")
        return list(csv.DictReader(text.splitlines())) if text else []
