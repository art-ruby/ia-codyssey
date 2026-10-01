"""T02.02: 실제 Firestore에서 저장소·중복 요청 규칙을 한 번 확인한다.

임시 소유자 ID(`check-t0202-...`)로 문서를 만들고 끝나면 모두 지운다.
'서버 재시작'은 새 FirestoreStore 인스턴스로 같은 키를 다시 보내는 것으로 확인한다.
출력에는 결과 요약만 남기고 서비스 계정·문서 원문은 출력하지 않는다.

실행: `M1-2` 폴더에서 `.\\.venv\\Scripts\\python.exe server/scripts/check_firestore.py`
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import load_settings  # noqa: E402
from app.core.context import RequestContext  # noqa: E402
from app.core.firestore import FirestoreStore, NotFound, VersionConflict  # noqa: E402
from app.core.requests import Result, record_id, run_idempotent  # noqa: E402


def main() -> int:
    owner = f"check-t0202-{uuid.uuid4().hex[:8]}"
    ctx = RequestContext(owner, "personal", f"key-{uuid.uuid4().hex[:8]}")
    other_mode = RequestContext(owner, "sample", None)
    settings = load_settings()
    store = FirestoreStore.from_settings(settings)
    report: dict[str, object] = {"owner": owner}
    created_id = None
    try:
        calls = []

        def handler(s):
            def run():
                calls.append(1)
                return Result(201, s.create(ctx, "materials", {"title": "firestore check"}))
            return run

        first = run_idempotent(store, ctx, "POST", "/check", {"t": 1}, handler(store))
        created_id = first.body["id"]

        restarted = FirestoreStore.from_settings(settings)  # 서버 재시작 흉내: 새 인스턴스
        again = run_idempotent(restarted, ctx, "POST", "/check", {"t": 1}, handler(restarted))
        report["idempotent_replay_after_restart"] = again.replayed and again.body["id"] == created_id
        report["handler_calls"] = len(calls)

        try:
            store.get(other_mode, "materials", created_id)
            report["other_mode_hidden"] = False
        except NotFound:
            report["other_mode_hidden"] = True

        updated = store.update(ctx, "materials", created_id, 1, {"title": "v2"})
        try:
            store.update(ctx, "materials", created_id, 1, {"title": "stale"})
            report["stale_update_rejected"] = False
        except VersionConflict as exc:
            report["stale_update_rejected"] = exc.current_version == 2
        report["version_after_update"] = updated["version"]

        try:
            page = store.list(ctx, "materials", limit=10)
            report["list_count"] = len(page.items)
        except Exception as exc:  # 복합 색인이 없으면 FailedPrecondition
            report["list_error"] = type(exc).__name__
            message = str(exc)
            start = message.find("https://console.firebase.google.com")
            if start >= 0:
                report["index_create_link"] = message[start:].split()[0]
    finally:
        if created_id:
            try:
                store.delete(ctx, "materials", created_id)
            except NotFound:
                pass
        store.release_key(record_id(owner, ctx.request_id))
        report["cleaned_up"] = True

    print(json.dumps(report, ensure_ascii=False, indent=2))
    ok = (report.get("idempotent_replay_after_restart") and report.get("handler_calls") == 1
          and report.get("other_mode_hidden") and report.get("stale_update_rejected"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
