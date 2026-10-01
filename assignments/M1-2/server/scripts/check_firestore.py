"""T02.02: 실제 Firestore에서 저장소·중복 요청 규칙을 한 번 확인한다.

임시 소유자 ID(`check-t0202-...`)로 문서 두 건을 만들고, 성공·실패와 관계없이 끝나면 모두 지운다.
'서버 재시작'은 새 FirestoreStore 인스턴스로 같은 키를 다시 보내는 것으로 확인한다.
목록은 페이지 크기 1로 두 페이지를 넘겨 복합 색인과 커서를 함께 확인한다.
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

REQUIRED_TRUE = (
    "idempotent_replay_after_restart",
    "other_mode_hidden",
    "stale_update_rejected",
    "list_page1_has_next_cursor",
    "list_page2_is_other_doc",
    "list_page2_is_last",
    "cleaned_up",
)


def check_list(store: FirestoreStore, ctx: RequestContext, ids: set[str], report: dict) -> None:
    try:
        first = store.list(ctx, "materials", limit=1)
        report["list_page1_count"] = len(first.items)
        report["list_page1_has_next_cursor"] = len(first.items) == 1 and first.next_cursor is not None
        if not report["list_page1_has_next_cursor"]:
            return
        second = store.list(ctx, "materials", limit=1, cursor=first.next_cursor)
        report["list_page2_count"] = len(second.items)
        seen = {first.items[0]["id"]} | {d["id"] for d in second.items}
        report["list_page2_is_other_doc"] = len(second.items) == 1 and seen == ids
        report["list_page2_is_last"] = second.next_cursor is None
    except Exception as exc:  # 복합 색인이 없으면 FailedPrecondition
        report["list_error"] = type(exc).__name__
        message = str(exc)
        start = message.find("https://console.firebase.google.com")
        if start >= 0:
            report["index_create_link"] = message[start:].split()[0]


def cleanup(store: FirestoreStore, ctx: RequestContext, ids: list[str], report: dict) -> None:
    errors = []
    for doc_id in ids:
        try:
            store.delete(ctx, "materials", doc_id)
        except NotFound:
            pass
        except Exception as exc:
            errors.append(f"materials:{type(exc).__name__}")
    try:
        store.release_key(record_id(ctx.owner_id, ctx.request_id))
    except Exception as exc:
        errors.append(f"idempotency:{type(exc).__name__}")
    report["cleaned_up"] = not errors
    if errors:
        report["cleanup_errors"] = errors


def main() -> int:
    owner = f"check-t0202-{uuid.uuid4().hex[:8]}"
    ctx = RequestContext(owner, "personal", f"key-{uuid.uuid4().hex[:8]}")
    other_mode = RequestContext(owner, "sample", None)
    settings = load_settings()
    store = FirestoreStore.from_settings(settings)
    report: dict[str, object] = {"owner": owner}
    created: list[str] = []
    try:
        calls = []

        def handler(s):
            def run():
                calls.append(1)
                doc = s.create(ctx, "materials", {"title": "firestore check"})
                created.append(doc["id"])
                return Result(201, doc)
            return run

        first = run_idempotent(store, ctx, "POST", "/check", {"t": 1}, handler(store))
        first_id = first.body["id"]

        restarted = FirestoreStore.from_settings(settings)  # 서버 재시작 흉내: 새 인스턴스
        again = run_idempotent(restarted, ctx, "POST", "/check", {"t": 1}, handler(restarted))
        report["idempotent_replay_after_restart"] = (
            again.replayed and again.body["id"] == first_id and len(calls) == 1
        )
        report["handler_calls"] = len(calls)

        try:
            store.get(other_mode, "materials", first_id)
            report["other_mode_hidden"] = False
        except NotFound:
            report["other_mode_hidden"] = True

        updated = store.update(ctx, "materials", first_id, 1, {"title": "v2"})
        try:
            store.update(ctx, "materials", first_id, 1, {"title": "stale"})
            report["stale_update_rejected"] = False
        except VersionConflict as exc:
            report["stale_update_rejected"] = exc.current_version == 2
        report["version_after_update"] = updated["version"]

        created.append(store.create(ctx, "materials", {"title": "firestore check 2"})["id"])
        check_list(store, ctx, set(created), report)
    except Exception as exc:
        report["error"] = type(exc).__name__
    finally:
        cleanup(store, ctx, created, report)

    failed = [name for name in REQUIRED_TRUE if report.get(name) is not True]
    if "list_error" in report or "error" in report:
        failed.append(report.get("list_error") or report["error"])
    report["failed"] = failed
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
