"""Claim card intake field configuration.

This module is the single source of truth for:
- required intake fields and their semantics
- hard-fail requirements for primary-source verification (claim_text, dataset_anchor)
- small examples of compliant vs non-compliant inputs
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Hard-fail requirements for primary-source verification.
HARD_FAIL_REQUIRED_FIELDS = ("claim_text", "dataset_anchor")

# Canonical intake field specs (keep keys stable; used by schema/validators).
INTAKE_FIELDS: List[Dict[str, Any]] = [
    {
        "name": "claim_id",
        "required": True,
        "type": "string",
        "description": "Unique identifier for the claim card (stable across edits).",
        "examples": ["CLM-000123"],
    },
    {
        "name": "claim_text",
        "required": True,
        "type": "string",
        "description": "The exact natural-language claim to be verified (quote/paste verbatim).",
        "examples": ["Model X reduces hospital readmissions by 12% vs baseline in 2024."],
    },
    {
        "name": "dataset_anchor",
        "required": True,
        "type": "object",
        "description": (
            "Primary-source pointer that uniquely anchors the claim to an evidence artifact "
            "(e.g., dataset + exact slice, paper + table/figure, URL + section, or file + row IDs)."
        ),
        "shape": {
            "source_type": "string",
            "ref": "string",
            "locator": "string",
            "version": "string",
        },
        "examples": [
            {
                "source_type": "dataset",
                "ref": "s3://bucket/path/readmissions.parquet",
                "locator": "rows where year==2024; metric=readmission_rate; cohort=all",
                "version": "sha256:…",
            }
        ],
    },
    {
        "name": "claim_type",
        "required": False,
        "type": "string",
        "description": "Optional classification (e.g., descriptive, causal, forecast, comparison).",
        "examples": ["comparison"],
    },
    {
        "name": "subject",
        "required": False,
        "type": "string",
        "description": "What the claim is about (entity, system, population).",
        "examples": ["Hospital readmissions"],
    },
    {
        "name": "metric",
        "required": False,
        "type": "string",
        "description": "Metric or outcome named in the claim (if applicable).",
        "examples": ["readmission_rate"],
    },
    {
        "name": "timeframe",
        "required": False,
        "type": "string",
        "description": "Time period asserted by the claim (if applicable).",
        "examples": ["2024"],
    },
    {
        "name": "notes",
        "required": False,
        "type": "string",
        "description": "Optional context/assumptions; must not replace claim_text or dataset_anchor.",
        "examples": ["Baseline defined as 2023 average; excludes pediatrics."],
    },
]

FIELD_INDEX: Dict[str, Dict[str, Any]] = {f["name"]: f for f in INTAKE_FIELDS}


def required_field_names(*, include_optional: bool = False) -> List[str]:
    """Return canonical required field names (optionally include all fields)."""
    if include_optional:
        return [f["name"] for f in INTAKE_FIELDS]
    return [f["name"] for f in INTAKE_FIELDS if f.get("required")]


def get_field_spec(name: str) -> Optional[Dict[str, Any]]:
    """Lookup field spec by canonical name."""
    return FIELD_INDEX.get(name)


def hard_fail_missing_fields(payload: Dict[str, Any]) -> List[str]:
    """Return missing fields that must hard-fail validation if absent/empty."""
    missing: List[str] = []
    for k in HARD_FAIL_REQUIRED_FIELDS:
        v = payload.get(k)
        if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, dict) and not v):
            missing.append(k)
    return missing


PRIMARY_SOURCE_VERIFICATION_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "compliant_minimal": {
        "claim_id": "CLM-000001",
        "claim_text": "In 2024, Model X reduces hospital readmissions by 12% versus baseline.",
        "dataset_anchor": {
            "source_type": "dataset",
            "ref": "file://data/readmissions_2024.parquet",
            "locator": "cohort=all; metric=readmission_rate; baseline=2023; compare=Model X vs baseline",
            "version": "sha256:REPLACE_WITH_ACTUAL_DIGEST",
        },
    },
    "non_compliant_missing_claim_text": {
        "claim_id": "CLM-000002",
        "dataset_anchor": {
            "source_type": "paper",
            "ref": "https://example.org/paper.pdf",
            "locator": "Table 2, row 'Readmissions', column 'Model X'",
            "version": "2025-01-01",
        },
        "notes": "Missing claim_text (hard-fail).",
    },
    "non_compliant_missing_dataset_anchor": {
        "claim_id": "CLM-000003",
        "claim_text": "Treatment Y improves accuracy by 5 points on Dataset Z.",
        "notes": "Missing dataset_anchor (hard-fail).",
    },
}
