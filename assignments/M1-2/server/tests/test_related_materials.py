"""T05.02 관련 자료: 근거 있는 후보만 제안, 연결·관련 없음·해제를 승인 API(action=link)로 기록, 제안과 확정 구분.

후보 계산 단위 시험과 API(`GET /api/materials/{id}/related`, `POST /api/reviews/approve`) 시험을 함께 둔다.
"""

from __future__ import annotations

import itertools

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.analysis.schemas import content_hash
from app.features.materials import related
from app.features.materials.url_keys import url_key
from app.main import create_app

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
SAMPLE = RequestContext(OWNER, "sample", None)
_ids = itertools.count()
_keys = itertools.count()


def make(store, ctx=ME, approved=True, registered=None, **fields):
    i = next(_ids)
    data = {"source_type": "url" if fields.get("url") else "text", "title": "", "description": "", "body": "",
            "save_reason": "", "memo": "", "url": None, "primary_project_id": None, "related_project_ids": [],
            "review_status": "approved" if approved else "unreviewed", "copy_status": "not_applicable",
            "lifecycle": "active", "registered_at": registered or f"2026-10-01T00:{i % 60:02d}:00+00:00", **fields}
    data["url_key"] = url_key(data["url"]) if data["url"] else None
    if "ai_keywords" in fields:
        data.update(analysis_status="done", ai_content_hash=content_hash(data))
    return store.create(ctx, "materials", data, doc_id=f"r{i:04d}")


BASE = dict(title="정산 API 종료 공지", body="기존 정산 API는 내년 1월에 종료된다. 인증 방식을 OAuth로 전환해야 한다.")


def ids(view):
    return [c["material"]["id"] for c in view["candidates"]]


# ── 후보 계산 ─────────────────────────────────────────────────────

def test_unrelated_materials_give_no_candidates():
    store = MemoryStore()
    new = make(store, approved=False, **BASE)
    make(store, title="Rust 소유권 정리", body="값마다 소유자가 하나뿐이라는 규칙과 빌림 개념")
    make(store, title="점심 메뉴", body="김치찌개와 된장찌개 비교")
    assert related.related_view(store, ME, new["id"])["candidates"] == []


def test_shared_content_terms_make_a_candidate_with_evidence():
    store = MemoryStore()
    new = make(store, approved=False, **BASE)
    old = make(store, title="정산 시스템 개편 회의", body="정산 API 전환 일정과 OAuth 인증 적용 범위를 논의했다.")
    view = related.related_view(store, ME, new["id"])
    assert ids(view) == [old["id"]]
    evidence = view["candidates"][0]["evidence"]
    terms = next(e for e in evidence if e["type"] == "terms")["values"]
    assert {"정산", "oauth"} <= set(terms)


def test_korean_particles_do_not_hide_shared_words():
    store = MemoryStore()
    new = make(store, approved=False, title="결제모듈 리팩터링은 다음 주", body="결제모듈을 정리하고 정산서를 갱신한다")
    old = make(store, title="결제모듈의 구조", body="정산서와 결제모듈에서 쓰는 리팩터링 기준")
    assert ids(related.related_view(store, ME, new["id"])) == [old["id"]]


def test_project_alone_is_weak_but_project_plus_term_is_enough():
    store = MemoryStore()
    new = make(store, approved=False, title="정산 일정", body="이번 분기 작업", primary_project_id="p1")
    only_project = make(store, title="회의실 예약", body="다음 주 화요일", related_project_ids=["p1"])
    with_term = make(store, title="정산 보고서", body="월간 매출", primary_project_id="p1")
    view = related.related_view(store, ME, new["id"])
    assert ids(view) == [with_term["id"]]
    assert only_project["id"] not in ids(view)
    kinds = {e["type"] for e in view["candidates"][0]["evidence"]}
    assert {"project", "terms"} <= kinds


def test_two_shared_ai_keywords_are_enough():
    store = MemoryStore()
    new = make(store, approved=False, title="새 공지", body="세부 내용 없음", ai_keywords=["마이그레이션", "웹훅"])
    old = make(store, title="연동 가이드", body="웹훅 재시도와 마이그레이션 순서를 설명한다")
    view = related.related_view(store, ME, new["id"])
    assert ids(view) == [old["id"]]
    assert any(e["type"] == "keywords" for e in view["candidates"][0]["evidence"])


def test_same_url_is_duplicate_handling_not_related():
    store = MemoryStore()
    new = make(store, approved=False, url="https://example.com/notice", **BASE)
    make(store, url="https://EXAMPLE.com/notice", title=BASE["title"], body=BASE["body"])  # 같은 비교 키
    assert related.related_view(store, ME, new["id"])["candidates"] == []


def test_only_kept_active_same_mode_others_are_candidates():
    store = MemoryStore()
    new = make(store, approved=False, **BASE)
    make(store, approved=False, **BASE)  # 미승인
    make(store, lifecycle="trash", **BASE)  # 휴지통
    make(store, ctx=SAMPLE, **BASE)  # 다른 모드
    assert related.related_view(store, ME, new["id"])["candidates"] == []


