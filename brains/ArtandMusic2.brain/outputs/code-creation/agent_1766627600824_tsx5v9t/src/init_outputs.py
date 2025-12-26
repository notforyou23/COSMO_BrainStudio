from __future__ import annotations
import argparse
import csv
import os
from pathlib import Path
from typing import Dict, Iterable, Optional

REPORT_OUTLINE_MD = """# Report Outline

## 1. Executive Summary
- Problem statement
- Key findings
- Recommendations

## 2. Background & Context
- Domain overview
- Stakeholders
- Constraints & assumptions

## 3. Methodology
- Data sources
- Approach
- Evaluation criteria

## 4. Findings
- Evidence
- Analysis
- Risks / limitations

## 5. Case Studies (Exemplars)
- Index-driven list (see CASE_STUDIES_INDEX.csv)
- Summaries and cross-cutting themes

## 6. Recommendations
- Prioritized actions
- Owners & timelines
- Success metrics

## 7. Appendix
- Glossary
- References
"""

CASE_STUDY_TEMPLATE_MD = """# Case Study: {{TITLE}}

## Summary
- One-paragraph overview.

## Context
- Organization / setting
- Constraints and goals

## Intervention
- What was done
- Who was involved
- Timeline

## Evidence
- Data sources
- Metrics
- Outcomes (quant + qual)

## What Worked / What Didn't
- Success factors
- Failure modes
- Trade-offs

## Reproducibility Notes
- Requirements
- Risks
- Implementation tips

## Metadata (mirror required fields from METADATA_SCHEMA.md)
- id:
- title:
- domain:
- date:
- source_url:
- tags:
"""

METADATA_SCHEMA_MD = """# Metadata Schema (Case Studies)

This schema defines the minimum metadata required for each exemplar entry in `CASE_STUDIES_INDEX.csv`.

## Required fields
- **id** (string): Unique stable identifier (e.g., `cs_0001`).
- **title** (string): Human-readable title.
- **domain** (string): Domain/category (e.g., healthcare, finance, education).
- **date** (YYYY-MM-DD): Publication or observation date (use best-known).
- **source_url** (url): Primary source location (paper, blog, report).
- **summary** (string): 1–3 sentence abstract.
- **tags** (comma-separated): Freeform tags.

## Optional fields
- **organization** (string)
- **region** (string)
- **methods** (string): Methods/approach keywords.
- **metrics** (string): Key metrics tracked.
- **artifact_path** (path): Local path to a markdown case study (relative to outputs dir).
- **notes** (string)
"""

INDEX_COLUMNS = [
    "id",
    "title",
    "domain",
    "date",
    "source_url",
    "summary",
    "tags",
    "organization",
    "region",
    "methods",
    "metrics",
    "artifact_path",
    "notes",
]

def _resolve_under_root(root: Path, p: Path) -> Path:
    root_r = root.resolve()
    p_r = p.resolve()
    try:
        p_r.relative_to(root_r)
    except Exception as e:
        raise ValueError(f"Refusing to write outside root: {p_r} (root={root_r})") from e
    return p_r

def _atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    os.replace(tmp, path)

def _ensure_file(path: Path, content: str, *, force: bool, dry_run: bool) -> str:
    if path.exists() and not force:
        return "skipped"
    if dry_run:
        return "would_write"
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, content)
    return "written"

def _ensure_csv(path: Path, headers: Iterable[str], *, force: bool, dry_run: bool) -> str:
    if path.exists() and not force:
        return "skipped"
    if dry_run:
        return "would_write"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(headers), quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
    os.replace(tmp, path)
    return "written"

def init_outputs(
    root: Path,
    outputs_dir: str = "outputs",
    *,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, str]:
    root = root.resolve()
    out_dir = _resolve_under_root(root, root / outputs_dir)
    report = _resolve_under_root(root, out_dir / "REPORT_OUTLINE.md")
    template = _resolve_under_root(root, out_dir / "CASE_STUDY_TEMPLATE.md")
    schema = _resolve_under_root(root, out_dir / "METADATA_SCHEMA.md")
    index = _resolve_under_root(root, out_dir / "CASE_STUDIES_INDEX.csv")

    results: Dict[str, str] = {}
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    results[str(report)] = _ensure_file(report, REPORT_OUTLINE_MD, force=force, dry_run=dry_run)
    results[str(template)] = _ensure_file(template, CASE_STUDY_TEMPLATE_MD, force=force, dry_run=dry_run)
    results[str(schema)] = _ensure_file(schema, METADATA_SCHEMA_MD, force=force, dry_run=dry_run)
    results[str(index)] = _ensure_csv(index, INDEX_COLUMNS, force=force, dry_run=dry_run)
    return results

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Initialize outputs directory and starter artifacts.")
    p.add_argument("--root", default=".", help="Project root directory (default: current directory).")
    p.add_argument("--outputs-dir", default="outputs", help="Outputs directory under root (default: outputs).")
    p.add_argument("--force", action="store_true", help="Overwrite existing files.")
    p.add_argument("--dry-run", action="store_true", help="Show actions without writing.")
    return p

def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    results = init_outputs(Path(args.root), args.outputs_dir, force=args.force, dry_run=args.dry_run)
    for k in sorted(results):
        print(f"{results[k]}\t{k}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
