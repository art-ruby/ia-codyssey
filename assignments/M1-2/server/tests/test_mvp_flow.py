"""T08.01 MVP 통합 흐름과 보안·실패 흐름 검증(A01·A02·A13·A14·A15·A16·A17·A18·A19·A23·A24·A26).

URL 접수 → 분석 → 검토·승인 → 보관 → 검색 → 질문 → 대화 복원 → 휴지통 → 복원 → 영구 삭제를 한 번에 잇고,
인증 우회·모드 혼합·오래된 승인·분석 제외 우회·입력 HTML 실행을 검사한다. Provider만 가짜다(실제 호출은 smoke 스크립트).
"""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.auth import InvalidToken
from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.analysis.provider import TextResult
from app.main import create_app
from test_analysis_lifecycle import FakeAdapter as AnalysisFake

OWNER = "owner-1"
_keys = itertools.count()
SCRIPT = "<script>alert(1)</script><img src=x onerror=alert(2)>"
WEB_JS = Path(__file__).parents[2] / "web" / "js"


class Adapter(AnalysisFake):
    """분석(`analyze_material`)과 채팅(`answer_question`)을 모두 가짜로 한다. 받은 채팅 메시지를 남긴다."""

    def __init__(self, reply=None):
        super().__init__()
        self.chats: list[list[dict]] = []
        self.reply = reply or {"from_materials": "자료 1에 종료 일정이 있습니다.", "interpretation": "", "sources": [1]}

    def answer_question(self, messages):
        self.chats.append(messages)
        return TextResult(json.dumps(self.reply, ensure_ascii=False), "fake-model", 10)


def make(adapter=None, store=None):
    store = store or MemoryStore()
    adapter = adapter or Adapter()
    tokens = {"owner-token": {"uid": OWNER}, "other-token": {"uid": "intruder"}}

    def verify(token):
        if token not in tokens:
            raise InvalidToken("bad")
        return tokens[token]

    app = create_app(load_settings({"OWNER_UID": OWNER, "AI_DAILY_REQUEST_LIMIT": "50"}), verify_token=verify,
                     store=store, analysis_adapter_factory=lambda: adapter)
    return TestClient(app, raise_server_exceptions=False), store, adapter


def h(mode="personal", key=None):
    return {"Authorization": "Bearer owner-token", "X-Data-Mode": mode, "Idempotency-Key": key or f"k{next(_keys)}"}


def post(c, path, body, mode="personal"):
    return c.post(path, json=body, headers=h(mode))


def intake(c, mode="personal", **body):
    res = post(c, "/api/materials", body, mode)
    assert res.status_code == 201, res.text
    return res.json()


def get_material(c, m, mode="personal"):
    return c.get(f"/api/materials/{m['id']}", headers=h(mode))


def approve(c, m, mode="personal", **changes):
    item = {"material_id": m["id"], "expected_version": m["version"], "action": "keep"}
    if changes:
        item["changes"] = changes
    res = post(c, "/api/reviews/approve", {"items": [item]}, mode)
    assert res.status_code == 200, res.text
    return res.json()["results"][0]


def trash(c, m):
    res = post(c, "/api/reviews/approve", {"items": [{"material_id": m["id"], "expected_version": m["version"],
                                                       "action": "trash"}]})
    assert res.status_code == 200, res.text
    return res.json()["results"][0]["material"]


def search(c, q, mode="personal"):
    return [i["id"] for i in c.get("/api/materials/search", params={"q": q}, headers=h(mode)).json()["items"]]


def kept_total(c, mode="personal"):
    return c.get("/api/data/summary", headers=h(mode)).json()["total"]


def ask(c, question, mode="personal", conversation_id=None):
    body = {"question": question, **({"conversation_id": conversation_id} if conversation_id else {})}
    return post(c, "/api/chat", body, mode)


def usage_by_kind(c):
    return {k: v for k, v in c.get("/api/ai/usage", headers=h()).json()["by_kind"].items() if v}


def source_status(c, conv_id):
    return c.get(f"/api/conversations/{conv_id}", headers=h()).json()["messages"][1]["sources"][0]["current_status"]


# ── 전체 흐름 ─────────────────────────────────────────────────────

