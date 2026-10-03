"""채팅 검색 품질 평가(T07.04, A14). 고정 표본(seed_sample)과 평가 세트(chat_cases.json)로 채점한다.

- 실제 검색·채팅 경로(`handle_chat`: 검색 모듈 순위 → 자격 필터 → 서버 출처 대조)를 그대로 돌리고 Provider만
  가짜로 바꾼다. 가짜는 받은 자료를 모두 인용하고 없는 번호(99)도 하나 끼워 넣어 출처 대조를 시험한다.
- 질문마다 기대 자료·실제 전달 자료·찾음 여부·실패 원인과, 검색 계약(`search_materials`)으로 핵심어를 찾았는지 낸다.
- 실행: `python server/scripts/evaluate_chat.py` → 마크다운 표 출력. Provider 호출 없음.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.context import RequestContext  # noqa: E402
from app.core.firestore import MemoryStore  # noqa: E402
from app.features.analysis.provider import TextResult  # noqa: E402
from app.features.chat import context as chat_context  # noqa: E402
from app.features.chat import service  # noqa: E402
from app.features.materials.search import SearchFilters, search_materials  # noqa: E402

OWNER = "eval-owner"
CTX = RequestContext(OWNER, "sample", None)
CASES = json.loads((Path(__file__).parents[1] / "tests" / "fixtures" / "chat_cases.json").read_text(encoding="utf-8"))
FAKE_NUMBER = 99


def seeded_store() -> MemoryStore:
    spec = importlib.util.spec_from_file_location("seed_sample", Path(__file__).with_name("seed_sample.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store = MemoryStore()
    module.seed(store, OWNER)
    return store


class CiteEverything:
    """받은 자료 번호를 모두 인용하고, 없는 번호 하나를 더 대는 가짜 Provider."""

    def answer_question(self, messages):
        content = messages[0]["content"]
        reference = json.loads(content.split(chat_context.REFERENCE_START)[1].split(chat_context.REFERENCE_END)[0])
        numbers = [m["자료 번호"] for m in reference["materials"]]
        reply = {"from_materials": "", "interpretation": "", "sources": [*numbers, FAKE_NUMBER]}
        return TextResult(json.dumps(reply), "fake", 0)


def _search_finds(store: MemoryStore, case: dict) -> list[str]:
    page = search_materials(store, CTX, " ".join(case["key_terms"]), SearchFilters(), limit=50)
    return [item["id"] for item in page.items]


def _terms(question: str) -> list[str]:
    return chat_context.extract_conditions(question, chat_context._now().astimezone(chat_context.SEOUL).date()).terms


def evaluate(store: MemoryStore | None = None) -> dict:
    store = store or seeded_store()
    known = {d["id"] for d in store.list(CTX, "materials", limit=100).items}
    rows = []
    for kind in ("answerable", "no_evidence"):
        for case in CASES[kind]:
            ctx = RequestContext(OWNER, "sample", f"eval-{case['id']}")
            status, body = service.handle_chat(store, ctx, None, case["question"], CiteEverything, 10_000)
            found = [s["material_id"] for s in body["sources"]]
            expected = case.get("expected_ids", [])
            if kind == "answerable":
                ok = set(expected) <= set(found)
                reason = "" if ok else f"검색어 {_terms(case['question'])}로 기대 자료를 찾지 못함"
            else:
                ok = not found and body["answer"]["limitations"][:1] == [service.NO_MATERIALS]
                reason = "" if ok else "근거 없는 질문에 자료가 잡히거나 한계 문구 없음"
            rows.append({"id": case["id"], "kind": kind, "question": case["question"], "expected": expected,
                         "found": found, "ok": ok, "reason": reason,
                         "invented": [m for m in found if m not in known],
                         "rejected": body["rejected_source_numbers"], "status": status,
                         "search_contract": _search_finds(store, case)})
    answerable = [r for r in rows if r["kind"] == "answerable"]
    no_evidence = [r for r in rows if r["kind"] == "no_evidence"]
    return {"rows": rows, "answerable_found": sum(r["ok"] for r in answerable), "answerable_total": len(answerable),
            "no_evidence_ok": sum(r["ok"] for r in no_evidence), "no_evidence_total": len(no_evidence),
            "invented_sources": sum(len(r["invented"]) for r in rows)}


def markdown(result: dict) -> str:
    lines = ["| 질문 | 기대 자료 | 실제 근거 자료(전달·인용) | 결과 | 실패 원인 | 검색 계약(핵심어) |",
             "|---|---|---|---|---|---|"]
    for r in result["rows"]:
        if r["expected"] and set(r["expected"]) <= set(r["search_contract"]):
            contract = "기대 자료 포함"
        else:
            contract = f"{len(r['search_contract'])}건"
        lines.append(f"| {r['id']} {r['question']} | {', '.join(r['expected']) or '없음'} | "
                     f"{', '.join(r['found']) or '없음'} | {'통과' if r['ok'] else '실패'} | {r['reason'] or '-'} | {contract} |")
    lines.append("")
    lines.append(f"정답 질문 {result['answerable_found']}/{result['answerable_total']}, "
                 f"근거 없는 질문 한계 표시 {result['no_evidence_ok']}/{result['no_evidence_total']}, "
                 f"존재하지 않는 출처 {result['invented_sources']}건(가짜 Provider가 댄 번호 {FAKE_NUMBER}는 모두 거부)")
    return "\n".join(lines)


if __name__ == "__main__":
    print(markdown(evaluate()))
