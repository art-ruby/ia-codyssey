import itertools
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.projects.service import DuplicateProjectName, create_project, update_project
from app.main import create_app

OWNER = "owner-1"
TOKENS = {"owner": {"uid": OWNER}}
_keys = itertools.count()


def make_client():
    store = MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: TOKENS[t], store=store)
    return TestClient(app), store


def h(mode="personal", key=True):
    headers = {"Authorization": "Bearer owner", "X-Data-Mode": mode}
    if key:
        headers["Idempotency-Key"] = f"k{next(_keys)}"
    return headers


# ── 프로젝트 ──────────────────────────────────────────────────────

def test_create_list_update_and_deactivate_project():
    c, _ = make_client()

    created = c.post("/api/projects", json={"name": "  AI Secretary ", "description": "주 프로젝트"}, headers=h())
    assert created.status_code == 201
    project = created.json()
    assert project["name"] == "AI Secretary" and project["active"] is True and project["version"] == 1
    assert "owner_id" not in project and "name_key" not in project

    renamed = c.put(f"/api/projects/{project['id']}", json={"expected_version": 1, "name": "AI 비서"}, headers=h())
    assert renamed.status_code == 200 and renamed.json()["version"] == 2

    off = c.put(f"/api/projects/{project['id']}", json={"expected_version": 2, "active": False}, headers=h())
    assert off.json()["active"] is False
    assert c.get("/api/projects", headers=h(key=False)).json()["items"] == []
    listed = c.get("/api/projects?include_inactive=true", headers=h(key=False)).json()["items"]
    assert [p["name"] for p in listed] == ["AI 비서"]


@pytest.mark.parametrize("second", ["ai secretary", "AI   Secretary", "AI SECRETARY"])
def test_duplicate_name_ignoring_case_and_spaces_is_409(second):
    c, _ = make_client()
    c.post("/api/projects", json={"name": "AI Secretary"}, headers=h())

    res = c.post("/api/projects", json={"name": second}, headers=h())

    assert res.status_code == 409 and res.json()["reason"] == "duplicate_name"


def test_renaming_to_another_projects_name_is_409_but_own_name_is_ok():
    c, _ = make_client()
    a = c.post("/api/projects", json={"name": "A"}, headers=h()).json()
    c.post("/api/projects", json={"name": "B"}, headers=h())

    assert c.put(f"/api/projects/{a['id']}", json={"expected_version": 1, "name": "b"}, headers=h()).status_code == 409
    assert c.put(f"/api/projects/{a['id']}", json={"expected_version": 1, "name": "a"}, headers=h()).status_code == 200


@pytest.mark.parametrize("body", [{"name": ""}, {"name": "   "}, {"name": "x" * 51},
                                  {"name": "ok", "description": "d" * 501}, {"name": "ok", "owner_id": "x"}])
def test_invalid_project_input_is_422(body):
    c, _ = make_client()
    assert c.post("/api/projects", json=body, headers=h()).status_code == 422


def test_stale_version_is_409_and_missing_key_is_422():
    c, _ = make_client()
    p = c.post("/api/projects", json={"name": "A"}, headers=h()).json()
    c.put(f"/api/projects/{p['id']}", json={"expected_version": 1, "description": "x"}, headers=h())

    stale = c.put(f"/api/projects/{p['id']}", json={"expected_version": 1, "description": "y"}, headers=h())
    assert stale.status_code == 409 and stale.json()["current_version"] == 2
    assert c.post("/api/projects", json={"name": "B"}, headers=h(key=False)).status_code == 422


def test_projects_are_separated_by_mode():
    c, _ = make_client()
    p = c.post("/api/projects", json={"name": "개인 프로젝트"}, headers=h("personal")).json()

    assert c.get("/api/projects", headers=h("sample", key=False)).json()["items"] == []
    assert c.put(f"/api/projects/{p['id']}", json={"expected_version": 1, "name": "x"},
                 headers=h("sample")).status_code == 404
    # 같은 이름도 다른 모드에서는 따로 만들 수 있다.
    assert c.post("/api/projects", json={"name": "개인 프로젝트"}, headers=h("sample")).status_code == 201


def test_same_idempotency_key_creates_one_project():
    c, store = make_client()
    headers = h()

    first = c.post("/api/projects", json={"name": "A"}, headers=headers)
    again = c.post("/api/projects", json={"name": "A"}, headers=headers)

    assert first.status_code == again.status_code == 201 and first.json() == again.json()
    assert len(c.get("/api/projects", headers=h(key=False)).json()["items"]) == 1


# ── 설정 ─────────────────────────────────────────────────────────

def test_unsaved_settings_return_mode_defaults():
    c, _ = make_client()

    personal = c.get("/api/settings", headers=h(key=False)).json()
    sample = c.get("/api/settings", headers=h("sample", key=False)).json()

    assert personal["saved"] is False and personal["version"] == 0
    assert "자동화" in personal["interests"] and "프로그램 개발" in personal["activities"]
    assert sample == {"interests": [], "activities": [], "default_project_id": None, "version": 0, "saved": False}


