#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = [
    "REPORT_OUTLINE.md",
    "CASE_STUDY_TEMPLATE.md",
    "METADATA_SCHEMA.json",
    "WORKLOG.md",
    "INDEX.md",
]

SCAFFOLDS = {
    "REPORT_OUTLINE.md": """# Report Outline

> Scaffold file created/maintained by runtime/outputs/tools/validate_outputs.py

## 1. Executive Summary
- Purpose
- Key findings
- Recommendations

## 2. Background / Context
- Problem statement
- Stakeholders
- Constraints & assumptions

## 3. Method / Approach
- Data sources
- Process / pipeline
- Limitations

## 4. Findings
- Evidence
- Analysis
- Visuals / tables (if applicable)

## 5. Discussion
- Interpretation
- Risks & uncertainties
- Alternatives considered

## 6. Recommendations
- Immediate actions
- Longer-term actions
- Ownership & timelines

## 7. Appendix
- Glossary
- References
""",
    "CASE_STUDY_TEMPLATE.md": """# Case Study Template

> Scaffold file created/maintained by runtime/outputs/tools/validate_outputs.py

## Title
## Summary (1 paragraph)

## Context
- Who / where / when
- What changed or was attempted
- Why now

## Objectives
- Primary objective
- Success criteria / metrics

## Intervention / Approach
- Inputs
- Activities
- Tools / methods
- Timeline

## Outcomes
- Quantitative results
- Qualitative results
- Unexpected effects

## Lessons Learned
- What worked
- What didn’t
- What to try next time

## Artifacts
- Links to datasets, notebooks, reports

## Metadata
- Tags
- Owners / contributors
- Date range
""",
    "WORKLOG.md": """# Worklog

> Scaffold file created/maintained by runtime/outputs/tools/validate_outputs.py

## Entries
- {utc_now} — Initialized scaffold.

### Entry Template
- Date (UTC):
- What changed:
- Why:
- Notes / links:
""",
    "INDEX.md": """# Outputs Index

> Scaffold file created/maintained by runtime/outputs/tools/validate_outputs.py

## Required Files
- [REPORT_OUTLINE.md](./REPORT_OUTLINE.md)
- [CASE_STUDY_TEMPLATE.md](./CASE_STUDY_TEMPLATE.md)
- [METADATA_SCHEMA.json](./METADATA_SCHEMA.json)
- [WORKLOG.md](./WORKLOG.md)

## Additional Outputs
- Add links to generated reports, datasets, figures, and logs here.
""",
}

DEFAULT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "runtime/outputs metadata",
    "type": "object",
    "required": ["title", "created_utc", "source", "version"],
    "properties": {
        "title": {"type": "string"},
        "created_utc": {"type": "string", "description": "ISO-8601 UTC timestamp"},
        "source": {"type": "string", "description": "Generator, notebook, or pipeline name"},
        "version": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}, "default": []},
        "description": {"type": "string"},
        "artifacts": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "kind": {"type": "string"},
                    "sha256": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "additionalProperties": True,
            },
            "default": [],
        },
    },
    "additionalProperties": True,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _outputs_dir() -> Path:
    # .../runtime/outputs/tools/validate_outputs.py -> outputs dir is parent of tools
    return Path(__file__).resolve().parents[1]


def _write_if_missing_or_empty(path: Path, text: str) -> bool:
    if path.exists():
        try:
            if path.is_file() and path.stat().st_size > 0:
                return False
        except OSError:
            return False
    path.write_text(text, encoding="utf-8")
    return True


def _ensure_scaffolds(outputs: Path, check_only: bool) -> dict:
    created = []
    updated = []
    missing = []

    utc_now = _utc_now()
    for name in REQUIRED:
        p = outputs / name
        if name == "METADATA_SCHEMA.json":
            if p.exists() and p.is_file() and p.stat().st_size > 0:
                continue
            if check_only:
                missing.append(name)
                continue
            p.write_text(json.dumps(DEFAULT_SCHEMA, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            created.append(name)
            continue

        tmpl = SCAFFOLDS.get(name)
        if tmpl is None:
            if not p.exists():
                missing.append(name)
            continue

        content = tmpl.format(utc_now=utc_now)
        if check_only:
            if not (p.exists() and p.is_file() and p.stat().st_size > 0):
                missing.append(name)
            continue

        wrote = _write_if_missing_or_empty(p, content)
        (created if wrote else updated).append(name) if wrote else None

    return {"created": created, "updated": updated, "missing": missing}


def _validate_presence(outputs: Path) -> list[str]:
    missing = []
    for name in REQUIRED:
        p = outputs / name
        if not (p.exists() and p.is_file()):
            missing.append(name)
            continue
        try:
            if p.stat().st_size == 0:
                missing.append(name)
        except OSError:
            missing.append(name)
    return missing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Create/update required scaffold files and validate runtime/outputs.")
    ap.add_argument("--check-only", action="store_true", help="Do not create/update; only validate presence.")
    ap.add_argument("--json", dest="json_out", action="store_true", help="Emit a machine-readable summary.")
    args = ap.parse_args(argv)

    outputs = _outputs_dir()
    outputs.mkdir(parents=True, exist_ok=True)

    changes = _ensure_scaffolds(outputs, check_only=args.check_only)
    missing = _validate_presence(outputs)

    ok = (len(missing) == 0)
    summary = {
        "outputs_dir": str(outputs),
        "ok": ok,
        "missing": missing,
        "created": changes.get("created", []),
        "check_only": bool(args.check_only),
    }

    if args.json_out:
        sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    else:
        if not args.check_only and summary["created"]:
            sys.stdout.write("CREATED:" + ",".join(summary["created"]) + "\n")
        if missing:
            sys.stderr.write("MISSING:" + ",".join(missing) + "\n")
        else:
            sys.stdout.write("OK\n")

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
