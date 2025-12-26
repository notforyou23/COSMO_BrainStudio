from __future__ import annotations
from pathlib import Path
import argparse
import json
import os
from datetime import datetime, timezone

DEFAULT_REPORT_OUTLINE = """# REPORT_OUTLINE

## Purpose
- [REQUIRED] State the purpose and audience.

## Executive Summary
- [REQUIRED] 5–10 bullet summary of key findings and recommendations.

## Background & Context
- [REQUIRED] Problem framing, scope, constraints.

## Methods
- [REQUIRED] Data sources, approach, assumptions, limitations.

## Findings
- [REQUIRED] Evidence-backed findings with references.

## Recommendations
- [REQUIRED] Prioritized actions, owners, timeline, risks.

## Risks & Mitigations
- [REQUIRED] Key risks, mitigations, monitoring plan.

## Appendix
- [REQUIRED] Definitions, links, artifacts, changelog.
"""

DEFAULT_CASE_STUDY_TEMPLATE = """# CASE_STUDY_TEMPLATE

## Context
- [REQUIRED] Organization/system context.

## Problem Statement
- [REQUIRED] What problem is being solved and why it matters.

## Stakeholders
- [REQUIRED] Primary users, decision-makers, impacted groups.

## Approach
- [REQUIRED] Strategy, process, what was built/delivered.

## Results
- [REQUIRED] Outcomes, metrics, qualitative feedback.

## Lessons Learned
- [REQUIRED] What worked, what didn’t, next steps.

## Artifacts
- [REQUIRED] Links to reports, dashboards, code, designs.
"""

def _read_template(path: Path, fallback: str) -> str:
    try:
        txt = path.read_text(encoding="utf-8")
        return txt.strip() + "\n"
    except FileNotFoundError:
        return fallback.strip() + "\n"

def _write_if_missing(path: Path, content: str, force: bool = False) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return False
    path.write_text(content, encoding="utf-8")
    return True

def scaffold(project_root: Path | None = None, force: bool = False) -> dict:
    project_root = (project_root or Path(__file__).resolve().parents[1]).resolve()
    templates_dir = project_root / "templates"
    out_dir = project_root / "outputs"
    qa_dir = out_dir / "qa"

    report_tpl = _read_template(templates_dir / "REPORT_OUTLINE.md", DEFAULT_REPORT_OUTLINE)
    case_tpl = _read_template(templates_dir / "CASE_STUDY_TEMPLATE.md", DEFAULT_CASE_STUDY_TEMPLATE)

    created = {}
    created["REPORT_OUTLINE.md"] = _write_if_missing(project_root / "REPORT_OUTLINE.md", report_tpl, force=force)
    created["CASE_STUDY_TEMPLATE.md"] = _write_if_missing(project_root / "CASE_STUDY_TEMPLATE.md", case_tpl, force=force)

    stamp = datetime.now(timezone.utc).isoformat()
    qa_readme = """# outputs/qa

This folder stores QA run artifacts (machine-readable and human-readable).

- qa_stub.json: baseline QA stub produced by scaffolding
- qa_stub.md: baseline QA stub produced by scaffolding
"""
    qa_stub = {
        "schema": "qa_stub.v1",
        "generated_at": stamp,
        "project_root": str(project_root),
        "artifacts": {
            "REPORT_OUTLINE.md": str(project_root / "REPORT_OUTLINE.md"),
            "CASE_STUDY_TEMPLATE.md": str(project_root / "CASE_STUDY_TEMPLATE.md"),
        },
        "checks": [],
        "status": "stub"
    }
    qa_md = f"""# QA Stub Report

Generated at (UTC): {stamp}

## Status
- stub (scaffolding-only)

## Notes
- This file is intended to be overwritten by a QA runner.
"""

    created["outputs/qa/README.md"] = _write_if_missing(qa_dir / "README.md", qa_readme, force=force)
    created["outputs/qa/qa_stub.json"] = _write_if_missing(qa_dir / "qa_stub.json", json.dumps(qa_stub, indent=2, sort_keys=True) + "\n", force=force)
    created["outputs/qa/qa_stub.md"] = _write_if_missing(qa_dir / "qa_stub.md", qa_md, force=force)

    return {"project_root": str(project_root), "created": created}

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate project scaffolding artifacts.")
    p.add_argument("--root", default=None, help="Project root (defaults to repo root inferred from src/).")
    p.add_argument("--force", action="store_true", help="Overwrite existing generated files.")
    args = p.parse_args(argv)

    root = Path(args.root).expanduser().resolve() if args.root else None
    res = scaffold(project_root=root, force=args.force)

    if os.environ.get("SCAFFOLD_SILENT") != "1":
        created_any = any(res["created"].values())
        print(json.dumps({"ok": True, "created_any": created_any, **res}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
