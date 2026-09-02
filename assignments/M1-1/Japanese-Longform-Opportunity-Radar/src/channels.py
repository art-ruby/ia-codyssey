# -*- coding: utf-8 -*-
"""채널 프로필 — 두 채널(돈·노후 / 집·상속)의 정체성을 한 곳에 둔다.

    data/config/channels.json

를 읽는다. 다른 모듈은 이 파일을 직접 열지 않고 아래 네 함수만 쓴다 —
storage.py 가 CSV 읽기·쓰기를 도맡는 것과 같은 이유다.

근거: Claude_Code_전달용_..._최종지시서.md §6, §61~65
      docs/specs/2026-09-02-channel-profile-seed-migration-design.md
"""
import json

from . import config

CHANNELS_JSON = config.ROOT / "data" / "config" / "channels.json"


def _load():
    """전체 채널 레코드. 파일이 없거나 JSON이 깨졌으면 빈 리스트 —
    channels.json 문제로 앱 전체가 죽으면 안 된다."""
    if not CHANNELS_JSON.exists():
        return []
    try:
        data = json.loads(CHANNELS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def records():
    """전체 채널 프로필."""
    return _load()


def get(channel_id):
    """단일 채널. 없으면 None."""
    return next((c for c in records() if c.get("id") == channel_id), None)


def enabled_for_discovery():
    """discovery_enabled=true 인 채널만 — Radar 탐색 대상."""
    return [c for c in records() if c.get("discovery_enabled")]


def enabled_for_production():
    """production_enabled=true 인 채널만 — 실제 업로드 채널."""
    return [c for c in records() if c.get("production_enabled")]
