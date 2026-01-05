import re
import pytest

pytestmark = pytest.mark.end_to_end
def _import_psyprov():
    import importlib
    pkg = importlib.import_module("psyprov")
    schemas = importlib.import_module("psyprov.schemas")
    heuristics = importlib.import_module("psyprov.heuristics") if importlib.util.find_spec("psyprov.heuristics") else None
    planner = importlib.import_module("psyprov.planner") if importlib.util.find_spec("psyprov.planner") else None
    plan = importlib.import_module("psyprov.plan") if importlib.util.find_spec("psyprov.plan") else None
    return pkg, schemas, heuristics, planner, plan
def test_metadata_schema_model_and_json_schema_export():
    _, schemas, _, _, _ = _import_psyprov()
    assert hasattr(schemas, "CitationRecord"), "schemas.CitationRecord model missing"
    assert hasattr(schemas, "ProvenanceMetadata"), "schemas.ProvenanceMetadata model missing"
    CitationRecord = schemas.CitationRecord
    ProvenanceMetadata = schemas.ProvenanceMetadata

    example = {
        "work": {
            "title": "The Interpretation of Dreams",
            "author": "Sigmund Freud",
            "original_year": 1899,
        },
        "edition": {
            "edition_label": "Standard Edition",
            "publisher": "Hogarth Press",
            "year": 1953,
            "language": "en",
        },
        "translation": {
            "translator": "James Strachey",
            "source_language": "de",
            "target_language": "en",
        },
        "locators": {
            "page": {"printed": "123", "pdf": "140", "variant_note": "PDF pagination differs from print."},
            "paragraph": {"index": 4, "scheme": "section-paragraph"},
        },
        "repository_citation": {
            "repository": "Internet Archive",
            "url": "https://archive.org/details/example",
            "accessed": "2025-12-26",
            "public_domain_claim": True,
            "checksum": {"alg": "sha256", "value": "0" * 64},
        },
        "generated_by": {"tool": "psyprov", "version": "0.1.0"},
    }

    m = ProvenanceMetadata.model_validate(example)
    assert m.work.title and m.edition.year >= 1800
    s = ProvenanceMetadata.model_json_schema()
    assert isinstance(s, dict) and "properties" in s and s.get("title"), "JSON Schema export malformed"

    c = CitationRecord.model_validate(example["repository_citation"])
    assert re.match(r"^https?://", c.url)
def test_plan_includes_required_sections_and_priorities():
    _, _, _, planner, planmod = _import_psyprov()
    gen = None
    for mod in (planner, planmod):
        if mod and hasattr(mod, "generate_plan"):
            gen = getattr(mod, "generate_plan")
            break
    assert gen is not None, "Missing plan generator function psyprov.(planner|plan).generate_plan"

    plan = gen(mission="primary-source psychology provenance", stage=1)
    assert isinstance(plan, dict), "Plan must be a dict-like JSON-serializable object"

    required_top = {"mission_summary", "prioritized_task_breakdown", "metadata_schema", "ui_ux_requirements", "heuristics", "evaluation_protocol"}
    assert required_top.issubset(plan.keys()), f"Plan missing required sections: {sorted(required_top - set(plan.keys()))}"

    tasks = plan["prioritized_task_breakdown"]
    assert isinstance(tasks, list) and tasks, "prioritized_task_breakdown must be a non-empty list"
    for t in tasks[:10]:
        assert isinstance(t, dict) and "priority" in t and "title" in t and "acceptance_criteria" in t
        assert t["priority"] in {"P0", "P1", "P2"}, "priority must be one of P0/P1/P2"

    # Must cover checklists/specs explicitly
    text_blob = json.dumps(plan).lower()
    for kw in ["checklist", "metadata", "ui/ux", "heuristic", "survey", "audit", "protocol", "variant page", "paragraph"]:
        assert kw.replace(" ", "") in text_blob.replace(" ", ""), f"Plan content missing keyword: {kw}
def test_heuristics_are_deterministic():
    _, _, heuristics, _, _ = _import_psyprov()
    assert heuristics is not None, "psyprov.heuristics module missing"
    assert hasattr(heuristics, "detect_provenance"), "heuristics.detect_provenance missing"
    detect = heuristics.detect_provenance

    sample = {
        "citation": "Freud, S. (1953). The Interpretation of Dreams (J. Strachey, Trans.). Hogarth Press. Internet Archive: https://archive.org/details/example",
        "snippet": "SE Vol. IV, p. 123; para. 4. PDF p. 140.",
    }
    r1 = detect(sample)
    r2 = detect(sample)
    assert r1 == r2, "Heuristic output must be deterministic for identical inputs"
    assert isinstance(r1, dict), "detect_provenance must return a dict"
    for k in ["edition", "translation", "locators", "repository_citation"]:
        assert k in r1, f"Heuristic result missing key: {k}
