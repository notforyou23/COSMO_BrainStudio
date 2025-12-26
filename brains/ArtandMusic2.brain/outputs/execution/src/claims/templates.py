"""Primary-source verification templates for claim-card intake.

These templates are used by docs/tests to demonstrate compliant vs non-compliant
inputs, especially the hard-required fields:
- claim_text (the exact claim being evaluated)
- dataset_anchor (where the primary-source evidence lives)

No validation logic lives here; this module is data-only.
"""

from __future__ import annotations
PRIMARY_SOURCE_VERIFICATION_TEMPLATES = {
    "compliant": {
        "id": "claim_example_compliant_001",
        "claim_text": "In 2023, Exampleville reduced PM2.5 annual mean by 12% compared to 2022.",
        "dataset_anchor": {
            "source_type": "government_dataset",
            "source_name": "Exampleville Air Quality Open Data Portal",
            "dataset_id": "EV-AQ-PM25-ANNUAL",
            "dataset_version": "2024-01",
            "record_locator": {
                "table": "annual_city_metrics",
                "primary_key": {"city": "Exampleville", "year": 2023},
                "fields": ["pm25_annual_mean", "pm25_annual_mean_change_pct"],
            },
            "retrieved_at": "2025-12-24T00:00:00Z",
            "access_url": "https://data.example.gov/air-quality/EV-AQ-PM25-ANNUAL",
        },
        "primary_source_verification": {
            "method": "dataset_lookup",
            "verification_steps": [
                "Open dataset EV-AQ-PM25-ANNUAL (version 2024-01).",
                "Filter annual_city_metrics to city=Exampleville and year=2023.",
                "Confirm pm25_annual_mean_change_pct equals -12 (or -0.12 depending on units).",
            ],
            "expected_evidence": {
                "fields_required": [
                    "pm25_annual_mean",
                    "pm25_annual_mean_change_pct",
                ],
                "acceptance_criteria": [
                    "Change percentage is -12% ± 0.5 percentage points (rounding).",
                    "Dataset version matches dataset_anchor.dataset_version.",
                ],
            },
        },
        "notes": "Includes exact claim text and a concrete, machine-locatable dataset anchor.",
    },
    "non_compliant_missing_claim_text": {
        "id": "claim_example_noncompliant_001",
        "claim_text": "",
        "dataset_anchor": {
            "source_type": "government_dataset",
            "source_name": "Exampleville Air Quality Open Data Portal",
            "dataset_id": "EV-AQ-PM25-ANNUAL",
            "dataset_version": "2024-01",
            "record_locator": {"table": "annual_city_metrics", "primary_key": {"city": "Exampleville", "year": 2023}},
            "retrieved_at": "2025-12-24T00:00:00Z",
            "access_url": "https://data.example.gov/air-quality/EV-AQ-PM25-ANNUAL",
        },
        "primary_source_verification": {
            "method": "dataset_lookup",
            "verification_steps": ["Open dataset and locate the referenced record."],
        },
        "expected_validator_error": "Missing required field: claim_text (must be a non-empty string).",
    },
    "non_compliant_missing_dataset_anchor": {
        "id": "claim_example_noncompliant_002",
        "claim_text": "In 2023, Exampleville reduced PM2.5 annual mean by 12% compared to 2022.",
        "dataset_anchor": None,
        "primary_source_verification": {
            "method": "dataset_lookup",
            "verification_steps": ["Attempt to find the supporting record."],
        },
        "expected_validator_error": "Missing required field: dataset_anchor (must be provided for primary-source verification).",
    },
    "non_compliant_ambiguous_dataset_anchor": {
        "id": "claim_example_noncompliant_003",
        "claim_text": "In 2023, Exampleville reduced PM2.5 annual mean by 12% compared to 2022.",
        "dataset_anchor": {
            "source_type": "government_dataset",
            "source_name": "Exampleville Air Quality Open Data Portal",
            "dataset_id": "",
            "dataset_version": "",
            "record_locator": {},
            "retrieved_at": "",
            "access_url": "https://data.example.gov/",
        },
        "primary_source_verification": {
            "method": "dataset_lookup",
            "verification_steps": ["Search the portal for relevant PM2.5 data."],
        },
        "expected_validator_error": "Dataset anchor is present but not specific enough to locate the primary source record.",
    },
}
def get_primary_source_verification_template(name: str) -> dict:
    """Return a deep-copiable template dict by name.

    Callers should treat the returned dict as mutable and should copy it before
    modifications in tests (e.g., json roundtrip or copy.deepcopy).
    """
    if name not in PRIMARY_SOURCE_VERIFICATION_TEMPLATES:
        raise KeyError(f"Unknown template: {name}. Available: {sorted(PRIMARY_SOURCE_VERIFICATION_TEMPLATES)}")
    return PRIMARY_SOURCE_VERIFICATION_TEMPLATES[name]
COMPLIANT_PRIMARY_SOURCE_INPUT = PRIMARY_SOURCE_VERIFICATION_TEMPLATES["compliant"]
NONCOMPLIANT_PRIMARY_SOURCE_INPUTS = {
    "missing_claim_text": PRIMARY_SOURCE_VERIFICATION_TEMPLATES["non_compliant_missing_claim_text"],
    "missing_dataset_anchor": PRIMARY_SOURCE_VERIFICATION_TEMPLATES["non_compliant_missing_dataset_anchor"],
    "ambiguous_dataset_anchor": PRIMARY_SOURCE_VERIFICATION_TEMPLATES["non_compliant_ambiguous_dataset_anchor"],
}
