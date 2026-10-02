"""T06.03 표본 seed: 숫자 120건(60일×2지표, 고정 seed)·채팅 근거 자료 20건·평가 질문 13개.

두 번 실행해도 늘지 않고, 사용자가 바꾸거나 지운 표본을 되돌리지 않으며, 개인 자료는 건드리지 않는다.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from app.core.context import RequestContext
from app.core.firestore import MemoryStore
from app.features.data import summary
from app.features.materials.eligibility import material_is_chat_eligible
from app.features.materials.search import SearchFilters, search_materials

OWNER = "owner-1"
ME = RequestContext(OWNER, "personal", None)
SAMPLE = RequestContext(OWNER, "sample", None)
FIXTURES = Path(__file__).parent / "fixtures"
SCRIPT = Path(__file__).parents[1] / "scripts" / "seed_sample.py"


def load_seed():
    spec = importlib.util.spec_from_file_location("seed_sample", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed_module = load_seed()


def cases():
    return json.loads((FIXTURES / "chat_cases.json").read_text(encoding="utf-8"))


# ── 숫자 표본 ─────────────────────────────────────────────────────

def test_sample_numbers_are_fixed_and_well_formed():
    first, second = seed_module.sample_numbers(), seed_module.sample_numbers()
    assert first == second  # 고정 seed
    assert len(first) == 120 and len({(r["metric_type"], r["date"]) for r in first}) == 120
    dates = sorted({r["date"] for r in first})
    assert (dates[0], dates[-1], len(dates)) == ("2026-08-02", "2026-09-30", 60)
    by_day = {}
    for r in first:
        assert isinstance(r["value"], int) and r["value"] >= 0
        by_day.setdefault(r["date"], {})[r["metric_type"]] = r["value"]
    assert all(v["kept_count"] <= v["received_count"] for v in by_day.values())


def test_seed_creates_numbers_materials_and_marker():
    store = MemoryStore()
    report = seed_module.seed(store, OWNER)
    assert report["status"] == "seeded"
    assert (report["data_created"], report["materials_created"]) == (120, 20)
    assert len(store._docs["data"]) == 120 and all(d["mode"] == "sample" and d["origin"] == "sample"
                                                   for d in store._docs["data"].values())
    materials = list(store._docs["materials"].values())
    assert len(materials) == 20 and all(material_is_chat_eligible(m, SAMPLE) for m in materials)
    assert len(store._docs["intake_records"]) == 20
    assert len(store._docs["url_index"]) == sum(1 for m in materials if m["url"])
    assert store.get(SAMPLE, "settings", seed_module.MARKER_ID)["seed_version"] == seed_module.SEED_VERSION


def test_seeded_numbers_drive_sample_summary():
    store = MemoryStore()
    seed_module.seed(store, OWNER)
    s = summary.summarize_data(store, SAMPLE, None, "kept_count", None, None)
    expected = sum(r["value"] for r in seed_module.sample_numbers() if r["metric_type"] == "kept_count")
    assert s["source"] == "sample" and s["label"] == "가상 보관 기록"
    assert (s["total"], s["days"]) == (expected, 60)
    assert s["trend"]["reference_date"] == "2026-09-30" and s["trend"]["status"] == "increase"


def test_running_twice_does_not_duplicate():
    store = MemoryStore()
    seed_module.seed(store, OWNER)
    counts = {name: len(docs) for name, docs in store._docs.items()}
    again = seed_module.seed(store, OWNER)
    assert again["status"] == "already_seeded"
    assert {name: len(docs) for name, docs in store._docs.items()} == counts


def test_rerun_keeps_user_crud_on_sample_numbers():
    store = MemoryStore()
    seed_module.seed(store, OWNER)
    changed_id = seed_module.data_id("kept_count", "2026-09-30")
    deleted_id = seed_module.data_id("kept_count", "2026-09-29")
    store.update(SAMPLE, "data", changed_id, 1, {"value": 99})
    store.delete(SAMPLE, "data", deleted_id)

    report = seed_module.seed(store, OWNER)

    assert store.get(SAMPLE, "data", changed_id)["value"] == 99  # 되돌리지 않는다
    assert deleted_id not in store._docs["data"]  # 다시 만들지 않는다
    assert (report["data_present"], report["data_changed"], report["data_missing"]) == (119, 1, 1)


def test_personal_mode_is_untouched_and_no_pc_records():
    store = MemoryStore()
    store.create(ME, "materials", {"title": "개인 자료", "lifecycle": "active"}, doc_id="personal-1")
    store.create(ME, "data", {"date": "2026-09-01", "metric_type": "kept_count", "value": 1, "origin": "manual"},
                 doc_id="personal-data")
    before = [json.dumps(d, sort_keys=True, default=str) for docs in store._docs.values() for d in docs.values()]
    seed_module.seed(store, OWNER)
    personal_after = [json.dumps(d, sort_keys=True, default=str)
                      for docs in store._docs.values() for d in docs.values() if d.get("mode") == "personal"]
    assert sorted(personal_after) == sorted(before)
    used = {name for name, docs in store._docs.items() if docs}
    assert used <= {"materials", "intake_records", "url_index", "data", "settings"}  # PC 작업 기록 없음


# ── 평가 세트 ─────────────────────────────────────────────────────

def test_chat_cases_have_10_answerable_and_3_unanswerable():
    data = cases()
    assert len(data["answerable"]) == 10 and len(data["no_evidence"]) == 3
    known = {m["id"] for m in json.loads((FIXTURES / "sample_materials.json").read_text(encoding="utf-8"))["materials"]}
    assert all(set(c["expected_ids"]) <= known for c in data["answerable"])
    assert len({c["id"] for c in data["answerable"] + data["no_evidence"]}) == 13


@pytest.mark.parametrize("case", cases()["answerable"], ids=lambda c: c["id"])
def test_key_terms_find_expected_materials_through_search_contract(case):
    store = MemoryStore()
    seed_module.seed(store, OWNER)
    found = {m["id"] for m in search_materials(store, SAMPLE, " ".join(case["key_terms"]), SearchFilters(), None, 50).items}
    assert set(case["expected_ids"]) <= found


@pytest.mark.parametrize("case", cases()["no_evidence"], ids=lambda c: c["id"])
def test_no_evidence_terms_match_nothing(case):
    store = MemoryStore()
    seed_module.seed(store, OWNER)
    for term in case["key_terms"]:
        assert search_materials(store, SAMPLE, term, SearchFilters(), None, 50).total_matches == 0
