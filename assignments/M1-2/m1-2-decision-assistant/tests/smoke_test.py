"""실제 서버를 띄워 HTTP 로 검증하는 smoke test.

TestClient 를 쓰지 않는다. TestClient 는 ASGI 앱을 프로세스 안에서 직접
부르므로 uvicorn 기동·포트 bind·CORS·직렬화 경계를 건너뛴다. 그 구간이
바로 '테스트는 다 통과하는데 사용자 첫 화면이 죽는' 장애가 사는 곳이다.

    python tests/smoke_test.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
BACKEND = PROJECT / "backend"
PORT = int(os.getenv("SMOKE_PORT", "8123"))
BASE = f"http://127.0.0.1:{PORT}"

passed, failed = 0, 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def call(method: str, path: str, body: dict | None = None, timeout: float = 30.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    def parse(raw: str):
        # /docs 는 HTML 을 준다. JSON 이 아니면 원문을 그대로 돌려준다.
        try:
            return json.loads(raw or "null")
        except json.JSONDecodeError:
            return raw

    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, parse(res.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        return exc.code, parse(exc.read().decode("utf-8", "replace"))


def wait_until_up(process: subprocess.Popen, seconds: int = 30) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        try:
            status, _ = call("GET", "/api/health", timeout=2)
            if status == 200:
                return True
        except Exception:
            time.sleep(0.3)
    return False


def main() -> int:
    print(f"[smoke] uvicorn 기동 (port {PORT})")
    process = subprocess.Popen(
        [sys.executable, "-X", "utf8", "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        cwd=str(BACKEND),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        # S1 — 서버가 실제로 포트를 열고 응답하는가
        if not wait_until_up(process):
            print("  FAIL  S1 서버 기동")
            print((process.stdout.read() if process.stdout else "")[:2000])
            return 1
        check("S1 서버 기동 + 포트 응답", True)

        status, health = call("GET", "/api/health")
        check("S2 /api/health 200", status == 200, str(status))
        print(f"        store={health.get('store')} openai={health.get('openai_configured')}")
        for warning in health.get("warnings", []):
            print(f"        warn: {warning}")

        status, _ = call("GET", "/docs")
        check("S3 Swagger /docs 접속", status == 200, str(status))

        # S4 — 표본 적재 (어댑터 경유)
        status, imported = call("POST", "/api/data/import?source=sample&replace=true")
        check("S4 표본 import >= 100건",
              status == 200 and imported.get("imported", 0) >= 100,
              f"{status} {imported.get('imported')}")
        check("S4b 표본이 실데이터로 표시되지 않음",
              imported.get("source", {}).get("is_real_data") is False)

        # S5 — Summary 가 AI 컨텍스트 형태로 나오는가
        status, summary = call("GET", "/api/data/summary")
        required = {"period", "count", "metrics", "trend", "decisions", "top_topics"}
        check("S5 summary 필수 항목", status == 200 and required <= set(summary), str(status))
        check("S5b summary count > 0", summary.get("count", 0) > 0)
        print(f"        기간 {summary.get('period')} · {summary.get('count')}건 · {summary.get('trend')}")

        # S6 — CRUD 한 바퀴
        new_item = {
            "date": "2026-09-11T09:00:00+09:00",
            "value": 88.5,
            "memo": "smoke test 후보",
            "topic": "年金 損",
            "title": "스모크 테스트용 제목",
            "channel": "loss_defense",
            "source": "manual",
        }
        status, created = call("POST", "/api/data", new_item)
        check("S6 후보 생성 201", status == 201, str(status))
        item_id = created.get("id", "")

        status, fetched = call("GET", f"/api/data/{item_id}")
        check("S6b 단건 조회", status == 200 and fetched.get("value") == 88.5, str(status))

        status, updated = call("PUT", f"/api/data/{item_id}", {"memo": "수정됨"})
        check("S6c 수정", status == 200 and updated.get("memo") == "수정됨", str(status))

        # S7 — 결정 변경과 handoff
        status, decided = call("PATCH", f"/api/data/{item_id}/decision",
                               {"decision": "MAKE", "reason": "smoke 근거1\nsmoke 근거2"})
        check("S7 MAKE 결정", status == 200 and decided.get("decision") == "MAKE", str(status))

        # 수동 후보의 결정은 RADAR 원장에 쓰지 않는다 — 응답이 그 사실을 말해야 한다.
        check("S7a 수동 후보는 RADAR 원장 미기록(이유 명시)",
              decided.get("ledger", {}).get("written") is False and bool(decided.get("ledger", {}).get("reason")))

        # 수동 후보는 RADAR 패키지가 될 수 없다. 가짜 인계 파일을 만들지 않고 409 로 이유를 말한다.
        status, handoff = call("POST", f"/api/handoff/{item_id}")
        check("S7b 수동 후보 인계 거부(409, 실측만 가능)", status == 409 and "실측" in str(handoff.get("detail", "")), str(status))
        status, sent = call("GET", "/api/handoff")
        check("S7c 인계 목록은 RADAR 저널 기준", status == 200 and "outbox" in str(sent.get("source", "")), str(status))

        # S8 — MAKE 가 아닌 후보는 인계 거부
        status, blocked = call("POST", "/api/data", {**new_item, "value": 10.0})
        other_id = blocked.get("id", "")
        status, _ = call("POST", f"/api/handoff/{other_id}")
        check("S8 미확정 후보 인계 차단(409)", status == 409, str(status))

        # S9 — 채팅 + 대화 자동 저장 + 불러오기
        status, chat = call("POST", "/api/chat", {"message": "지금 MAKE 후보가 몇 건이야?"})
        check("S9 chat 응답", status == 200 and bool(chat.get("reply")), str(status))
        conversation_id = chat.get("conversation_id", "")
        check("S9b 컨텍스트 주입 확인", chat.get("summary_used", {}).get("count", 0) > 0)

        status, conversations = call("GET", "/api/conversations")
        check("S9c 대화 목록에 저장됨",
              status == 200 and any(c["id"] == conversation_id for c in conversations),
              str(status))
        check("S9d 목록에는 본문 미포함",
              all("messages" not in c for c in conversations))

        status, one = call("GET", f"/api/conversations/{conversation_id}")
        check("S9e 대화 불러오기(전체 messages)",
              status == 200 and len(one.get("messages", [])) >= 2, str(status))

        # S10 — 삭제와 404 처리
        status, _ = call("DELETE", f"/api/data/{other_id}")
        check("S10 삭제", status == 200, str(status))
        status, _ = call("GET", f"/api/data/{other_id}")
        check("S10b 삭제 후 404", status == 404, str(status))

        # S11 — 잘못된 입력이 422/400 으로 구분되는가
        status, _ = call("POST", "/api/data", {"date": "2026-09-11T00:00:00Z", "value": 999})
        check("S11 범위 밖 점수 거부(422)", status == 422, str(status))

        print(f"\n[smoke] PASS {passed} · FAIL {failed}")
        return 0 if failed == 0 else 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    sys.exit(main())