def test_at_most_five_ordered_by_strength():
    store = MemoryStore()
    new = make(store, approved=False, **BASE)
    weak = [make(store, title=f"정산 OAuth 전환 {i}", body="메모") for i in range(6)]
    strong = make(store, title="정산 API 종료와 OAuth 전환", body="기존 정산 API 종료 인증 방식 전환")
    view = related.related_view(store, ME, new["id"])
    assert len(view["candidates"]) == related.MAX_CANDIDATES
    assert ids(view)[0] == strong["id"]
    assert set(ids(view)[1:]) <= {w["id"] for w in weak}


# ── API: 조회와 결정 ──────────────────────────────────────────────

def make_client(store=None):
    store = store or MemoryStore()
    app = create_app(load_settings({"OWNER_UID": OWNER}), verify_token=lambda t: {"uid": OWNER}, store=store)
    return TestClient(app), store


def h(key=None):
    return {"Authorization": "Bearer t", "X-Data-Mode": "personal", "Idempotency-Key": key or f"l{next(_keys)}"}


def get_related(c, m):
    res = c.get(f"/api/materials/{m['id']}/related", headers=h())
    assert res.status_code == 200
    return res.json()


def decide(c, src, dst, decision, key=None, src_version=None, dst_version=None):
    item = {"material_id": src["id"], "expected_version": src_version or src["version"], "action": "link",
            "link": {"target_id": dst["id"], "target_version": dst_version or dst["version"], "decision": decision}}
    return c.post("/api/reviews/approve", json={"items": [item]}, headers=h(key))


def result(res):
    assert res.status_code == 200
    return res.json()["results"][0]


def pair(store):
    new = make(store, approved=False, **BASE)
    old = make(store, title="정산 시스템 개편 회의", body="정산 API 전환 일정과 OAuth 인증 적용 범위")
    return new, old


def test_link_moves_candidate_to_confirmed_with_versions():
    c, store = make_client()
    new, old = pair(store)
    assert ids(get_related(c, new)) == [old["id"]]

    r = result(decide(c, new, old, "link"))

    assert r["status"] == "linked"
    view = get_related(c, new)
    assert view["candidates"] == []
    confirmed = view["confirmed"][0]
    assert confirmed["material"]["id"] == old["id"] and confirmed["state"] == "linked"
    assert confirmed["available"] is True
    assert (confirmed["source_version"], confirmed["target_version"]) == (new["version"], old["version"])
    # 반대쪽에서 봐도 같은 연결이다.
    assert get_related(c, old)["confirmed"][0]["material"]["id"] == new["id"]
    # 연결은 자료 버전을 올리지 않는다.
    assert store.get(ME, "materials", new["id"])["version"] == new["version"]


def test_unrelated_is_remembered_and_not_suggested_again():
    c, store = make_client()
    new, old = pair(store)
    assert result(decide(c, new, old, "unrelated"))["status"] == "marked_unrelated"
    view = get_related(c, new)
    assert view["candidates"] == [] and view["confirmed"] == [] and view["unrelated_count"] == 1
    assert result(decide(c, new, old, "link"))["status"] == "linked"  # 판단을 바꿀 수 있다


def test_unlink_returns_strong_pair_to_suggestions():
    c, store = make_client()
    new, old = pair(store)
    decide(c, new, old, "link")
    assert result(decide(c, new, old, "unlink"))["status"] == "unlinked"
    view = get_related(c, new)
    assert view["confirmed"] == [] and ids(view) == [old["id"]]


def test_unlink_without_link_is_invalid():
    c, store = make_client()
    new, old = pair(store)
    r = result(decide(c, new, old, "unlink"))
    assert r["status"] == "invalid" and r["reason"] == "not_linked"


@pytest.mark.parametrize("which", ["source", "target"])
def test_version_change_is_a_conflict(which):
    c, store = make_client()
    new, old = pair(store)
    stale = new if which == "source" else old
    store.update(ME, "materials", stale["id"], stale["version"], {"memo": "다른 곳에서 수정"})
    r = result(decide(c, new, old, "link"))
    assert r["status"] == "conflict" and r["side"] == which
    assert get_related(c, new)["confirmed"] == []


def test_trashed_or_unapproved_target_cannot_be_linked():
    c, store = make_client()
    new, old = pair(store)
    unapproved = make(store, approved=False, title="미승인 정산 OAuth 자료", body="정산 OAuth 전환")
    store.update(ME, "materials", old["id"], old["version"], {"lifecycle": "trash"})
    old = store.get(ME, "materials", old["id"])
    assert result(decide(c, new, old, "link"))["reason"] == "target_unavailable"
    assert result(decide(c, new, unapproved, "link"))["reason"] == "target_unavailable"


