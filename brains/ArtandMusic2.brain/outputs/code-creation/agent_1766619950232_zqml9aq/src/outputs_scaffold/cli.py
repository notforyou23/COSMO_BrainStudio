from __future__ import annotations
import argparse
import sys
from pathlib import Path

TEMPLATES = {
    "REPORT_OUTLINE.md": """# Report Outline

## 1. Executive Summary
- Purpose, scope, key findings, recommendations

## 2. Context & Problem Statement
- Background, stakeholders, constraints, definitions

## 3. Methodology
- Data sources, selection criteria, analysis methods, limitations

## 4. Findings
- Thematic sections, evidence, visuals (with provenance)

## 5. Case Studies
- See: CASE_STUDY_TEMPLATE.md

## 6. Risks, Ethics, and Equity Considerations
- Measurement/selection effects, bias, uncertainty, safeguards

## 7. Rights, Licensing, and Attribution
- Checklist: RIGHTS_AND_LICENSING_CHECKLIST.md
- Log: RIGHTS_LOG.csv

## 8. Appendices
- Metadata schema: METADATA_SCHEMA.json / METADATA_SCHEMA.yaml
""",
    "CASE_STUDY_TEMPLATE.md": """# Case Study Template

## Title
## Summary (3-5 sentences)

## Context
- Who/what/where/when

## Inputs / Evidence
- Data sources (with citations), artifacts, assumptions

## Intervention / Approach
- What was done, by whom, timeline

## Outcomes
- Quantitative and qualitative results; counterfactuals if known

## Implementation Notes
- Dependencies, costs, operational considerations

## Risks / Ethics / Equity
- Potential harms, mitigations, distributional impacts

## Rights & Licensing
- Confirm entries exist in RIGHTS_LOG.csv for any third-party materials
""",
    "RIGHTS_AND_LICENSING_CHECKLIST.md": """# Rights and Licensing Checklist

Use this checklist before publishing or distributing any artifact in /outputs.

## Checklist
- [ ] Identify all third-party content (images, charts, text excerpts, datasets, code)
- [ ] Record each item in RIGHTS_LOG.csv
- [ ] Confirm the license/permission allows intended use (publish, commercial, modification)
- [ ] Provide attribution per license terms (author, title, source, license, link)
- [ ] Preserve copyright notices where required
- [ ] Document restrictions (non-commercial, no-derivatives, share-alike, embargo)
- [ ] Confirm privacy/consent for personal data (if any)
- [ ] Confirm trademark/brand usage constraints (if any)

## Required artifacts
- RIGHTS_LOG.csv must exist and be kept up to date.
""",
    "RIGHTS_LOG.csv": """asset_id,asset_type,source_url,creator,license,license_url,permission_status,attribution_required,notes,added_by,added_on
example-figure-001,image,https://example.com,Example Author,CC-BY-4.0,https://creativecommons.org/licenses/by/4.0/,ok,yes,"Replace with real entry",,YYYY-MM-DD
""",
    "METADATA_SCHEMA.json": """{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Outputs Metadata Schema",
  "type": "object",
  "required": ["title", "created_on", "version", "rights_log"],
  "properties": {
    "title": {"type": "string"},
    "created_on": {"type": "string", "description": "ISO-8601 date or datetime"},
    "version": {"type": "string"},
    "summary": {"type": "string"},
    "artifacts": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["path", "type"],
        "properties": {
          "path": {"type": "string"},
          "type": {"type": "string"},
          "description": {"type": "string"},
          "provenance": {"type": "string"},
          "rights_asset_id": {"type": "string", "description": "Maps to RIGHTS_LOG.csv asset_id when third-party content is used"}
        }
      }
    },
    "rights_log": {"type": "string", "const": "RIGHTS_LOG.csv"},
    "rights_checklist": {"type": "string", "const": "RIGHTS_AND_LICENSING_CHECKLIST.md"}
  }
}
""",
    "METADATA_SCHEMA.yaml": """title: Outputs Metadata Schema
type: object
required: [title, created_on, version, rights_log]
properties:
  title: {type: string}
  created_on: {type: string, description: ISO-8601 date or datetime}
  version: {type: string}
  summary: {type: string}
  artifacts:
    type: array
    items:
      type: object
      required: [path, type]
      properties:
        path: {type: string}
        type: {type: string}
        description: {type: string}
        provenance: {type: string}
        rights_asset_id: {type: string, description: Maps to RIGHTS_LOG.csv asset_id when third-party content is used}
  rights_log: {type: string, const: RIGHTS_LOG.csv}
  rights_checklist: {type: string, const: RIGHTS_AND_LICENSING_CHECKLIST.md}
""",
}

REQUIRED = [
    "REPORT_OUTLINE.md",
    "CASE_STUDY_TEMPLATE.md",
    "METADATA_SCHEMA.json",
    "METADATA_SCHEMA.yaml",
    "RIGHTS_AND_LICENSING_CHECKLIST.md",
    "RIGHTS_LOG.csv",
]

def _write_if_needed(path: Path, content: str, update: bool) -> str | None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")
        return "created"
    existing = path.read_text(encoding="utf-8")
    if existing != content and update:
        path.write_text(content, encoding="utf-8")
        return "updated"
    return None

def init_scaffold(root: Path, update: bool) -> list[tuple[str, str]]:
    out_dir = root / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    actions: list[tuple[str, str]] = []
    for name in REQUIRED:
        action = _write_if_needed(out_dir / name, TEMPLATES[name], update=update)
        if action:
            actions.append((name, action))
    return actions

def validate_scaffold(root: Path) -> tuple[bool, list[str]]:
    out_dir = root / "outputs"
    problems: list[str] = []
    if not out_dir.exists():
        problems.append("missing outputs directory: outputs/")
        return False, problems
    for name in REQUIRED:
        p = out_dir / name
        if not p.exists():
            problems.append(f"missing: outputs/{name}")
    outline = (out_dir / "REPORT_OUTLINE.md")
    if outline.exists():
        txt = outline.read_text(encoding="utf-8")
        for ref in ("RIGHTS_AND_LICENSING_CHECKLIST.md", "RIGHTS_LOG.csv"):
            if ref not in txt:
                problems.append(f"REPORT_OUTLINE.md missing reference to {ref}")
    checklist = (out_dir / "RIGHTS_AND_LICENSING_CHECKLIST.md")
    if checklist.exists():
        if "RIGHTS_LOG.csv" not in checklist.read_text(encoding="utf-8"):
            problems.append("RIGHTS_AND_LICENSING_CHECKLIST.md missing reference to RIGHTS_LOG.csv")
    ok = len(problems) == 0
    return ok, problems

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="outputs-scaffold", description="Initialize/validate the /outputs scaffold.")
    ap.add_argument("--root", default=".", help="Project root (default: current directory)")
    sub = ap.add_subparsers(dest="cmd", required=False)
    p_init = sub.add_parser("init", help="Create /outputs and populate core artifacts")
    p_init.add_argument("--update", action="store_true", help="Overwrite scaffolded files if contents differ")
    sub.add_parser("validate", help="Validate that /outputs and required artifacts exist and are cross-referenced")
    ns = ap.parse_args(argv)

    root = Path(ns.root).resolve()
    cmd = ns.cmd or "init"
    if cmd == "init":
        actions = init_scaffold(root, update=getattr(ns, "update", False))
        for name, action in actions:
            print(f"{action}: outputs/{name}")
        if not actions:
            print("no changes")
        return 0
    ok, problems = validate_scaffold(root)
    if ok:
        print("ok")
        return 0
    for pr in problems:
        print(f"problem: {pr}")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
