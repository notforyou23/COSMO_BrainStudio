from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


DEFAULT_REPORT_OUTLINE = """# Report Outline

## 0) Rights & Licensing (read first)
- Checklist: [RIGHTS_AND_LICENSING_CHECKLIST.md](RIGHTS_AND_LICENSING_CHECKLIST.md)
- Log: [RIGHTS_LOG.csv](RIGHTS_LOG.csv)

## 1) Executive Summary
## 2) Background & Problem Statement
## 3) Approach / Methods
## 4) Findings
## 5) Case Studies
- Use: [CASE_STUDY_TEMPLATE.md](CASE_STUDY_TEMPLATE.md)

## 6) Limitations, Risks, and Equity Considerations
## 7) Recommendations
## 8) Appendix
- Metadata schema: METADATA_SCHEMA.json / METADATA_SCHEMA.yaml
"""

DEFAULT_CASE_STUDY_TEMPLATE = """# Case Study Template

## Title
## Context
## Stakeholders
## Intervention / Program Description
## Evidence & Outcomes
## Mechanisms / Theory of Change
## Risks, Equity, and Measurement Notes
## Implementation Notes
## Sources
## Rights & Licensing
Before embedding third-party text/images, complete:
- [RIGHTS_AND_LICENSING_CHECKLIST.md](RIGHTS_AND_LICENSING_CHECKLIST.md)
- Add an entry to [RIGHTS_LOG.csv](RIGHTS_LOG.csv)
"""

DEFAULT_RIGHTS_CHECKLIST = """# Rights and Licensing Checklist

Use this checklist before including third-party assets (images, charts, long quotes, datasets).

## Asset identification
- [ ] Asset name / short description
- [ ] Source URL / citation
- [ ] Creator / copyright holder

## Permission basis
- [ ] Original work created by us
- [ ] Public domain (record basis)
- [ ] Licensed (record license + terms)
- [ ] Permission obtained in writing (store proof location)
- [ ] Fair use / exception rationale documented (jurisdiction noted)

## Attribution & storage
- [ ] Required attribution text recorded
- [ ] Proof of permission/license stored (path/URL)
- [ ] Any restrictions (non-commercial, no-derivatives, share-alike) recorded

## Logging
- [ ] Entry added to RIGHTS_LOG.csv
"""

DEFAULT_RIGHTS_LOG_CSV = """asset_id,asset_type,title_or_description,source_url,creator_or_rightsholder,license_or_permission_basis,attribution_required,restrictions,proof_location,approved_by,approval_date,notes
"""

DEFAULT_METADATA_SCHEMA_JSON = """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Outputs Metadata",
  "type": "object",
  "properties": {
    "report_title": { "type": "string" },
    "version": { "type": "string" },
    "created_utc": { "type": "string", "format": "date-time" },
    "authors": { "type": "array", "items": { "type": "string" } },
    "sources": { "type": "array", "items": { "type": "string" } },
    "rights": {
      "type": "object",
      "properties": {
        "checklist_path": { "const": "RIGHTS_AND_LICENSING_CHECKLIST.md" },
        "rights_log_path": { "const": "RIGHTS_LOG.csv" }
      },
      "required": ["checklist_path", "rights_log_path"]
    }
  },
  "required": ["report_title", "version", "created_utc", "authors", "rights"]
}
"""

DEFAULT_METADATA_SCHEMA_YAML = """$schema: https://json-schema.org/draft/2020-12/schema
title: Outputs Metadata
type: object
properties:
  report_title: {type: string}
  version: {type: string}
  created_utc: {type: string, format: date-time}
  authors:
    type: array
    items: {type: string}
  sources:
    type: array
    items: {type: string}
  rights:
    type: object
    properties:
      checklist_path: {const: RIGHTS_AND_LICENSING_CHECKLIST.md}
      rights_log_path: {const: RIGHTS_LOG.csv}
    required: [checklist_path, rights_log_path]
required: [report_title, version, created_utc, authors, rights]
"""


@dataclass
class ScaffoldResult:
    outputs_dir: Path
    created: Tuple[str, ...]
    updated: Tuple[str, ...]
    skipped: Tuple[str, ...]


def _write_text(path: Path, content: str, overwrite: bool) -> str:
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return "skipped"
        if not overwrite:
            return "skipped"
        path.write_text(content, encoding="utf-8")
        return "updated"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "created"


def generate_outputs_scaffold(project_root: Path, overwrite: bool = False) -> ScaffoldResult:
    project_root = Path(project_root)
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    files: Dict[str, str] = {
        "REPORT_OUTLINE.md": DEFAULT_REPORT_OUTLINE,
        "CASE_STUDY_TEMPLATE.md": DEFAULT_CASE_STUDY_TEMPLATE,
        "METADATA_SCHEMA.json": DEFAULT_METADATA_SCHEMA_JSON,
        "METADATA_SCHEMA.yaml": DEFAULT_METADATA_SCHEMA_YAML,
        "RIGHTS_AND_LICENSING_CHECKLIST.md": DEFAULT_RIGHTS_CHECKLIST,
        "RIGHTS_LOG.csv": DEFAULT_RIGHTS_LOG_CSV,
    }

    created, updated, skipped = [], [], []
    for name, content in files.items():
        status = _write_text(outputs_dir / name, content, overwrite=overwrite)
        (created if status == "created" else updated if status == "updated" else skipped).append(name)

    return ScaffoldResult(outputs_dir=outputs_dir, created=tuple(created), updated=tuple(updated), skipped=tuple(skipped))


def validate_outputs_scaffold(project_root: Path) -> Dict[str, bool]:
    project_root = Path(project_root)
    outputs_dir = project_root / "outputs"
    required = [
        "REPORT_OUTLINE.md",
        "CASE_STUDY_TEMPLATE.md",
        "METADATA_SCHEMA.json",
        "METADATA_SCHEMA.yaml",
        "RIGHTS_AND_LICENSING_CHECKLIST.md",
        "RIGHTS_LOG.csv",
    ]
    present = {name: (outputs_dir / name).is_file() for name in required}
    return present