def test_full_mvp_flow_from_url_intake_to_permanent_delete():
    c, store, adapter = make()

    # A01: URL만 접수 → 저장되고 본문 미확인, AI 호출 없음, 입력하지 않은 요약 없음
    link = intake(c, url="https://example.com/settlement")
    assert link["analysis_status"] == "link_only" and not link.get("ai_summary") and adapter.calls == []
    assert approve(c, link)["material"]["review_status"] == "approved"
    assert search(c, "example") == [link["id"]]

    # A18: 같은 URL을 다시 입력하면 기존 자료를 알려 준다(409, 새 자료 없음)
    dup = post(c, "/api/materials", {"url": "https://example.com/settlement"})
    assert dup.status_code == 409 and dup.json()["reason"] == "duplicate_url"

    # 텍스트 자료 → 사용량 확인 → 분석 시작(사용자 동의) → 검토 → 중요도 수정 승인
    text = intake(c, title="정산 API 종료 안내", body="정산 API는 2027년 1월 31일에 종료된다.",
                  save_reason="결제 개편 일정")
    assert c.get("/api/ai/usage", headers=h()).json()["used"] == 0
    started = post(c, f"/api/materials/{text['id']}/analyze", {"expected_version": text["version"]})
    assert started.status_code == 202
    analyzed = get_material(c, text).json()
    assert analyzed["analysis_status"] == "done" and len(adapter.calls) == 1
    usage = c.get("/api/ai/usage", headers=h()).json()  # A23: 실제 호출 1회가 사용량
    assert (usage["used"], usage["by_kind"]["analysis"]) == (1, 1)

    kept = approve(c, analyzed, user_importance="low")["material"]  # A02: AI 'high'를 사용자가 'low'로 수정
    assert get_material(c, kept).json()["user_importance"] == "low"
    assert kept_total(c) == 2  # 링크 자료 + 텍스트 자료

    # 검색 → 질문(A14: 존재하는 출처만) → 대화 저장
    assert text["id"] in search(c, "정산")
    answer = ask(c, "정산 API 종료 일정 알려줘")
    assert answer.status_code == 200
    body = answer.json()
    assert [s["material_id"] for s in body["sources"]] == [text["id"]] and body["saved"] is True
    conv_id = body["conversation_id"]
    assert usage_by_kind(c) == {"analysis": 1, "chat": 1}

    # A17(대화): 불러오기에 출처의 현재 상태
    restored = c.get(f"/api/conversations/{conv_id}", headers=h()).json()
    assert [m["role"] for m in restored["messages"]] == ["user", "assistant"]
    assert source_status(c, conv_id) == "available"

    # A26: 휴지통 → 검색·새 채팅 문맥·보관 수에서 빠지고, 대화 출처는 '휴지통'으로 표시
    trashed = trash(c, kept)
    assert search(c, "정산") == [] and kept_total(c) == 1
    again = ask(c, "정산 API 종료 일정 알려줘").json()
    assert again["sources"] == [] and again["omitted"]["no_materials"] is True
    assert source_status(c, conv_id) == "trashed"

    # 복원 → 다시 포함
    restore = post(c, f"/api/trash/{text['id']}/restore", {"expected_version": trashed["version"]})
    assert restore.status_code == 200
    assert text["id"] in search(c, "정산") and kept_total(c) == 2

    # 영구 삭제: 휴지통 → 확인 값·버전과 함께 → 자료·검색·대화 출처 모두 사라짐
    moved = trash(c, get_material(c, text).json())
    refused = c.delete(f"/api/trash/{text['id']}", params={"expected_version": moved["version"]}, headers=h())
    assert refused.status_code == 422 and get_material(c, text).status_code == 200  # 확인 값 없이는 안 지워진다
    done = c.delete(f"/api/trash/{text['id']}", params={"expected_version": moved["version"], "confirm": "permanent"},
                    headers=h())
    assert done.status_code == 200
    assert get_material(c, text).status_code == 404 and search(c, "정산") == []
    assert source_status(c, conv_id) == "deleted"
    # 대화를 지우면 남은 인용문까지 사라진다
    assert c.delete(f"/api/conversations/{conv_id}", headers=h()).status_code == 200
    assert c.get(f"/api/conversations/{conv_id}", headers=h()).status_code == 404
    # 휴지통 뒤에 한 질문은 별도 대화이므로 그 대화만 남아 있다. 마저 지우면 저장소에 대화가 없다.
    left = store.list(RequestContext(OWNER, "personal", None), "conversations").items
    assert [d["id"] for d in left] == [again["conversation_id"]]
    assert c.delete(f"/api/conversations/{again['conversation_id']}", headers=h()).status_code == 200
    assert store.list(RequestContext(OWNER, "personal", None), "conversations").items == []


