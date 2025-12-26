#!/usr/bin/env python3
"""Deterministic scaffold generator for required validation artifacts."""

from __future__ import annotations

import json
from pathlib import Path


REQUIRED_FILENAMES = [
    "REPORT_OUTLINE.md",
    "CASE_STUDY_TEMPLATE.md",
    "METADATA_SCHEMA.json",
    "WORKLOG.md",
]


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate(base_dir: Path) -> dict:
    base_dir = base_dir.resolve()
    outputs_dir = base_dir / "outputs"
    report_dir = outputs_dir / "report"
    logs_dir = outputs_dir / "logs"

    for d in (outputs_dir, report_dir, logs_dir, base_dir / "scripts"):
        d.mkdir(parents=True, exist_ok=True)

    report_outline = """# Report Outline

## 1. Executive Summary
- Purpose
- Key findings
- Recommendations

## 2. Background & Context
- Scope
- Stakeholders
- Constraints/assumptions

## 3. Methodology
- Data sources
- Process
- Limitations

## 4. Findings
- Finding 1
- Finding 2
- Finding 3

## 5. Case Studies
- Case study index
- Individual case write-ups

## 6. Risks & Mitigations
- Risk register
- Mitigation plan

## 7. Conclusion
- Summary
- Next steps
"""

    case_study_template = """# Case Study Template

## Title
(Concise name)

## Problem Statement
(What problem is being solved?)

## Context
- Organization / team:
- Timeframe:
- Constraints:

## Approach
- Steps taken:
- Tools / methods:

## Outcomes
- Results:
- Metrics (if any):
- What worked / what didn't:

## Lessons Learned
- Key takeaways:

## References
- Links / documents:
"""

    metadata_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Project Metadata Schema",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "project_name": {"type": "string"},
            "generated_by": {"type": "string"},
            "version": {"type": "string"},
            "artifacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "path": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["path", "description"],
                },
            },
        },
        "required": ["project_name", "version", "artifacts"],
    }

    worklog = """# Worklog

## Entries
- Initial scaffold generated deterministically.
"""

    targets = []
    for fn in REQUIRED_FILENAMES:
        targets.append(base_dir / fn)
        targets.append(outputs_dir / fn)

    for p in targets:
        if p.name == "REPORT_OUTLINE.md":
            _write_text(p, report_outline)
        elif p.name == "CASE_STUDY_TEMPLATE.md":
            _write_text(p, case_study_template)
        elif p.name == "METADATA_SCHEMA.json":
            _write_json(p, metadata_schema)
        elif p.name == "WORKLOG.md":
            _write_text(p, worklog)

    # Convenience placeholder report directory content (deterministic, optional)
    _write_text(report_dir / "README.md", "This directory contains generated report artifacts.")
    _write_text(logs_dir / "README.md", "This directory contains run/validation logs.")

    created = []
    for p in targets + [report_dir / "README.md", logs_dir / "README.md"]:
        if p.exists():
            created.append(str(p.relative_to(base_dir)))
    return {"base_dir": str(base_dir), "created": sorted(set(created))}


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    info = generate(base_dir)
    print("SCAFFOLD_OK:" + json.dumps(info, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
