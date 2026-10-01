import itertools

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore, VersionConflict
from app.features.materials.service import url_key
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
_keys = itertools.count()


def make_client():
    store = MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store)
    return TestClient(app), store


def h(mode="personal", key=True):
    headers = {"Authorization": "Bearer t", "X-Data-Mode": mode}
    if key:
        headers["Idempotency-Key"] = f"m{next(_keys)}"
    return headers


def post(c, body, **kw):
    return c.post("/api/materials", json=body, headers=h(**kw))


# ── 접수(A01) ─────────────────────────────────────────────────────

def test_url_only_is_saved_as_link_only_without_invented_title_or_summary():
    c, store = make_client()

    res = post(c, {"url": "https://Example.COM:443/Post?id=1"})

    assert res.status_code == 201
    m = res.json()
    assert m["analysis_status"] == "link_only" and m["source_type"] == "url"
    assert m["url"] == "https://Example.COM:443/Post?id=1"  # 원래 URL 보존
    assert m["title"] == "" and m["body"] == "" and m["description"] == ""
    assert (m["display_title"], m["title_source"]) == ("example.com", "url")  # 도메인을 임시 표제로만
    assert "summary" not in m and "ai_suggestion" not in m
    assert (m["review_status"], m["copy_status"], m["lifecycle"]) == ("unreviewed", "not_applicable", "active")
    assert m["registered_at"].endswith("+00:00")


def test_title_only_is_accepted_and_waits_for_user_to_start_analysis():
    c, _ = make_client()
    m = post(c, {"title": "Agent Memory 정리"}).json()
    assert m["source_type"] == "text" and m["analysis_status"] == "awaiting_start"
    assert (m["display_title"], m["title_source"]) == ("Agent Memory 정리", "user")


def test_description_and_body_are_kept_separately_with_save_reason():
    c, _ = make_client()
    m = post(c, {"url": "https://a.test", "description": "내 설명", "body": "원문 본문",
                 "save_reason": "AI Secretary 메모리 설계 참고", "memo": "나중 생각"}).json()
    assert (m["description"], m["body"], m["save_reason"], m["memo"]) == (
        "내 설명", "원문 본문", "AI Secretary 메모리 설계 참고", "나중 생각")
    assert m["analysis_status"] == "awaiting_start"


@pytest.mark.parametrize("body", [{}, {"title": "   "}, {"save_reason": "이유만"}, {"memo": "메모만"},
                                  {"save_reason": "이유", "memo": "메모"}])
def test_empty_or_reason_only_input_is_422(body):
    c, _ = make_client()
    res = post(c, body)
    assert res.status_code == 422
    assert "URL 또는 제목" in res.json()["detail"]


@pytest.mark.parametrize("url", ["ftp://a.test/f", "javascript:alert(1)", "file:///etc/passwd",
                                 "a.test/no-scheme", "https://", "http://exa mple.com"])
def test_non_http_or_broken_url_is_422(url):
    c, _ = make_client()
    res = post(c, {"url": url})
    assert res.status_code == 422 and "URL" in res.json()["detail"]


@pytest.mark.parametrize("field,limit", [("title", 200), ("description", 2000), ("body", 20000),
                                         ("save_reason", 2000), ("memo", 2000)])
def test_too_long_is_rejected_with_limit_not_truncated(field, limit):
    c, store = make_client()

    res = post(c, {"url": "https://a.test", field: "가" * (limit + 1)})

    assert res.status_code == 422
    assert f"{limit}자" in res.json()["detail"]
    assert "가" * 50 not in res.text  # 입력값을 되돌려 보내지 않는다
    assert store.list(ME, "materials").items == []

    ok = post(c, {"url": "https://a.test", field: "가" * limit})
    assert ok.status_code == 201 and len(ok.json()[field]) == limit


def test_html_is_stored_as_plain_text():
    c, _ = make_client()
    html = '<img src=x onerror="alert(1)"><script>alert(2)</script>'
    m = post(c, {"title": html, "body": html}).json()
    assert m["title"] == html and m["body"] == html


def test_file_or_unknown_fields_are_rejected():
    c, _ = make_client()
    for extra in ({"file": "x"}, {"analysis_status": "done"}, {"owner_id": "other"}):
        assert post(c, {"title": "t", **extra}).status_code == 422


# ── 접수 기록·원자성·중복 요청 ─────────────────────────────────────

def test_intake_record_is_created_with_material():
    c, store = make_client()
    m = post(c, {"url": "https://a.test"}).json()

    intake = store.get(ME, "intake_records", m["id"])
    assert intake["material_id"] == m["id"] and intake["received_at"] == m["registered_at"]


