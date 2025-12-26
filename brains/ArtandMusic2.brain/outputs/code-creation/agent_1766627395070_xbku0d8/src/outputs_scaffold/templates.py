"""Embedded, deterministic template contents for the outputs scaffold.

This module intentionally has no external file dependencies: all scaffolded artifacts
are defined as in-code strings to ensure reproducible generation across environments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

__all__ = [
    "Template",
    "TEMPLATES",
    "DEFAULT_OUTPUT_FILES",
    "get_template",
    "iter_templates",
]


@dataclass(frozen=True)
class Template:
    path: str
    content: str
    content_type: str = "text/plain; charset=utf-8"


def get_template(path: str) -> Template:
    """Return a template by its relative path (e.g., 'REPORT_OUTLINE.md')."""
    return TEMPLATES[path]


def iter_templates() -> Iterable[Template]:
    """Iterate templates in deterministic order."""
    for k in DEFAULT_OUTPUT_FILES:
        yield TEMPLATES[k]
REPORT_OUTLINE_MD = """# Report Outline

## 0. Document Control
- Title:
- Version:
- Author(s):
- Date:
- Status: Draft / In Review / Final
- Related artifacts:
  - RIGHTS_AND_LICENSING_CHECKLIST.md (required)
  - RIGHTS_LOG.csv (required)

## 1. Executive Summary
- Problem statement
- Key findings (3–7 bullets)
- Recommendations (3–7 bullets)

## 2. Background & Context
- Audience
- Scope (in / out)
- Prior work / constraints

## 3. Research Questions
- Primary question(s)
- Secondary question(s)

## 4. Methods
- Data sources
- Collection period
- Sampling/selection criteria
- Measurement definitions
- Limitations and threats to validity

## 5. Findings
- Thematic findings
- Evidence table(s) (link to appendix as needed)
- Quantitative summaries (if applicable)

## 6. Case Studies
- Use CASE_STUDY_TEMPLATE.md for each case study
- Include rights status for any media or third-party content

## 7. Discussion
- Interpretation
- Alternative explanations
- Equity/impact considerations (if relevant)

## 8. Recommendations & Next Steps
- Actions
- Owners
- Timeline
- Risks and mitigations

## 9. References
- Citations and links
- Note rights/licensing status for third-party materials in RIGHTS_LOG.csv

## Appendix
- Glossary
- Additional tables/figures
- Metadata export (see METADATA_SCHEMA.*)
"""
CASE_STUDY_TEMPLATE_MD = """# Case Study: <Title>

## Summary
- One-paragraph overview of the case.

## Context
- Setting:
- Stakeholders:
- Constraints:

## What Happened
- Timeline (bullets or table)
- Key decisions

## Evidence
- Data sources:
- Methods used:
- Links to supporting artifacts:

## Outcomes
- Intended outcomes:
- Observed outcomes:
- Metrics (if applicable):

## Lessons Learned
- What worked
- What did not
- What to try next

## Rights & Licensing
- If this case study includes any third-party content (images, charts, quotes, datasets),
  record it in RIGHTS_LOG.csv and complete RIGHTS_AND_LICENSING_CHECKLIST.md.
