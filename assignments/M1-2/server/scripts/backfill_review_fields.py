"""T03.03: 검토 필드가 없는 기존 자료에 기본값을 채운다(T03.01·T03.02 때 만든 자료).

받은 자료·승인 요청 목록은 `review_requested` 같음 조건으로 조회하므로, 이 필드가 없는 문서는 두 목록
어디에도 보이지 않는다. 없는 필드만 채운다: `review_requested=False`, `review_requested_at=None`,
`user_importance=None`, `revisit_on=None`(T03.04). 이미 있는 값·내용·버전은 바꾸지 않는다(사용자가 바꾼 것이 아니므로 버전을 올리지 않는다).
읽은 뒤 다른 곳에서 바뀐 문서는 덮어쓰지 않고 건너뛴다(마지막 수정 시각 전제 조건).

기본은 개수만 세는 시험 실행이다. `--apply`를 붙여야 쓴다. `--mode`로 한 모드만 고를 수 있다.
출력에는 모드별 개수만 남기고 문서 내용·ID는 출력하지 않는다.

실행: `M1-2` 폴더에서 `.\\.venv\\Scripts\\python.exe server/scripts/backfill_review_fields.py [--mode sample] [--apply]`
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import load_settings  # noqa: E402
from app.core.firestore import firebase_app  # noqa: E402

DEFAULTS = {"review_requested": False, "review_requested_at": None, "user_importance": None, "revisit_on": None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("personal", "sample"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    from firebase_admin import firestore
    from google.api_core.exceptions import FailedPrecondition
    from google.cloud.firestore_v1 import FieldFilter

    settings = load_settings()
    db = firestore.client(firebase_app(settings))
    query = db.collection("materials").where(filter=FieldFilter("owner_id", "==", settings.get("OWNER_UID")))
    if args.mode:
        query = query.where(filter=FieldFilter("mode", "==", args.mode))

    report: dict[str, dict[str, int]] = {}
    for snap in query.stream():
        doc = snap.to_dict() or {}
        missing = {k: v for k, v in DEFAULTS.items() if k not in doc}
        counts = report.setdefault(doc.get("mode", "?"), {"total": 0, "missing": 0, "updated": 0, "skipped": 0})
        counts["total"] += 1
        if not missing:
            continue
        counts["missing"] += 1
        if not args.apply:
            continue
        try:
            # 없는 필드만 더한다. 읽은 뒤 바뀐 문서(예: 그사이 승인됨)는 건너뛴다.
            snap.reference.update(missing, option=db.write_option(last_update_time=snap.update_time))
            counts["updated"] += 1
        except FailedPrecondition:
            counts["skipped"] += 1

    print(json.dumps({"apply": args.apply, "modes": report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
