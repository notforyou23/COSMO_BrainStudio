"""psyprim.instruments

Templates/builders for: surveys, audit-study coding sheets, metadata checklists, rubrics.
Designed for validating primary-source scholarship in psychology with lightweight tooling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

Scale = Dict[str, Any]
Item = Dict[str, Any]
Instrument = Dict[str, Any]


def likert_scale(points: int = 5, anchors: Optional[Sequence[str]] = None) -> Scale:
    if points not in (4, 5, 7):
        raise ValueError("points must be one of {4,5,7}")
    if anchors is None:
        anchors = ("Strongly disagree", "Disagree", "Neutral", "Agree", "Strongly agree") if points == 5 else None
    labels = list(anchors) if anchors else [str(i) for i in range(1, points + 1)]
    return {"type": "likert", "points": points, "labels": labels}


def make_item(
    item_id: str,
    prompt: str,
    response: str,
    *,
    scale: Optional[Scale] = None,
    required: bool = True,
    tags: Optional[Sequence[str]] = None,
    notes: Optional[str] = None,
) -> Item:
    return {
        "id": item_id,
        "prompt": prompt,
        "response": response,
        "scale": scale,
        "required": required,
        "tags": list(tags or []),
        "notes": notes,
    }


def open_text(item_id: str, prompt: str, *, required: bool = False, tags: Sequence[str] = ()) -> Item:
    return make_item(item_id, prompt, "text", required=required, tags=tags)


def multi_select(item_id: str, prompt: str, options: Sequence[str], *, required: bool = True, tags: Sequence[str] = ()) -> Item:
    return make_item(item_id, prompt, "multi_select", required=required, tags=tags, scale={"options": list(options)})


def single_select(item_id: str, prompt: str, options: Sequence[str], *, required: bool = True, tags: Sequence[str] = ()) -> Item:
    return make_item(item_id, prompt, "single_select", required=required, tags=tags, scale={"options": list(options)})


@dataclass(frozen=True)
class InstrumentSpec:
    name: str
    version: str = "1.0"
    population: str = "researchers"
    mode: str = "online"
    description: str = ""


def build_survey_primary_source_practices(spec: InstrumentSpec = InstrumentSpec("primary_source_practices")) -> Instrument:
    s5 = likert_scale(5)
    items: List[Item] = [
        make_item("S1_role", "Your primary role", "single_select",
                  scale={"options": ["Faculty", "Graduate student", "Undergraduate", "Librarian/Archivist", "Other"]},
                  required=True, tags=["demographics"]),
        make_item("S2_subfield", "Primary subfield(s) (select all that apply)", "multi_select",
                  scale={"options": ["Clinical", "Cognitive", "Developmental", "Social", "History/Philosophy", "Methods", "Other"]},
                  required=False, tags=["demographics"]),
        make_item("S3_primary_source_use", "In the past 24 months, how often did you consult primary sources (original editions/translations/archives)?",
                  "single_select", scale={"options": ["Never", "1-2 times", "3-5 times", "6-10 times", "11+ times"]},
                  required=True, tags=["behavior"]),
        make_item("S4_confidence", "I can reliably distinguish primary vs. secondary sources in my domain.", "likert", scale=s5,
                  required=True, tags=["self_efficacy"]),
        make_item("S5_provenance", "I record edition/translation provenance when citing historical texts.", "likert", scale=s5,
                  required=True, tags=["practice", "provenance"]),
        make_item("S6_pagination", "I verify page/section alignment when using scans with variant pagination.", "likert", scale=s5,
                  required=True, tags=["practice", "pagination"]),
        make_item("S7_repo_cite", "I include stable repository identifiers (e.g., DOI/ARK/handle/catalog record URL) when citing primary sources.", "likert", scale=s5,
                  required=True, tags=["practice", "repository"]),
        make_item("S8_barriers", "What are your main barriers to using/verifying primary sources? (select all)", "multi_select",
                  scale={"options": ["Access restrictions", "Time", "Language/translation", "Unclear editions", "Poor scans", "Citation uncertainty", "Lack of training", "Other"]},
                  required=False, tags=["barriers"]),
        open_text("S9_tools", "Which repositories or tools do you use for locating/verifying primary sources? (e.g., HathiTrust, IA, Gallica)", required=False, tags=["resources"]),
        open_text("S10_examples", "Provide one example (optional) of a primary-source citation you found difficult to verify, and why.", required=False, tags=["qualitative"]),
    ]
    return {
        "spec": spec.__dict__,
        "sections": [
            {"id": "sec_demo", "title": "Background", "items": ["S1_role", "S2_subfield"]},
            {"id": "sec_practice", "title": "Practices", "items": ["S3_primary_source_use", "S4_confidence", "S5_provenance", "S6_pagination", "S7_repo_cite"]},
            {"id": "sec_barriers", "title": "Barriers & Resources", "items": ["S8_barriers", "S9_tools", "S10_examples"]},
        ],
        "items": items,
        "scoring": {
            "indices": {
                "primary_source_rigor": {"items": ["S5_provenance", "S6_pagination", "S7_repo_cite"], "method": "mean_likert_1_5"},
                "self_efficacy": {"items": ["S4_confidence"], "method": "likert_1_5"},
            }
        },
    }


def build_audit_coding_sheet(spec: InstrumentSpec = InstrumentSpec("audit_study_coding_sheet", population="coders", mode="spreadsheet")) -> Instrument:
    fields = [
        {"id": "A1_paper_id", "type": "string", "required": True, "desc": "Unique paper identifier"},
        {"id": "A2_venue_year", "type": "string", "required": True, "desc": "Venue and year"},
        {"id": "A3_claim_primary_source", "type": "boolean", "required": True, "desc": "Paper claims primary-source use"},
        {"id": "A4_citation_text", "type": "string", "required": True, "desc": "Extracted citation(s) to primary source(s)"},
        {"id": "A5_edition_present", "type": "single_select", "required": True, "options": ["Yes", "No", "Unclear"], "desc": "Edition stated (year/printing/version)"},
        {"id": "A6_translation_present", "type": "single_select", "required": True, "options": ["N/A", "Yes", "No", "Unclear"], "desc": "Translator/translation edition stated"},
        {"id": "A7_repo_identifier", "type": "single_select", "required": True, "options": ["Yes", "No", "Unclear"], "desc": "Repository identifier/URL/DOI/ARK/handle present"},
        {"id": "A8_variant_pagination_risk", "type": "single_select", "required": True, "options": ["Low", "Medium", "High"], "desc": "Scan/edition likely to have pagination variance"},
        {"id": "A9_verifiable", "type": "single_select", "required": True, "options": ["Yes", "No", "Partial"], "desc": "Coder could locate and verify cited passage/page"},
        {"id": "A10_notes", "type": "string", "required": False, "desc": "Coder notes / ambiguity"},
    ]
    decision_rules = [
        "Edition present: includes publication year AND edition/printing markers (e.g., 2nd ed., vol., revised).",
        "Translation present: includes translator name OR explicitly names translation edition/year/publisher.",
        "Repository identifier: stable identifier preferred (DOI/ARK/handle/catalog record); bare homepage counts as 'Unclear'.",
        "Verifiable: coder can retrieve referenced object and match cited location (page/section/plate) with reasonable effort (<15 min).",
    ]
    return {"spec": spec.__dict__, "fields": fields, "decision_rules": decision_rules}


def build_metadata_checklist(spec: InstrumentSpec = InstrumentSpec("metadata_checklist", population="authors", mode="document")) -> Instrument:
    checks = [
        {"id": "M1_work_author", "label": "Work author(s) recorded", "required": True, "evidence": "citation"},
        {"id": "M2_work_title", "label": "Work title recorded", "required": True, "evidence": "citation"},
        {"id": "M3_edition_statement", "label": "Edition/printing/version statement recorded", "required": True, "evidence": "citation/note"},
        {"id": "M4_pub_year_place_publisher", "label": "Publication year/place/publisher recorded", "required": True, "evidence": "citation"},
        {"id": "M5_translation_provenance", "label": "Translation provenance (translator + edition/year) recorded where applicable", "required": True, "evidence": "citation/note"},
        {"id": "M6_repository_citation", "label": "Repository citation with stable identifier (DOI/ARK/handle/catalog record URL)", "required": True, "evidence": "reference list"},
        {"id": "M7_locator", "label": "Passage locator provided (page/section/para/plate) with awareness of variant pagination", "required": True, "evidence": "in-text cite"},
        {"id": "M8_access_date", "label": "Access date recorded for online facsimiles", "required": False, "evidence": "citation"},
        {"id": "M9_rights", "label": "Rights/licensing noted if reusing images/plates", "required": False, "evidence": "caption/acknowledgment"},
        {"id": "M10_link_rot_mitigation", "label": "Link-rot mitigation (permalink + archived copy if possible)", "required": False, "evidence": "citation"},
    ]
    return {"spec": spec.__dict__, "checklist": checks, "format": {"statuses": ["Yes", "No", "N/A"], "notes_field": "notes"}}


def build_rubric_primary_source_validation(spec: InstrumentSpec = InstrumentSpec("validation_rubric", population="reviewers", mode="form")) -> Instrument:
    levels = ["0-absent", "1-minimal", "2-adequate", "3-exemplary"]
    criteria = [
        {"id": "R1_provenance", "label": "Edition/translation provenance", "levels": levels,
         "guidance": {"0-absent": "No edition/translation info.",
                      "1-minimal": "Some info but incomplete/ambiguous.",
                      "2-adequate": "Edition and translation details sufficient to locate source.",
                      "3-exemplary": "Full provenance + justification for chosen edition/translation."}},
        {"id": "R2_locator", "label": "Locator robustness (variant pagination aware)", "levels": levels,
         "guidance": {"0-absent": "No locators.",
                      "1-minimal": "Page numbers only with unclear edition/scan.",
                      "2-adequate": "Locators match specified edition/scan; section/paragraph where needed.",
                      "3-exemplary": "Provides multi-locators (page+section) or canonical refs; notes pagination variants."}},
        {"id": "R3_repository", "label": "Repository citation & persistence", "levels": levels,
         "guidance": {"0-absent": "No repository link/ID.",
                      "1-minimal": "Unstable URL or vague source mention.",
                      "2-adequate": "Stable ID/record link present; retrieval reproducible.",
                      "3-exemplary": "Stable ID + archived link + access date; mirrors when appropriate."}},
        {"id": "R4_traceability", "label": "Traceability of claims to primary text", "levels": levels,
         "guidance": {"0-absent": "Claims not traceable.",
                      "1-minimal": "Some claims traceable; many not.",
                      "2-adequate": "Most claims traceable to cited passages.",
                      "3-exemplary": "All key claims traceable; includes quotations or paraphrase mapping where needed."}},
    ]
    return {"spec": spec.__dict__, "criteria": criteria, "scoring": {"method": "sum", "range": [0, 12]}}


def build_all_instruments() -> Dict[str, Instrument]:
    return {
        "survey": build_survey_primary_source_practices(),
        "audit": build_audit_coding_sheet(),
        "checklist": build_metadata_checklist(),
        "rubric": build_rubric_primary_source_validation(),
    }


__all__ = [
    "InstrumentSpec",
    "build_survey_primary_source_practices",
    "build_audit_coding_sheet",
    "build_metadata_checklist",
    "build_rubric_primary_source_validation",
    "build_all_instruments",
]
