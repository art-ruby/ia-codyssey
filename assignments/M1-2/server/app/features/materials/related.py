"""관련 자료 제안·연결 기록(PRD §6.4·§9 '관련 자료 연결', T05.02, docs/decisions.md).

- 후보: 같은 모드의 보관 완료 자료(`is_kept`) 중 자기 자신·같은 URL(중복 처리 영역)·이미 판단한 짝을 뺀 것.
- 근거(AI 호출 없이 계산): 같은 프로젝트(사용자가 정한 주·관련), 공통 핵심어(지금 내용 기준 AI 핵심어가 상대 내용에
  있는지), 함께 나오는 내용 단어(제목·설명·본문·저장 이유·메모에서 조사·어미·불용어를 뺀 2자 이상 단어).
- 근거가 약하면 후보로 내지 않는다: (같은 프로젝트 + 단어·핵심어 1개 이상) 또는 핵심어 2개 이상 또는 단어 3개 이상.
- 사용자 판단(연결·관련 없음·해제)은 승인 API(`action=link`)가 짝마다 한 문서(`material_links`)에 기록한다.
  두 자료의 ID·버전, 당시 근거, 시각을 남긴다. 자료 자체의 버전은 올리지 않는다.
- 제안(candidates)과 사용자가 확정한 연결(confirmed)을 따로 돌려준다.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

from app.core.context import RequestContext
from app.core.firestore import NotFound, Store
from app.features.materials import search
from app.features.materials.service import COLLECTION, analysis_outdated, display_title, is_kept
from app.features.projects import service as projects

LINKS = "material_links"
MAX_CANDIDATES = 5
MAX_TERMS_SHOWN = 8
TEXT_FIELDS = ("title", "description", "body", "save_reason", "memo")
# 단어 끝에서 한 번만 떼는 조사·어미(긴 것부터). 떼고 남은 부분이 2자 이상일 때만 뗀다.
_SUFFIXES = sorted({
    "에서는", "으로는", "에서", "으로", "까지", "부터", "에게", "처럼", "보다", "이나", "이라는", "라는",
    "해야", "하다", "한다", "했다", "된다", "되는", "하는", "해서", "하고", "하여", "하며", "합니다",
    "은", "는", "이", "가", "을", "를", "의", "에", "로", "와", "과", "도", "만", "나",
}, key=len, reverse=True)
_STOPWORDS = {
    "있다", "있는", "없는", "위한", "대한", "관련", "내용", "자료", "정리", "다음", "이번", "그리고", "하지만",
    "또는", "그냥", "우리", "모든", "각각", "같은", "the", "and", "for", "with", "this", "that", "from",
}
_WORD = re.compile(r"\w+")


def _norm(text: str | None) -> str:
    return unicodedata.normalize("NFC", text or "").casefold()


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            return word[: -len(suffix)]
    return word


def terms(doc: dict) -> set[str]:
    """사용자가 쓴 내용의 단어 집합. 숫자가 섞인 단어·1자·불용어는 뺀다."""
    words = set()
    for raw in _WORD.findall(" ".join(_norm(doc.get(f)) for f in TEXT_FIELDS)):
        word = _stem(raw)
        if len(word) >= 2 and not any(ch.isdigit() for ch in word) and word not in _STOPWORDS:
            words.add(word)
    return words


def _keywords(doc: dict) -> list[str]:
    usable = doc.get("analysis_status") == "done" and not analysis_outdated(doc)
    return [_norm(k) for k in (doc.get("ai_keywords") or [])] if usable else []


def _project_ids(doc: dict) -> set[str]:
    return {p for p in [doc.get("primary_project_id"), *(doc.get("related_project_ids") or [])] if p}


def same_url(a: dict, b: dict) -> bool:
    return bool(a.get("url_key")) and a.get("url_key") == b.get("url_key")


def evidence_for(a: dict, b: dict, names: dict[str, str]) -> tuple[list[dict], int, bool]:
    """(근거 목록, 점수, 근거가 충분한가). 근거는 화면에 그대로 보여줄 수 있는 형태다."""
    shared_projects = sorted(_project_ids(a) & _project_ids(b))
    a_text = " ".join(_norm(a.get(f)) for f in TEXT_FIELDS)
    b_text = " ".join(_norm(b.get(f)) for f in TEXT_FIELDS)
    hits = {k for k in _keywords(a) if k and k in b_text} | {k for k in _keywords(b) if k and k in a_text}
    shared_terms = sorted(terms(a) & terms(b))
    strong = (bool(shared_projects) and bool(shared_terms or hits)) or len(hits) >= 2 or len(shared_terms) >= 3
    score = 2 * bool(shared_projects) + 2 * len(hits) + len(shared_terms)
    evidence = []
    if shared_projects:
        evidence.append({"type": "project", "label": "같은 프로젝트",
                         "values": [names.get(p, p) for p in shared_projects]})
    if hits:
        evidence.append({"type": "keywords", "label": "공통 핵심어(AI 분석)", "values": sorted(hits)})
    if shared_terms:
        evidence.append({"type": "terms", "label": "함께 나오는 단어", "values": shared_terms[:MAX_TERMS_SHOWN]})
    return evidence, score, strong


def link_id(a_id: str, b_id: str) -> str:
    low, high = sorted([a_id, b_id])
    return hashlib.sha256(f"{low}\n{high}".encode()).hexdigest()[:40]


def links_for(store: Store, ctx: RequestContext, material_id: str) -> dict[str, dict]:
    """이 자료가 들어간 판단 기록. 키는 상대 자료 ID."""
    found = (store.find(ctx, LINKS, "a_id", material_id, limit=100)
             + store.find(ctx, LINKS, "b_id", material_id, limit=100))
    return {(d["b_id"] if d["a_id"] == material_id else d["a_id"]): d for d in found}


def project_names(store: Store, ctx: RequestContext) -> dict[str, str]:
    return {p["id"]: p["name"] for p in projects.list_projects(store, ctx, include_inactive=True)}


def brief(doc: dict) -> dict:
    title, _ = display_title(doc)
    return {"id": doc["id"], "display_title": title, "url": doc.get("url"), "registered_at": doc.get("registered_at"),
            "review_status": doc.get("review_status"), "lifecycle": doc.get("lifecycle"), "version": doc.get("version")}


def related_view(store: Store, ctx: RequestContext, material_id: str) -> dict:
    doc = store.get(ctx, COLLECTION, material_id)  # 남의 자료·다른 모드는 404
    decided = links_for(store, ctx, material_id)
    docs, truncated = search._scan(store, ctx)
    by_id = {d["id"]: d for d in docs}
    names = project_names(store, ctx)

    scored = []
    for other in docs:
        if other["id"] == material_id or not is_kept(other) or same_url(doc, other):
            continue
        if decided.get(other["id"], {}).get("state") in ("linked", "unrelated"):
            continue
        evidence, score, strong = evidence_for(doc, other, names)
        if strong:
            scored.append((score, other.get("registered_at") or "", other, evidence))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    confirmed = []
    for other_id, link in decided.items():
        if link.get("state") != "linked":
            continue
        other = by_id.get(other_id)
        if other is None:
            try:
                other = store.get(ctx, COLLECTION, other_id)
            except NotFound:
                other = None
        confirmed.append({
            "material": brief(other) if other else {"id": other_id, "display_title": "(삭제된 자료)"},
            "state": "linked", "available": bool(other) and is_kept(other),
            "source_id": link["source_id"], "target_id": link["target_id"],
            "source_version": link["source_version"], "target_version": link["target_version"],
            "evidence": link.get("evidence", []), "decided_at": link.get("decided_at"),
        })
    return {
        "candidates": [{"material": brief(o), "evidence": ev, "score": s} for s, _, o, ev in scored[:MAX_CANDIDATES]],
        "confirmed": confirmed,
        "unrelated_count": sum(1 for d in decided.values() if d.get("state") == "unrelated"),
        "scope": {"scanned": len(docs), "truncated": truncated},
    }
