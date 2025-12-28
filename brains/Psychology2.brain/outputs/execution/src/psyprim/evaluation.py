"""Survey + audit-study scaffolding for PsyPrim.

Provides: instrument templates, sampling plan template, audit rubric template,
and utilities to export analysis-ready JSON/CSV artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import csv
import json
import uuid
import datetime as _dt

__all__ = [
    "survey_instrument_template",
    "sampling_plan_template",
    "audit_rubric_template",
    "make_survey_response_sheet",
    "make_audit_case_sheet",
    "export_json",
    "export_csv",
    "export_instrument_bundle",
]


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def export_json(obj: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _flatten(obj: Any, prefix: str = "", out: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    out = out or {}
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            _flatten(v, f"{prefix}{k}.", out)
    elif isinstance(obj, list):
        out[prefix[:-1]] = json.dumps(obj, ensure_ascii=False)
    else:
        out[prefix[:-1]] = "" if obj is None else str(obj)
    return out


def export_csv(rows: Sequence[Mapping[str, Any]], path: Path, field_order: Optional[List[str]] = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    flat = [_flatten(r) for r in rows]
    fields = field_order or sorted({k for r in flat for k in r.keys()})
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in flat:
            w.writerow({k: r.get(k, "") for k in fields})
    return path
def survey_instrument_template(version: str = "1.0") -> Dict[str, Any]:
    """Standard survey instrument focusing on primary-source workflow + tooling."""
    return {
        "schema": "psyprim.survey.instrument",
        "version": version,
        "created_utc": _now_iso(),
        "title": "Primary-source scholarship workflow evaluation (survey)",
        "audience": [
            "psychology_researchers",
            "students",
            "librarians/archivists",
            "open_science_practitioners",
        ],
        "constructs": [
            {"id": "C1", "name": "metadata_comprehension"},
            {"id": "C2", "name": "workflow_usability"},
            {"id": "C3", "name": "trust_in_provenance"},
            {"id": "C4", "name": "time_cost"},
            {"id": "C5", "name": "adoption_intent"},
        ],
        "scales": {
            "likert_1_7": {"min": 1, "max": 7, "anchors": {1: "Strongly disagree", 4: "Neutral", 7: "Strongly agree"}},
            "confidence_0_100": {"min": 0, "max": 100, "anchors": {0: "Not confident", 100: "Fully confident"}},
        },
        "items": [
            {"id": "S01", "type": "consent", "text": "I consent to participate; responses will be analyzed in aggregate.", "required": True},
            {"id": "S02", "type": "single_choice", "construct": None, "text": "Primary role", "options": ["undergrad", "grad", "postdoc", "faculty", "librarian/archivist", "independent", "other"], "required": True},
            {"id": "S03", "type": "single_choice", "construct": None, "text": "Primary subfield", "options": ["clinical", "cognitive", "developmental", "social", "I/O", "neuroscience", "history/theory", "methods", "other"], "required": True},
            {"id": "S04", "type": "multi_choice", "construct": None, "text": "Sources used in past 12 months", "options": ["journal_articles", "books", "archival_scans", "public_domain_editions", "translations", "microfilm", "other"], "required": True},
            {"id": "S10", "type": "likert", "construct": "C1", "scale": "likert_1_7", "text": "I can reliably identify the edition/version of a primary source I cite."},
            {"id": "S11", "type": "likert", "construct": "C1", "scale": "likert_1_7", "text": "I can document translation provenance (translator, year, publisher, basis text) when relevant."},
            {"id": "S12", "type": "likert", "construct": "C1", "scale": "likert_1_7", "text": "I can handle variant pagination (different printings/editions) in citations without confusion."},
            {"id": "S13", "type": "likert", "construct": "C3", "scale": "likert_1_7", "text": "I trust citations more when a scan/identifier and public-domain status are recorded."},
            {"id": "S20", "type": "likert", "construct": "C2", "scale": "likert_1_7", "text": "A standardized checklist would reduce my errors in primary-source metadata."},
            {"id": "S21", "type": "likert", "construct": "C2", "scale": "likert_1_7", "text": "A lightweight CLI tool would fit my workflow (notes, Zotero, scripts)."},
            {"id": "S22", "type": "likert", "construct": "C4", "scale": "likert_1_7", "text": "The added time to record provenance is acceptable for my projects."},
            {"id": "S23", "type": "number", "construct": "C4", "text": "Estimated minutes per primary source to record provenance + pagination variants", "min": 0, "max": 240},
            {"id": "S24", "type": "likert", "construct": "C5", "scale": "likert_1_7", "text": "I would adopt a standardized workflow if peers/journals recommended it."},
            {"id": "S30", "type": "open_text", "construct": None, "text": "Biggest pain point in primary-source citation/provenance today"},
            {"id": "S31", "type": "open_text", "construct": None, "text": "What feature would most increase trust/reproducibility for primary sources?"},
        ],
        "analysis_hints": {
            "role_weighting": "Consider stratified analyses by role/subfield.",
            "primary_outcomes": ["S20", "S21", "S24"],
            "time_cost_field": "S23",
        },
    }


def sampling_plan_template(version: str = "1.0") -> Dict[str, Any]:
    """Sampling plan template for surveys + audit studies (implementable)."""
    return {
        "schema": "psyprim.evaluation.sampling_plan",
        "version": version,
        "created_utc": _now_iso(),
        "targets": {
            "survey_n": 60,
            "audit_cases_n": 24,
            "audit_raters_n": 2,
            "power_notes": "Aim to detect medium effects in usability/adoption outcomes; focus on descriptive precision in Stage 1.",
        },
        "strata": [
            {"name": "role", "levels": ["grad", "faculty", "librarian/archivist", "other"], "min_per_level": 10},
            {"name": "subfield", "levels": ["cognitive", "clinical", "social", "history/theory", "methods", "other"], "min_per_level": 6},
            {"name": "language_context", "levels": ["english_only", "translation_involved", "multilingual"], "min_per_level": 8},
        ],
        "recruitment_channels": [
            "society_listservs",
            "departmental_methods_groups",
            "library_scholarly_comm_groups",
            "history_of_psychology networks",
            "open_science communities",
        ],
        "inclusion_criteria": [
            "Has cited or analyzed a primary source (original text/edition/scan) in last 24 months OR supports such work (librarian/archivist).",
        ],
        "randomization": {
            "survey_item_order": "block_randomization_within_construct",
            "audit_case_assignment": "balanced_incomplete_block: each case rated by >=2 raters; each rater sees ~12 cases",
        },
        "data_management": {
            "id_strategy": "assign pseudonymous respondent_id/rater_id; store contact separately",
            "export_formats": ["json", "csv"],
            "privacy": "avoid collecting direct identifiers in response files",
        },
    }
def audit_rubric_template(version: str = "1.0") -> Dict[str, Any]:
    """Audit rubric for evaluating primary-source metadata + citation quality."""
    dims = [
        ("edition_provenance", "Edition is uniquely identifiable (publisher/year/printing/ID) and tied to evidence (scan/URL/DOI/IA/Hathi)."),
        ("translation_provenance", "Translation details recorded (translator/year/publisher/source text) and justified when used."),
        ("variant_pagination", "Crosswalk/notes provided for pagination variants; quoted passages locatable across editions."),
        ("public_domain_citations", "Public-domain status and access pathway cited when applicable (jurisdiction/date/source)."),
        ("metadata_completeness", "Checklist fields are complete, consistent, and machine-parseable."),
        ("reproducibility", "Another researcher can retrieve the same primary source and locate cited passage without extra info."),
    ]
    scale = {
        "0": "Absent/incorrect",
        "1": "Partial/ambiguous",
        "2": "Complete/verified",
    }
    return {
        "schema": "psyprim.audit.rubric",
        "version": version,
        "created_utc": _now_iso(),
        "title": "Primary-source workflow audit rubric",
        "scale": {"min": 0, "max": 2, "anchors": scale},
        "dimensions": [
            {"id": f"D{i+1:02d}", "key": k, "description": d, "evidence_required": ["citation", "metadata_record", "access_link_or_identifier"]}
            for i, (k, d) in enumerate(dims)
        ],
        "global_fields": [
            {"key": "case_id", "type": "string"},
            {"key": "rater_id", "type": "string"},
            {"key": "project_context", "type": "string"},
            {"key": "notes", "type": "string"},
        ],
        "scoring_notes": [
            "Use 2 only when evidence allows independent retrieval and verification.",
            "If dimension not applicable (e.g., no translation), mark score as 'NA' and provide brief justification.",
        ],
    }


def make_survey_response_sheet(instrument: Optional[Mapping[str, Any]] = None, n_rows: int = 0) -> List[Dict[str, Any]]:
    """Create an analysis-ready row schema for survey responses (optionally with blank rows)."""
    instrument = instrument or survey_instrument_template()
    item_ids = [it["id"] for it in instrument.get("items", []) if it.get("type") not in ("consent",)]
    base = {
        "schema": "psyprim.survey.responses",
        "instrument_version": instrument.get("version"),
        "respondent_id": "",
        "submitted_utc": "",
    }
    row = {**base, **{iid: "" for iid in item_ids}}
    return [dict(row) for _ in range(n_rows)]


def make_audit_case_sheet(
    rubric: Optional[Mapping[str, Any]] = None,
    cases: Optional[Sequence[Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Create analysis-ready audit rows; if cases provided, expands to per-case rows (no rater assignment)."""
    rubric = rubric or audit_rubric_template()
    dim_keys = [d["key"] for d in rubric.get("dimensions", [])]
    def row_for(case: Mapping[str, Any]) -> Dict[str, Any]:
        base = {
            "schema": "psyprim.audit.scores",
            "rubric_version": rubric.get("version"),
            "case_id": case.get("case_id", _uid("case")),
            "rater_id": "",
            "project_context": case.get("project_context", ""),
            "primary_source_citation": case.get("primary_source_citation", ""),
            "metadata_record_path": case.get("metadata_record_path", ""),
            "evidence_links": case.get("evidence_links", []),
            "notes": "",
        }
        for k in dim_keys:
            base[f"score.{k}"] = ""
            base[f"justification.{k}"] = ""
        return base
    if not cases:
        return [row_for({})]
    return [row_for(c) for c in cases]


def export_instrument_bundle(out_dir: Path) -> Dict[str, str]:
    """Write JSON + CSV templates for survey + audit to out_dir."""
    out_dir = Path(out_dir)
    survey = survey_instrument_template()
    rubric = audit_rubric_template()
    sampling = sampling_plan_template()
    survey_rows = make_survey_response_sheet(survey, n_rows=0)
    audit_rows = make_audit_case_sheet(rubric, cases=None)
    paths = {
        "survey_instrument_json": str(export_json(survey, out_dir / "survey_instrument.json")),
        "sampling_plan_json": str(export_json(sampling, out_dir / "sampling_plan.json")),
        "audit_rubric_json": str(export_json(rubric, out_dir / "audit_rubric.json")),
        "survey_responses_csv": str(export_csv(survey_rows, out_dir / "survey_responses_template.csv")),
        "audit_scores_csv": str(export_csv(audit_rows, out_dir / "audit_scores_template.csv")),
    }
    return paths