def test_sample_mode_number_crud_summary_and_isolation():
    c, _, _ = make()
    values = [3, 4, 5]
    rows = [post(c, "/api/data", {"date": f"2026-09-{10 + i}", "metric_type": "kept_count", "value": v}, "sample").json()
            for i, v in enumerate(values)]
    summary = c.get("/api/data/summary", headers=h("sample")).json()
    assert (summary["source"], summary["label"], summary["total"]) == ("sample", "가상 보관 기록", sum(values))
    assert (summary["min"], summary["max"]) == (3, 5) and summary["average"] == round(sum(values) / 3, 2)

    edited = c.put(f"/api/data/{rows[0]['id']}", json={"expected_version": rows[0]["version"], "value": 10},
                   headers=h("sample"))
    assert edited.status_code == 200
    assert c.get("/api/data/summary", headers=h("sample")).json()["total"] == 19
    gone = c.delete(f"/api/data/{rows[1]['id']}", params={"expected_version": rows[1]["version"]}, headers=h("sample"))
    assert gone.status_code == 200
    assert c.get("/api/data/summary", headers=h("sample")).json()["total"] == 15
    # 개인 모드의 실제 보관 수에는 표본 기록이 섞이지 않는다
    personal = c.get("/api/data/summary", headers=h("personal")).json()
    assert (personal["source"], personal["total"]) == ("actual", 0)


# ── 인증 우회 ─────────────────────────────────────────────────────

def api_routes(app):
    """OpenAPI 명세의 /api/ 경로·메서드(포함된 라우터가 app.routes에 펼쳐지지 않으므로 명세를 쓴다)."""
    return sorted((method.upper(), re.sub(r"\{[^}]+\}", "x", path))
                  for path, ops in app.openapi()["paths"].items() if path.startswith("/api/")
                  for method in ops if method in ("get", "post", "put", "delete"))


def test_every_api_route_rejects_missing_invalid_and_non_owner_tokens():
    c, _, _ = make()
    routes = api_routes(c.app)
    assert len(routes) >= 33  # 경로를 못 찾아 빈 검사가 되지 않게(2026-10-03 기준 /api/ 작업 33개)
    bad = []
    for method, path in routes:
        for headers, expected in (({}, 401), ({"Authorization": "Bearer nope", "X-Data-Mode": "personal"}, 401),
                                  ({"Authorization": "Bearer other-token", "X-Data-Mode": "personal",
                                    "Idempotency-Key": "k"}, 403)):
            res = c.request(method, path, headers=headers, json={} if method in ("POST", "PUT") else None)
            if res.status_code != expected:
                bad.append((method, path, expected, res.status_code))
    assert bad == []


# ── 모드 혼합 ─────────────────────────────────────────────────────

def approve_status(c, m):
    res = post(c, "/api/reviews/approve", {"items": [{"material_id": m["id"], "expected_version": m["version"],
                                                       "action": "keep"}]})
    return res.json()["results"][0]["status"] if res.status_code == 200 else res.status_code


def test_other_mode_material_is_invisible_everywhere_and_never_sent_to_ai():
    c, _, adapter = make()
    marker = "SAMPLEONLYMARKER"
    sample = intake(c, "sample", title="정산 표본 자료", body=f"정산 일정 {marker}")
    sample = approve(c, sample, "sample")["material"]
    assert search(c, "정산", "sample") == [sample["id"]]

    assert get_material(c, sample).status_code == 404  # 개인 모드에서 같은 ID
    assert search(c, "정산") == []
    assert post(c, f"/api/materials/{sample['id']}/analyze", {"expected_version": sample["version"]}).status_code == 404
    assert c.put(f"/api/materials/{sample['id']}", json={"expected_version": sample["version"], "memo": "x"},
                 headers=h()).status_code == 404
    assert approve_status(c, sample) == "not_found"
    assert post(c, f"/api/trash/{sample['id']}/restore", {"expected_version": sample["version"]}).status_code == 404

    body = ask(c, "정산 일정 알려줘").json()
    assert body["sources"] == [] and marker not in json.dumps(adapter.chats, ensure_ascii=False)
    conv = ask(c, "표본 질문", "sample").json()["conversation_id"]
    assert c.get(f"/api/conversations/{conv}", headers=h()).status_code == 404
    assert conv not in [i["id"] for i in c.get("/api/conversations", headers=h()).json()["items"]]
    assert c.delete(f"/api/conversations/{conv}", headers=h()).status_code == 404


