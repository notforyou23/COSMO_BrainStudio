"""Machine-validated schema for claim card intake.

Encodes required fields and structural constraints used by validators.
Hard-fail requirements: claim_text and dataset_anchor must be present and non-empty.
"""

CLAIM_CARD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://example.local/schemas/claim_card_intake.schema.json",
    "title": "Claim Card Intake",
    "type": "object",
    "additionalProperties": False,
    "required": ["claim_text", "dataset_anchor"],
    "properties": {
        "claim_id": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "claim_text": {"type": "string", "minLength": 1},
        "dataset_anchor": {
            "description": "Pointer to primary source data supporting verification (URL, DOI, file path, or dataset id+location).",
            "oneOf": [
                {"type": "string", "minLength": 1},
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["kind", "value"],
                    "properties": {
                        "kind": {
                            "type": "string",
                            "enum": ["url", "doi", "path", "dataset_id", "other"],
                        },
                        "value": {"type": "string", "minLength": 1},
                        "locator": {"type": "string", "minLength": 1},
                        "notes": {"type": "string"},
                    },
                },
            ],
        },
        "primary_source": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "citation": {"type": "string", "minLength": 1},
                "accessed_at": {"type": "string", "minLength": 1},
                "archived_url": {"type": "string", "minLength": 1},
            },
        },
        "verification": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "method": {"type": "string", "minLength": 1},
                "notes": {"type": "string"},
                "checks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "status"],
                        "properties": {
                            "name": {"type": "string", "minLength": 1},
                            "status": {"type": "string", "enum": ["pass", "fail", "n/a"]},
                            "evidence": {"type": "string"},
                        },
                    },
                },
            },
        },
        "metadata": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "created_at": {"type": "string", "minLength": 1},
                "created_by": {"type": "string", "minLength": 1},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

PRIMARY_SOURCE_VERIFICATION_TEMPLATES = {
    "compliant": {
        "claim_text": "In 2023, Example City reduced PM2.5 by 12% compared to 2022.",
        "dataset_anchor": {
            "kind": "url",
            "value": "https://data.example.org/air/pm25_2022_2023.csv",
            "locator": "rows 2-366; columns date, pm25",
        },
        "primary_source": {
            "citation": "Example City Open Data Portal — PM2.5 Daily Measurements (2022–2023)",
            "accessed_at": "2025-12-25",
            "archived_url": "https://web.archive.org/web/20251225/https://data.example.org/air/pm25_2022_2023.csv",
        },
        "verification": {
            "method": "Compute annual mean PM2.5 for 2022 and 2023 from anchored dataset; compare percent change.",
            "checks": [
                {"name": "Dataset reachable", "status": "pass", "evidence": "HTTP 200"},
                {"name": "Computation reproducible", "status": "pass", "evidence": "Notebook cell output saved"},
            ],
        },
    },
    "non_compliant_missing_claim_text": {
        "dataset_anchor": "https://data.example.org/air/pm25_2022_2023.csv",
        "primary_source": {"citation": "Example City Open Data Portal"},
    },
    "non_compliant_missing_dataset_anchor": {
        "claim_text": "In 2023, Example City reduced PM2.5 by 12% compared to 2022.",
        "primary_source": {"citation": "Example City Open Data Portal"},
    },
}

__all__ = ["CLAIM_CARD_SCHEMA", "PRIMARY_SOURCE_VERIFICATION_TEMPLATES"]