"""
METADATA_SCHEMA_JSON = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.local/schemas/metadata.schema.json",
  "title": "Outputs Metadata",
  "type": "object",
  "required": ["project", "artifacts", "generated_at"],
  "properties": {
    "project": {
      "type": "object",
      "required": ["name"],
      "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "version": {"type": "string"}
      },
      "additionalProperties": false
    },
    "generated_at": {"type": "string", "description": "ISO-8601 timestamp"},
    "artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["path", "type", "title"],
        "properties": {
          "path": {"type": "string"},
          "type": {"type": "string", "description": "e.g., report, case_study, dataset, figure"},
          "title": {"type": "string"},
          "summary": {"type": "string"},
          "authors": {"type": "array", "items": {"type": "string"}},
          "sources": {"type": "array", "items": {"type": "string"}},
          "rights": {
            "type": "object",
            "properties": {
              "rights_log_row_id": {"type": "string"},
              "license": {"type": "string"},
              "notes": {"type": "string"}
            },
            "additionalProperties": false
          }
        },
        "additionalProperties": false
      }
    }
  },
  "additionalProperties": false
}
"""
METADATA_SCHEMA_YAML = """# Outputs Metadata Schema (YAML mirror of METADATA_SCHEMA.json)
project:
  name: string
  description: string
  version: string
generated_at: "YYYY-MM-DDThh:mm:ssZ"
artifacts:
  - path: "relative/path.ext"
    type: "report|case_study|dataset|figure|other"
    title: "Human-readable title"
    summary: "Optional short summary"
    authors: ["Optional author name"]
    sources: ["Optional source URL or citation"]
    rights:
      rights_log_row_id: "Row identifier from RIGHTS_LOG.csv (if applicable)"
      license: "License identifier (if applicable)"
      notes: "Optional notes"
"""
RIGHTS_AND_LICENSING_CHECKLIST_MD = """# Rights & Licensing Checklist

This checklist is required for any project outputs that include third-party materials.

## A. Inventory
- [ ] List every external asset (images, figures, screenshots, quotes, datasets, code).
- [ ] Add an entry for each asset in RIGHTS_LOG.csv.

## B. Rights Status
For each asset in RIGHTS_LOG.csv:
- [ ] Identify the owner/rightsholder.
- [ ] Determine the license/terms (e.g., CC-BY, CC0, public domain, proprietary).
- [ ] Confirm attribution requirements and include attribution text where used.
- [ ] Confirm redistribution and modification permissions (if applicable).

## C. Documentation
- [ ] Store/attach proof of permission or license link in the RIGHTS_LOG.csv notes field.
- [ ] Record the intended use and where the asset appears (report section, figure name).

## D. Final Review
- [ ] Ensure all third-party materials are either licensed appropriately, permitted in writing,
      or removed/replaced.
- [ ] Confirm the report references RIGHTS_LOG.csv as the source of truth.
"""
RIGHTS_LOG_CSV = """asset_id,asset_name,asset_type,source_url_or_citation,owner,license_or_permission,status,attribution_required,attribution_text,intended_use,where_used,notes
A-001,,,,,,unknown,false,,,,,
"""
DEFAULT_OUTPUT_FILES: Tuple[str, ...] = (
    "REPORT_OUTLINE.md",
    "CASE_STUDY_TEMPLATE.md",
    "METADATA_SCHEMA.json",
    "METADATA_SCHEMA.yaml",
    "RIGHTS_AND_LICENSING_CHECKLIST.md",
    "RIGHTS_LOG.csv",
)

TEMPLATES: Dict[str, Template] = {
    "REPORT_OUTLINE.md": Template("REPORT_OUTLINE.md", REPORT_OUTLINE_MD, "text/markdown; charset=utf-8"),
    "CASE_STUDY_TEMPLATE.md": Template("CASE_STUDY_TEMPLATE.md", CASE_STUDY_TEMPLATE_MD, "text/markdown; charset=utf-8"),
    "METADATA_SCHEMA.json": Template("METADATA_SCHEMA.json", METADATA_SCHEMA_JSON, "application/schema+json; charset=utf-8"),
    "METADATA_SCHEMA.yaml": Template("METADATA_SCHEMA.yaml", METADATA_SCHEMA_YAML, "text/yaml; charset=utf-8"),
    "RIGHTS_AND_LICENSING_CHECKLIST.md": Template("RIGHTS_AND_LICENSING_CHECKLIST.md", RIGHTS_AND_LICENSING_CHECKLIST_MD, "text/markdown; charset=utf-8"),
    "RIGHTS_LOG.csv": Template("RIGHTS_LOG.csv", RIGHTS_LOG_CSV, "text/csv; charset=utf-8"),
}