def test_trashed_source_cannot_link():
    c, store = make_client()
    new, old = pair(store)
    store.update(ME, "materials", new["id"], new["version"], {"lifecycle": "trash"})
    new = store.get(ME, "materials", new["id"])
    assert result(decide(c, new, old, "link"))["reason"] == "trashed"


def test_same_url_pair_cannot_be_linked():
    c, store = make_client()
    a = make(store, approved=False, url="https://example.com/x", **BASE)
    b = make(store, url="https://example.com/x", title="같은 주소", body="다른 설명")
    assert result(decide(c, a, b, "link"))["reason"] == "same_url"


def test_deleted_target_after_link_is_shown_as_unavailable():
    c, store = make_client()
    new, old = pair(store)
    decide(c, new, old, "link")
    store.update(ME, "materials", old["id"], old["version"], {"lifecycle": "trash"})
    confirmed = get_related(c, new)["confirmed"]
    assert confirmed[0]["available"] is False and confirmed[0]["material"]["id"] == old["id"]


def test_missing_target_is_not_found():
    c, store = make_client()
    new, _ = pair(store)
    ghost = {"id": "r9999", "version": 1}
    assert result(decide(c, new, ghost, "link"))["status"] == "not_found"


def test_same_key_replays_link_decision():
    c, store = make_client()
    new, old = pair(store)
    first = decide(c, new, old, "link", key="same")
    again = decide(c, new, old, "link", key="same")
    assert again.json() == first.json()
    assert len(store.find(ME, "material_links", "source_id", new["id"])) == 1


def test_related_of_other_mode_material_is_404():
    c, store = make_client()
    other = make(store, ctx=SAMPLE, **BASE)
    assert c.get(f"/api/materials/{other['id']}/related", headers=h()).status_code == 404


def test_reverse_pair_in_one_request_is_rejected():
    # 리뷰 재현: A→B와 B→A는 같은 관계(같은 기록)인데 한 요청에서 서로 다른 결정으로 통과했다.
    c, store = make_client()
    a = make(store, **BASE)
    b = make(store, title="정산 시스템 개편 회의", body="정산 API 전환 일정과 OAuth 인증 적용 범위")
    items = [
        {"material_id": a["id"], "expected_version": a["version"], "action": "link",
         "link": {"target_id": b["id"], "target_version": b["version"], "decision": "link"}},
        {"material_id": b["id"], "expected_version": b["version"], "action": "link",
         "link": {"target_id": a["id"], "target_version": a["version"], "decision": "unrelated"}},
    ]
    assert c.post("/api/reviews/approve", json={"items": items}, headers=h()).status_code == 422
    assert store.find(ME, "material_links", "a_id", min(a["id"], b["id"])) == []


@pytest.mark.parametrize("change, expected", [
    ({"memo": "확인 직후 수정"}, ("conflict", "target")),
    ({"lifecycle": "trash"}, ("invalid", "target_unavailable")),
])
def test_change_between_check_and_save_is_not_saved(monkeypatch, change, expected):
    # 리뷰 재현: 버전 확인과 기록 저장이 따로라, 그 사이 수정·휴지통 이동이 있어도 오래된 버전으로 저장됐다.
    c, store = make_client()
    new, old = pair(store)
    original = related.project_names

    def change_target_meanwhile(*args, **kwargs):
        current = store.get(ME, "materials", old["id"])
        store.update(ME, "materials", old["id"], current["version"], change)
        return original(*args, **kwargs)

    monkeypatch.setattr(related, "project_names", change_target_meanwhile)
    r = result(decide(c, new, old, "link"))
    status, detail = expected
    assert r["status"] == status and (r.get("side") == detail or r.get("reason") == detail)
    assert store.find(ME, "material_links", "source_id", new["id"]) == []


@pytest.mark.parametrize("item", [
    {"action": "link"},  # link 정보 없음
    {"action": "link", "link": {"target_id": "SELF", "target_version": 1, "decision": "link"}},
    {"action": "link", "link": {"target_id": "x", "target_version": 1, "decision": "maybe"}},
    {"action": "link", "link": {"target_id": "x", "target_version": 1, "decision": "link"}, "changes": {"title": "t"}},
    {"action": "keep", "link": {"target_id": "x", "target_version": 1, "decision": "link"}},
])
def test_link_request_shape_is_validated(item):
    c, store = make_client()
    new, _ = pair(store)
    body = {"material_id": new["id"], "expected_version": 1, **item}
    if body.get("link", {}).get("target_id") == "SELF":
        body["link"]["target_id"] = new["id"]
    assert c.post("/api/reviews/approve", json={"items": [body]}, headers=h()).status_code == 422


def test_keep_still_works_beside_link():
    c, store = make_client()
    new, _ = pair(store)
    keep = {"material_id": new["id"], "expected_version": new["version"]}
    assert result(c.post("/api/reviews/approve", json={"items": [keep]}, headers=h()))["status"] == "approved"