def test_create_many_is_all_or_nothing():
    store = MemoryStore()
    store.create(ME, "intake_records", {"material_id": "taken"}, doc_id="taken")

    with pytest.raises(VersionConflict):
        store.create_many(ME, [("materials", {"title": "x"}, "taken"), ("intake_records", {}, "taken")])
    assert store.list(ME, "materials").items == []


def test_same_key_creates_one_material_and_one_intake():
    c, store = make_client()
    headers = h()
    first = c.post("/api/materials", json={"url": "https://a.test"}, headers=headers)
    again = c.post("/api/materials", json={"url": "https://a.test"}, headers=headers)

    assert first.json() == again.json()
    assert len(store.list(ME, "materials").items) == 1 and len(store.list(ME, "intake_records").items) == 1


def test_missing_idempotency_key_is_422():
    c, _ = make_client()
    assert post(c, {"title": "t"}, key=False).status_code == 422


# ── 조회·수정 ────────────────────────────────────────────────────

def test_list_is_newest_first_with_cursor_and_mode_separation():
    c, _ = make_client()
    created = [post(c, {"title": f"t{i}"}).json() for i in range(5)]
    post(c, {"title": "sample"}, mode="sample")

    seen, cursor = [], None
    while True:
        url = "/api/materials?limit=2" + (f"&cursor={cursor}" if cursor else "")
        page = c.get(url, headers=h(key=False)).json()
        seen += [m["id"] for m in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    # Windows에서는 연속 저장의 created_at이 같을 수 있으므로 ID 보조 정렬도 검증한다.
    expected = sorted(created, key=lambda m: (m["created_at"], m["id"]), reverse=True)
    assert seen == [m["id"] for m in expected]


def test_get_and_update_detail():
    c, _ = make_client()
    m = post(c, {"url": "https://a.test"}).json()

    got = c.get(f"/api/materials/{m['id']}", headers=h(key=False))
    assert got.status_code == 200 and got.json()["id"] == m["id"]

    upd = c.put(f"/api/materials/{m['id']}", json={"expected_version": 1, "title": "직접 쓴 제목",
                                                   "save_reason": "이유"}, headers=h())
    body = upd.json()
    assert upd.status_code == 200 and body["version"] == 2
    assert body["title_source"] == "user" and body["analysis_status"] == "awaiting_start"
    assert body["url"] == "https://a.test"

    cleared = c.put(f"/api/materials/{m['id']}", json={"expected_version": 2, "title": None}, headers=h()).json()
    assert cleared["title"] == "" and cleared["analysis_status"] == "link_only"


def test_url_cannot_be_changed_and_stale_version_is_409():
    c, _ = make_client()
    m = post(c, {"url": "https://a.test"}).json()

    assert c.put(f"/api/materials/{m['id']}", json={"expected_version": 1, "url": "https://b.test"},
                 headers=h()).status_code == 422
    c.put(f"/api/materials/{m['id']}", json={"expected_version": 1, "memo": "m"}, headers=h())
    stale = c.put(f"/api/materials/{m['id']}", json={"expected_version": 1, "memo": "x"}, headers=h())
    assert stale.status_code == 409 and stale.json()["current_version"] == 2


def test_update_cannot_remove_all_content():
    c, _ = make_client()
    m = post(c, {"title": "only"}).json()
    res = c.put(f"/api/materials/{m['id']}", json={"expected_version": 1, "title": ""}, headers=h())
    assert res.status_code == 422


def test_other_mode_cannot_read_or_update():
    c, _ = make_client()
    m = post(c, {"title": "t"}).json()
    assert c.get(f"/api/materials/{m['id']}", headers=h("sample", key=False)).status_code == 404
    assert c.put(f"/api/materials/{m['id']}", json={"expected_version": 1, "memo": "x"},
                 headers=h("sample")).status_code == 404


def test_project_references_must_be_active_projects_of_same_mode():
    c, _ = make_client()
    p = c.post("/api/projects", json={"name": "AI Secretary"}, headers=h()).json()
    other = c.post("/api/projects", json={"name": "표본"}, headers=h("sample")).json()

    ok = post(c, {"title": "t", "primary_project_id": p["id"], "related_project_ids": [p["id"], p["id"]]})
    assert ok.status_code == 201
    assert ok.json()["primary_project_id"] == p["id"] and ok.json()["related_project_ids"] == [p["id"]]
    assert post(c, {"title": "t", "primary_project_id": other["id"]}).status_code == 422
    assert post(c, {"title": "t", "related_project_ids": ["missing"]}).status_code == 422


def test_url_key_only_safe_normalization():
    assert url_key("HTTPS://Example.COM:443/A?b=1#c") == "https://example.com/A?b=1#c"
    assert url_key("http://example.com:80/") == "http://example.com/"
    assert url_key("http://example.com:8080/") == "http://example.com:8080/"
    assert url_key("https://a.test/?utm_source=x") == "https://a.test/?utm_source=x"  # 추적 쿼리도 보존