# ── 오래된 승인 ───────────────────────────────────────────────────

def test_approval_with_an_old_version_does_not_keep_the_material():
    c, _, _ = make()
    m = intake(c, title="정산 일정", body="초안 본문")
    edited = c.put(f"/api/materials/{m['id']}", json={"expected_version": m["version"], "body": "수정한 본문"},
                   headers=h())
    assert edited.status_code == 200
    result = approve(c, m)  # 수정 전 화면(버전)으로 승인
    assert result["status"] != "approved", result
    now = get_material(c, m).json()
    assert now["review_status"] == "unreviewed" and now["body"] == "수정한 본문" and search(c, "정산") == []
    assert approve(c, now)["material"]["review_status"] == "approved"  # 새로 불러온 버전으로는 승인된다


def test_analysis_started_from_an_old_version_is_refused_without_calling_ai():
    c, _, adapter = make()
    m = intake(c, title="제목", body="본문")
    c.put(f"/api/materials/{m['id']}", json={"expected_version": m["version"], "memo": "메모"}, headers=h())
    res = post(c, f"/api/materials/{m['id']}/analyze", {"expected_version": m["version"]})
    assert res.status_code == 409 and adapter.calls == [] and usage_by_kind(c) == {}


# ── 분석 제외 우회 ────────────────────────────────────────────────

def test_ai_excluded_material_cannot_reach_ai_by_analysis_chat_or_history():
    c, _, adapter = make()
    marker = "EXCLUDEDBODYMARKER"
    m = intake(c, title="정산 제외 자료", body=f"정산 일정 {marker}")
    m = approve(c, m)["material"]
    first = ask(c, "정산 일정 알려줘").json()
    assert [s["material_id"] for s in first["sources"]] == [m["id"]]  # 제외 전에는 근거로 쓰인다

    excluded = c.put(f"/api/materials/{m['id']}", json={"expected_version": m["version"], "ai_excluded": True},
                     headers=h()).json()
    calls_before = len(adapter.calls)
    assert post(c, f"/api/materials/{m['id']}/analyze", {"expected_version": excluded["version"]}).status_code == 409
    assert len(adapter.calls) == calls_before
    assert search(c, "정산") == [m["id"]]  # 보관함에서는 보인다(AI 문맥만 막는다)

    chats_before = len(adapter.chats)
    follow = ask(c, "정산 일정 다시 알려줘", conversation_id=first["conversation_id"]).json()
    assert follow["sources"] == [] and follow["omitted"]["excluded"] == {"ai_excluded": 1}
    assert marker not in json.dumps(adapter.chats[chats_before:], ensure_ascii=False)  # 새 검색·과거 대화 모두

    back = c.put(f"/api/materials/{m['id']}", json={"expected_version": excluded["version"], "ai_excluded": False},
                 headers=h()).json()
    assert back["ai_excluded"] is False  # 제외를 풀면 다시 근거가 된다
    assert [s["material_id"] for s in ask(c, "정산 일정 알려줘").json()["sources"]] == [m["id"]]


# ── 입력 HTML ─────────────────────────────────────────────────────

def test_input_html_is_stored_as_text_and_returned_as_json_only():
    c, _, _ = make(Adapter({"from_materials": SCRIPT, "interpretation": SCRIPT, "sources": [1]}))
    m = intake(c, title=f"정산 {SCRIPT}", body=f"정산 일정 {SCRIPT}", memo=SCRIPT)
    assert m["body"] == f"정산 일정 {SCRIPT}"  # 지우거나 바꾸지 않고 글자 그대로 보관
    m = approve(c, m)["material"]
    responses = [get_material(c, m), c.get("/api/materials/search", params={"q": "정산"}, headers=h()),
                 ask(c, "정산 일정 알려줘")]
    for res in responses:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("application/json"), res.headers["content-type"]
    assert responses[2].json()["answer"]["from_materials"] == SCRIPT


def test_web_code_never_inserts_strings_as_html():
    sinks = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function\(|srcdoc")
    offenders = [f"{path.name}:{n}" for path in sorted(WEB_JS.rglob("*.js"))
                 for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if sinks.search(line)]
    assert offenders == []
