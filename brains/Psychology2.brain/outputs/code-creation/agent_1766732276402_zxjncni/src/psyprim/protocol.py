"""Protocol definitions for standardized primary-source workflows.

This module defines: (1) checklist items + decision rules, (2) a lightweight
metadata schema for machine-readable records, and (3) templates + validators.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

PROTOCOL_ID = "psyprim"
PROTOCOL_VERSION = "0.1.0"
@dataclass(frozen=True)
class ChecklistItem:
    id: str
    label: str
    required: bool = True
    decision_rule: str = ""
    evidence_fields: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["evidence_fields"] = list(self.evidence_fields)
        d["tags"] = list(self.tags)
        return d
METADATA_SCHEMA: Dict[str, Any] = {
    "schema_id": "psyprim.primary_source_record",
    "schema_version": 1,
    "required": [
        "record_id",
        "title",
        "authors",
        "year",
        "source_type",
        "repository",
        "citations",
        "provenance_flags",
        "variant",
    ],
    "fields": {
        "record_id": {"type": "string", "pattern": r"^[A-Za-z0-9._-]{6,64}$"},
        "title": {"type": "string", "min_len": 1},
        "authors": {"type": "list[string]", "min_len": 1},
        "year": {"type": "integer", "min": 1400, "max": 2100},
        "source_type": {"type": "string", "enum": ["book", "article", "chapter", "letter", "archival_item", "thesis", "other"]},
        "language": {"type": "string", "optional": True},
        "translator": {"type": "string", "optional": True},
        "repository": {"type": "object", "keys": ["name"], "optional_keys": ["collection", "call_number", "url"]},
        "access_date": {"type": "string", "optional": True},  # ISO-8601 recommended
        "urls": {"type": "list[string]", "optional": True},
        "citations": {"type": "list[object]", "min_len": 1},
        "variant": {
            "type": "object",
            "keys": ["variant_id", "variant_number", "variant_of", "status"],
            "optional_keys": ["description"],
        },
        "provenance_flags": {"type": "list[string]"},
        "evidence": {"type": "object", "optional": True},  # e.g., page_images, hashes, ocr_confidence, notes
        "notes": {"type": "string", "optional": True},
    },
}
DECISION_RULES: Dict[str, str] = {
    "prov:has_scan": "If any quotation or transcription is used, record whether a page-image scan exists and how it was obtained.",
    "prov:has_photograph": "If a scan is unavailable, photographs are acceptable; record device/context and ensure page/folio identifiers are captured.",
    "prov:has_ocr": "If OCR is used, record OCR engine/version and confidence (or sampling error-rate) in evidence.",
    "prov:ocr_requires_spotcheck": "If OCR present, spot-check at least N=10 random lines OR 5% of lines (whichever larger); record results.",
    "prov:translation_used": "If working in translation, cite translator/edition and link quotations to both source-language and translated passages when feasible.",
    "prov:secondary_citation": "If citing via a secondary source, mark explicitly and record primary-source lookup attempt outcome.",
    "variant:numbering": "Each distinct instantiation of a source (edition/scan/OCR/transcription) gets a variant_number; increments within a variant_of family.",
    "cite:link_repository_id": "Every repository item must include stable identifier(s): call_number/handle/ARK/DOI/URL; include access_date if URL-based.",
}
CHECKLISTS: Dict[str, List[ChecklistItem]] = {
    "acquire": [
        ChecklistItem(
            id="A1",
            label="Identify repository item with stable identifier(s) (call number/ARK/DOI/handle/URL).",
            decision_rule=DECISION_RULES["cite:link_repository_id"],
            evidence_fields=("repository.name", "repository.call_number", "repository.url", "access_date"),
            tags=("repository", "citation"),
        ),
        ChecklistItem(
            id="A2",
            label="Record acquisition mode (scan/photo/manual copy) and any restrictions.",
            decision_rule=DECISION_RULES["prov:has_scan"],
            evidence_fields=("evidence.page_images", "evidence.acquisition_mode", "notes"),
            tags=("provenance",),
        ),
    ],
    "transcribe": [
        ChecklistItem(
            id="T1",
            label="Assign/confirm variant identifiers (variant_of, variant_id, variant_number).",
            decision_rule=DECISION_RULES["variant:numbering"],
            evidence_fields=("variant.variant_of", "variant.variant_id", "variant.variant_number"),
            tags=("variant",),
        ),
        ChecklistItem(
            id="T2",
            label="If OCR used, record engine/version and confidence or measured error rate.",
            decision_rule=DECISION_RULES["prov:has_ocr"],
            evidence_fields=("evidence.ocr_engine", "evidence.ocr_version", "evidence.ocr_confidence", "evidence.ocr_error_rate"),
            tags=("provenance", "ocr"),
        ),
        ChecklistItem(
            id="T3",
            label="If OCR used, perform and record spot-check procedure and results.",
            decision_rule=DECISION_RULES["prov:ocr_requires_spotcheck"],
            evidence_fields=("evidence.ocr_spotcheck_n", "evidence.ocr_spotcheck_result"),
            tags=("quality", "ocr"),
        ),
    ],
    "cite": [
        ChecklistItem(
            id="C1",
            label="Provide at least one full citation record including pages/folio where applicable.",
            decision_rule="Citations must be sufficient to locate the quoted passage; include page/folio for paginated sources.",
            evidence_fields=("citations",),
            tags=("citation",),
        ),
        ChecklistItem(
            id="C2",
            label="Mark any secondary citation explicitly and document primary-source lookup attempt.",
            decision_rule=DECISION_RULES["prov:secondary_citation"],
            evidence_fields=("provenance_flags", "notes"),
            tags=("citation", "provenance"),
        ),
    ],
    "archive": [
        ChecklistItem(
            id="R1",
            label="Store evidence artifacts (page images, hashes, transcription file refs) with durable paths/identifiers.",
            decision_rule="Evidence fields should permit independent verification; include hashes when feasible.",
            evidence_fields=("evidence",),
            tags=("reproducibility",),
        )
    ],
}
def protocol_bundle() -> Dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "metadata_schema": METADATA_SCHEMA,
        "decision_rules": DECISION_RULES,
        "checklists": {k: [i.to_dict() for i in v] for k, v in CHECKLISTS.items()},
    }


def metadata_template() -> Dict[str, Any]:
    return {
        "record_id": "",
        "title": "",
        "authors": [],
        "year": None,
        "source_type": "other",
        "language": None,
        "translator": None,
        "repository": {"name": "", "collection": None, "call_number": None, "url": None},
        "access_date": None,
        "urls": [],
        "citations": [{"style": "apa", "text": "", "locator": None, "repository_link": None}],
        "variant": {"variant_of": "", "variant_id": "", "variant_number": 1, "status": "draft", "description": None},
        "provenance_flags": [],
        "evidence": {},
        "notes": "",
    }


def checklist_template(name: str) -> List[Dict[str, Any]]:
    if name not in CHECKLISTS:
        raise KeyError(f"Unknown checklist: {name}")
    return [{"id": i.id, "label": i.label, "required": i.required, "status": "unstarted", "notes": ""} for i in CHECKLISTS[name]]
def _get(d: Dict[str, Any], dotted: str) -> Any:
    cur: Any = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def validate_metadata(meta: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    req = METADATA_SCHEMA["required"]
    for k in req:
        if k not in meta or meta.get(k) in (None, "", []):
            errs.append(f"missing_required:{k}")

    f = METADATA_SCHEMA["fields"]
    if "year" in meta and meta.get("year") is not None:
        y = meta["year"]
        if not isinstance(y, int):
            errs.append("type:year")
        else:
            if y < f["year"]["min"] or y > f["year"]["max"]:
                errs.append("range:year")
    if "authors" in meta and meta.get("authors") is not None:
        if not (isinstance(meta["authors"], list) and all(isinstance(a, str) and a.strip() for a in meta["authors"])):
            errs.append("type:authors")
    if "citations" in meta:
        c = meta.get("citations")
        if not (isinstance(c, list) and len(c) >= 1 and all(isinstance(x, dict) for x in c)):
            errs.append("type:citations")
    if "variant" in meta:
        v = meta.get("variant")
        if not isinstance(v, dict):
            errs.append("type:variant")
        else:
            for kk in METADATA_SCHEMA["fields"]["variant"]["keys"]:
                if kk not in v or v.get(kk) in (None, ""):
                    errs.append(f"missing_variant:{kk}")
            if isinstance(v.get("variant_number"), int) and v["variant_number"] < 1:
                errs.append("range:variant.variant_number")
            if not isinstance(v.get("variant_number"), int):
                errs.append("type:variant.variant_number")

    # checklist-driven soft consistency checks based on provenance flags
    flags = meta.get("provenance_flags") or []
    if not isinstance(flags, list) or not all(isinstance(x, str) for x in flags):
        errs.append("type:provenance_flags")
        flags = []
    ev = meta.get("evidence") or {}
    if "prov:has_ocr" in flags:
        if _get(meta, "evidence.ocr_engine") in (None, ""):
            errs.append("ocr:missing_engine")
        if _get(meta, "evidence.ocr_confidence") in (None, "") and _get(meta, "evidence.ocr_error_rate") in (None, ""):
            errs.append("ocr:missing_quality_metric")
    if "prov:secondary_citation" in flags and not (isinstance(meta.get("notes"), str) and meta.get("notes", "").strip()):
        errs.append("secondary:missing_notes")
    if ev is not None and not isinstance(ev, dict):
        errs.append("type:evidence")

    return (len(errs) == 0), errs
