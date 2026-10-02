"""T05.04 검색·채팅에 전달할 자료의 공통 필터: 한 조건씩 바꾼 표본의 허용/거부, 보관함 표시와 AI 문맥의 구분,
질문 때 다시 읽어 거르기, 실제 Provider 요청 캡처에 금지 자료가 없는지.
"""

from __future__ import annotations

import json

import pytest

from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.analysis.provider import AnalysisAdapter, TextResult
from app.features.materials import eligibility
from app.features.materials.eligibility import (AI_CONTEXT_FIELDS, library_visible, material_is_chat_eligible,
                                                refresh_and_filter, select_ai_context)

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)


def doc(**overrides) -> dict:
    base = {"id": "m1", "owner_id": OWNER, "mode": "personal", "title": "허용 자료", "body": "허용 본문",
            "review_status": "approved", "copy_status": "not_applicable", "lifecycle": "active",
            "ai_excluded": False, "registered_at": "2026-10-02T00:00:00+00:00", "version": 1}
    base.update(overrides)
    return base


# ── 한 조건씩 ─────────────────────────────────────────────────────

def test_kept_active_not_excluded_material_is_eligible():
    assert material_is_chat_eligible(doc(), ME) is True
    assert eligibility.exclusion_reason(doc(), ME) is None


@pytest.mark.parametrize("change, reason", [
    ({"owner_id": "someone-else"}, "not_found"),
    ({"mode": "sample"}, "not_found"),
    ({"review_status": "unreviewed"}, "unapproved"),
    ({"review_status": "later"}, "unapproved"),
    ({"copy_status": "pending"}, "not_kept"),
    ({"lifecycle": "trash"}, "trashed"),
    ({"lifecycle": "deleting"}, "trashed"),
    ({"ai_excluded": True}, "ai_excluded"),
])
def test_each_single_condition_blocks_ai_context(change, reason):
    material = doc(**change)
    assert material_is_chat_eligible(material, ME) is False
    assert eligibility.exclusion_reason(material, ME) == reason


def test_missing_material_is_not_eligible():
    assert material_is_chat_eligible(None, ME) is False
    assert eligibility.exclusion_reason(None, ME) == "not_found"


def test_library_and_ai_context_differ_for_ai_excluded():
    excluded = doc(ai_excluded=True)
    assert library_visible(excluded, ME) is True  # 보관함에는 보인다
    assert material_is_chat_eligible(excluded, ME) is False  # AI 문맥에는 제목도 보내지 않는다(Open Decision 5 전)
    assert library_visible(doc(review_status="unreviewed"), ME) is False
    assert library_visible(doc(lifecycle="trash"), ME) is False


# ── 문맥 고르기 ───────────────────────────────────────────────────

def test_select_ai_context_keeps_order_and_counts_reasons():
    materials = [doc(id="a"), doc(id="b", ai_excluded=True), doc(id="c", lifecycle="trash"),
                 doc(id="d", review_status="unreviewed"), doc(id="e")]
    picked = select_ai_context(materials, ME)
    assert [m["id"] for m in picked.allowed] == ["a", "e"]
    assert picked.excluded == {"ai_excluded": 1, "trashed": 1, "unapproved": 1}


def test_payload_contains_only_user_content_and_registered_date():
    material = doc(ai_summary="AI 요약", ai_keywords=["k"], memo="메모", url="https://example.com",
                   analysis_job_id="j", deletion_job_id="d")
    payload = eligibility.ai_payload(material)
    assert set(AI_CONTEXT_FIELDS) == {"title", "description", "body", "save_reason", "memo", "url", "registered_at"}
    assert set(payload) <= set(AI_CONTEXT_FIELDS) and "registered_at" in payload
    assert "owner_id" not in payload and "ai_summary" not in payload and "mode" not in payload and "id" not in payload


def test_refresh_rereads_each_material_before_use():
    store = MemoryStore()
    fields = {k: v for k, v in doc().items() if k not in ("id", "owner_id", "mode", "version")}
    ok = store.create(ME, "materials", fields, doc_id="ok")
    gone = store.create(ME, "materials", fields, doc_id="gone")
    later_trashed = store.create(ME, "materials", fields, doc_id="trashed")
    later_excluded = store.create(ME, "materials", fields, doc_id="excluded")
    store.create(RequestContext(OWNER, "sample", None), "materials", fields, doc_id="sample-one")
    # 이전 대화 이후에 바뀐 상태
    store.delete(ME, "materials", gone["id"])
    store.update(ME, "materials", later_trashed["id"], 1, {"lifecycle": "trash"})
    store.update(ME, "materials", later_excluded["id"], 1, {"ai_excluded": True})

    picked = refresh_and_filter(store, ME, ["ok", "gone", "trashed", "excluded", "sample-one", "ok"])

    assert [m["id"] for m in picked.allowed] == [ok["id"]]  # 중복 제거, 순서 유지
    assert picked.excluded == {"not_found": 2, "trashed": 1, "ai_excluded": 1}


# ── 실제 Provider 요청 캡처 ───────────────────────────────────────

class CapturingCompleter:
    def __init__(self):
        self.sent = []

    def complete_text(self, messages):
        self.sent.append(messages)
        return TextResult(text="답변", model="gpt-6-luna", total_tokens=10)


def test_provider_request_never_contains_forbidden_materials():
    store = MemoryStore()
    allowed = {"title": "허용된 자료 제목", "body": "허용된 본문 ALLOWEDBODY"}
    forbidden = {
        "excluded": {"title": "제외된 제목 EXCLUDEDTITLE", "body": "제외 본문 EXCLUDEDBODY", "ai_excluded": True},
        "trashed": {"title": "휴지통 제목 TRASHTITLE", "body": "휴지통 본문 TRASHBODY", "lifecycle": "trash"},
        "unapproved": {"title": "미승인 제목 UNAPPROVEDTITLE", "body": "미승인 본문", "review_status": "unreviewed"},
    }
    base = {k: v for k, v in doc().items() if k not in ("id", "owner_id", "mode", "version")}
    store.create(ME, "materials", {**base, **allowed}, doc_id="allowed")
    for name, fields in forbidden.items():
        store.create(ME, "materials", {**base, **fields}, doc_id=name)

    picked = refresh_and_filter(store, ME, ["allowed", *forbidden])
    capture = CapturingCompleter()
    context = [eligibility.ai_payload(m) for m in picked.allowed]
    AnalysisAdapter(capture).answer_question([
        {"role": "system", "content": "자료 문맥만 근거로 답한다."},
        {"role": "user", "content": json.dumps({"materials": context, "question": "정리해 줘"}, ensure_ascii=False)},
    ])

    sent = json.dumps(capture.sent, ensure_ascii=False)
    assert "ALLOWEDBODY" in sent
    for word in ("EXCLUDEDTITLE", "EXCLUDEDBODY", "TRASHTITLE", "TRASHBODY", "UNAPPROVEDTITLE"):
        assert word not in sent
    for name in forbidden:
        assert f'"{name}"' not in sent  # 자료 ID도 보내지 않는다