def test_settings_save_persist_and_version():
    c, _ = make_client()
    p = c.post("/api/projects", json={"name": "AI Secretary"}, headers=h()).json()

    saved = c.put("/api/settings", json={
        "expected_version": 0, "interests": [" 자동화 ", "자동화", "AI Agent"], "activities": ["학습"],
        "default_project_id": p["id"]}, headers=h())
    assert saved.status_code == 200
    assert saved.json()["interests"] == ["자동화", "AI Agent"] and saved.json()["version"] == 1

    # '새로고침': 다시 읽어도 유지된다.
    again = c.get("/api/settings", headers=h(key=False)).json()
    assert again["saved"] is True and again["default_project_id"] == p["id"] and again["version"] == 1

    second_create = c.put("/api/settings", json={"expected_version": 0, "interests": []}, headers=h())
    assert second_create.status_code == 409 and second_create.json()["current_version"] == 1
    updated = c.put("/api/settings", json={"expected_version": 1, "interests": ["콘텐츠"]}, headers=h())
    assert updated.json()["version"] == 2 and updated.json()["default_project_id"] is None


def test_update_before_first_save_is_conflict_not_404():
    c, _ = make_client()
    res = c.put("/api/settings", json={"expected_version": 3, "interests": []}, headers=h())
    assert res.status_code == 409 and res.json()["current_version"] == 0


def test_default_project_must_be_own_active_project():
    c, _ = make_client()
    p = c.post("/api/projects", json={"name": "A"}, headers=h()).json()
    c.put(f"/api/projects/{p['id']}", json={"expected_version": 1, "active": False}, headers=h())
    sample_p = c.post("/api/projects", json={"name": "S"}, headers=h("sample")).json()

    for project_id in (p["id"], sample_p["id"], "missing"):
        res = c.put("/api/settings", json={"expected_version": 0, "default_project_id": project_id}, headers=h())
        assert res.status_code == 422


@pytest.mark.parametrize("body", [{"expected_version": -1}, {"expected_version": 0, "interests": ["x" * 51]},
                                  {"expected_version": 0, "interests": [str(i) for i in range(21)]},
                                  {"expected_version": 0, "interests": [""]}, {"expected_version": 0, "mode": "x"}])
def test_invalid_settings_input_is_422(body):
    c, _ = make_client()
    assert c.put("/api/settings", json=body, headers=h()).status_code == 422


def test_settings_are_separated_by_mode():
    c, _ = make_client()
    c.put("/api/settings", json={"expected_version": 0, "interests": ["개인 관심"]}, headers=h("personal"))

    sample = c.get("/api/settings", headers=h("sample", key=False)).json()
    assert sample["saved"] is False and sample["interests"] == []


def test_protected_routes_require_login():
    c, _ = make_client()
    for method, path in [("get", "/api/projects"), ("post", "/api/projects"), ("get", "/api/settings"),
                         ("put", "/api/settings")]:
        res = getattr(c, method)(path, headers={"X-Data-Mode": "personal"})
        assert res.status_code == 401, (method, path)


def test_concurrent_project_creation_keeps_name_unique():
    store = MemoryStore()
    ctx = RequestContext(OWNER, "sample", None)
    barrier = threading.Barrier(2)

    def create():
        barrier.wait(timeout=5)
        return create_project(store, ctx, "Same Name", "")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create) for _ in range(2)]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result())
            except DuplicateProjectName:
                outcomes.append("duplicate")

    assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1
    assert outcomes.count("duplicate") == 1


def test_deactivating_default_project_clears_saved_default():
    c, _ = make_client()
    project = c.post("/api/projects", json={"name": "Default"}, headers=h()).json()
    saved = c.put("/api/settings", json={"expected_version": 0,
        "default_project_id": project["id"]}, headers=h())
    assert saved.status_code == 200 and saved.json()["version"] == 1

    disabled = c.put(f"/api/projects/{project['id']}", json={"expected_version": 1,
        "active": False}, headers=h())
    assert disabled.status_code == 200
    after = c.get("/api/settings", headers=h(key=False)).json()
    assert after["default_project_id"] is None
    assert after["version"] == 2

    c.put(f"/api/projects/{project['id']}", json={"expected_version": 2,
        "active": True}, headers=h())
    assert c.get("/api/settings", headers=h(key=False)).json()["default_project_id"] is None


def test_concurrent_project_renames_keep_name_unique():
    store = MemoryStore()
    ctx = RequestContext(OWNER, "sample", None)
    first = create_project(store, ctx, "First", "")
    second = create_project(store, ctx, "Second", "")
    barrier = threading.Barrier(2)

    def rename(project_id):
        barrier.wait(timeout=5)
        return update_project(store, ctx, project_id, 1, {"name": "Shared"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(rename, project_id) for project_id in (first["id"], second["id"])]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result())
            except DuplicateProjectName:
                outcomes.append("duplicate")
    assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1
    assert outcomes.count("duplicate") == 1


def test_invalid_project_ids_keep_existing_error_contract():
    c, _ = make_client()
    assert c.put("/api/projects/__bad__", json={"expected_version": 1, "name": "x"},
                 headers=h()).status_code == 404
    assert c.put("/api/settings", json={"expected_version": 0,
        "default_project_id": "__bad__"}, headers=h()).status_code == 422
