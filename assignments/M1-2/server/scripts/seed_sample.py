"""표본 모드 seed(T06.03, PRD §11.3, docs/decisions.md).

- 숫자 표본: 2026-08-02~2026-09-30(60일) × `received_count`·`kept_count` = 120건. 고정 seed라 늘 같은 값이다.
  표본 자료 개수와 맞추지 않는 독립 시계열이다. 마지막 7일은 추세가 보이도록 조금 높다.
- 채팅 근거 자료: `server/tests/fixtures/sample_materials.json`의 20건을 보관 승인·보관 완료·활성으로 만든다.
  접수 기록과 같은 URL 예약도 실제 자료와 같은 구조로 만든다.
- 표본 모드에만 쓰고 개인 모드는 읽지도 쓰지 않는다. PC 작업 기록은 만들지 않는다.
- 재실행: 처음 끝날 때 완료 표시(`settings/sample_seed`)를 남긴다. 완료 표시가 있으면 아무것도 만들지 않고
  남아 있는·바뀐·지워진 표본 수만 알린다(사용자가 CRUD로 바꾸거나 지운 표본을 되돌리지 않는다).
  완료 표시 전에 중단됐다면 다시 실행할 때 없는 것만 만든다.

실행: `.\\.venv\\Scripts\\python.exe server/scripts/seed_sample.py` (서버 `.env`의 OWNER_UID·Firebase 설정 사용)
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.context import RequestContext  # noqa: E402
from app.core.firestore import NotFound, Store, VersionConflict, now_utc  # noqa: E402
from app.features.materials.service import COLLECTION, INTAKE, URL_INDEX, _new_material_doc  # noqa: E402
from app.features.materials.url_keys import url_index_id, url_key  # noqa: E402

SEED_VERSION = "2026-10-02.1"
MARKER_ID = "sample_seed"
START = date(2026, 8, 2)
DAYS = 60
RNG_SEED = 20261002
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "sample_materials.json"


def data_id(metric: str, day: str) -> str:
    return f"sample-{metric}-{day}"


def sample_numbers() -> list[dict]:
    """60일 × 2지표. 날마다 보관 수 ≤ 접수 수. 마지막 7일은 1~2건 더 많다."""
    rng = random.Random(RNG_SEED)
    rows = []
    for i in range(DAYS):
        day = (START + timedelta(days=i)).isoformat()
        boost = 2 if i >= DAYS - 7 else 0
        received = rng.randint(2, 6) + boost
        kept = max(0, min(received, received - rng.randint(0, 2) + boost // 2))
        rows.append({"date": day, "metric_type": "received_count", "value": received, "memo": "가상 표본"})
        rows.append({"date": day, "metric_type": "kept_count", "value": kept, "memo": "가상 표본"})
    return rows


def sample_materials() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["materials"]


def _material_items(ctx: RequestContext, item: dict) -> list[tuple]:
    doc = _new_material_doc(item, item["registered_at"])
    doc.update(review_status="approved", storage_approved_at=item["registered_at"], sample_seed=SEED_VERSION)
    items = [(COLLECTION, doc, item["id"]),
             (INTAKE, {"material_id": item["id"], "received_at": item["registered_at"]}, item["id"])]
    if item.get("url"):
        key = url_key(item["url"])
        items.append((URL_INDEX, {"url_key": key, "material_id": item["id"]}, url_index_id(ctx.owner_id, ctx.mode, key)))
    return items


def _exists(store: Store, ctx: RequestContext, collection: str, doc_id: str) -> dict | None:
    try:
        return store.get(ctx, collection, doc_id)
    except NotFound:
        return None


def _report_existing(store: Store, ctx: RequestContext, marker: dict) -> dict:
    present = changed = 0
    numbers = sample_numbers()
    for row in numbers:
        doc = _exists(store, ctx, "data", data_id(row["metric_type"], row["date"]))
        if doc:
            present += 1
            changed += doc.get("value") != row["value"] or doc.get("date") != row["date"]
    materials = sample_materials()
    materials_present = sum(1 for m in materials if _exists(store, ctx, COLLECTION, m["id"]))
    return {"status": "already_seeded", "seed_version": marker.get("seed_version"), "data_present": present,
            "data_changed": changed, "data_missing": len(numbers) - present,
            "materials_present": materials_present, "materials_missing": len(materials) - materials_present}


def seed(store: Store, owner_id: str) -> dict:
    ctx = RequestContext(owner_id, "sample", None)  # 표본 모드에만 쓴다
    marker = _exists(store, ctx, "settings", MARKER_ID)
    if marker:
        return _report_existing(store, ctx, marker)

    data_created = 0
    for row in sample_numbers():
        try:
            store.create(ctx, "data", {**row, "origin": "sample"}, doc_id=data_id(row["metric_type"], row["date"]))
            data_created += 1
        except VersionConflict:
            pass  # 중단된 이전 실행이 이미 만들었다
    materials_created = 0
    for item in sample_materials():
        try:
            store.create_many(ctx, _material_items(ctx, item))  # 자료·접수 기록·URL 예약을 함께
            materials_created += 1
        except VersionConflict:
            pass
    store.create(ctx, "settings", {"seed_version": SEED_VERSION, "data_count": len(sample_numbers()),
                                   "material_count": len(sample_materials()), "seeded_at": now_utc()},
                 doc_id=MARKER_ID)
    return {"status": "seeded", "seed_version": SEED_VERSION, "data_created": data_created,
            "materials_created": materials_created}


def main() -> int:
    from app.core.config import ConfigError, load_settings
    from app.core.firestore import FirestoreStore

    settings = load_settings()
    try:
        settings.require("firebase")
        store = FirestoreStore.from_settings(settings)
    except ConfigError:
        print(json.dumps({"status": "error", "error": "missing_firebase_settings"}))
        return 1
    print(json.dumps(seed(store, settings.get("OWNER_UID")), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
