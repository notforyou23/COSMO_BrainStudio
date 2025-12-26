"""Default initial artifact templates plus small helpers to render/validate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional


REPORT_OUTLINE_MD = """# Report Outline

## 0. Executive Summary
- Problem statement
- Key findings
- Recommendations
- Risks / open questions

## 1. Context & Objectives
- Background
- Stakeholders
- Scope (in / out)

## 2. Methodology
- Data sources
- Assumptions
- Evaluation criteria

## 3. Findings
- Finding 1
- Finding 2
- Finding 3

## 4. Options & Tradeoffs
- Option A
- Option B
- Option C

## 5. Recommendation
- Chosen approach
- Rationale
- Dependencies

## 6. Implementation Plan
- Milestones
- Owners
- Timeline

## 7. Appendix
- Glossary
- References
"""


CASE_STUDY_TEMPLATE_MD = """# Case Study: {title}

## Snapshot
- **ID:** {case_id}
- **Domain:** {domain}
- **Date:** {date}
- **Owner:** {owner}
- **Status:** {status}

## Problem
Describe the problem in 3–7 bullets.

## Context
Key background, constraints, stakeholders, and why this mattered.

## Approach
- What was tried
- Why this approach
- Tools / methods used

## Evidence
List supporting artifacts (links, docs, metrics, screenshots), and what they show.

## Outcome
- Results and impact
- What changed (before/after)
- Cost / time / quality notes

## Lessons Learned
- What worked
- What did not
- What we'd do differently

## Tags
Comma-separated tags.
"""


METADATA_SCHEMA_MD = """# Metadata Schema (for Case Studies)

This project uses a single intake table (`CASE_STUDIES_INDEX.csv`) plus per-case narrative markdown.
Each row in the CSV represents one exemplar. Suggested fields:

## Required columns
- `case_id` (string, unique, stable)
- `title` (string)
- `domain` (string)
- `date` (YYYY-MM-DD)
- `owner` (string)
- `status` (one of: draft, reviewed, published, deprecated)
- `summary` (string, 1–3 sentences)
- `source_path` (relative path to the case study markdown)
- `tags` (comma-separated)

## Optional columns
- `evidence_links` (semicolon-separated URLs)
- `metrics` (freeform short text)
- `confidentiality` (public|internal|restricted)
- `notes` (freeform)

## Conventions
- Keep `case_id` immutable once issued.
- Keep paths relative and inside the project outputs directory.
- Prefer ISO dates.
"""


CASE_STUDIES_INDEX_CSV = """case_id,title,domain,date,owner,status,summary,source_path,tags,evidence_links,metrics,confidentiality,notes
EXAMPLE-001,Example Case Study,example,2025-01-01,unknown,draft,Short summary goes here,case_studies/EXAMPLE-001.md,"example,template",,,internal,
"""


DEFAULT_TEMPLATES: Dict[str, str] = {
    "REPORT_OUTLINE.md": REPORT_OUTLINE_MD,
    "CASE_STUDY_TEMPLATE.md": CASE_STUDY_TEMPLATE_MD,
    "METADATA_SCHEMA.md": METADATA_SCHEMA_MD,
    "CASE_STUDIES_INDEX.csv": CASE_STUDIES_INDEX_CSV,
}


@dataclass(frozen=True)
class TemplateIssue:
    name: str
    message: str


def list_template_names() -> Iterable[str]:
    return DEFAULT_TEMPLATES.keys()


def get_template(name: str) -> str:
    if name not in DEFAULT_TEMPLATES:
        raise KeyError(f"Unknown template: {name}")
    return DEFAULT_TEMPLATES[name]


def render_template(name: str, *, values: Optional[Mapping[str, str]] = None) -> str:
    text = get_template(name)
    if not values:
        return text
    try:
        return text.format(**dict(values))
    except KeyError as e:
        missing = e.args[0]
        raise KeyError(f"Missing render value for {missing!r} in template {name!r}") from None


def validate_templates(templates: Optional[Mapping[str, str]] = None) -> list[TemplateIssue]:
    t = dict(DEFAULT_TEMPLATES if templates is None else templates)
    issues: list[TemplateIssue] = []
    required = ["REPORT_OUTLINE.md", "CASE_STUDY_TEMPLATE.md", "METADATA_SCHEMA.md", "CASE_STUDIES_INDEX.csv"]
    for r in required:
        if r not in t or not str(t[r]).strip():
            issues.append(TemplateIssue(r, "missing or empty"))
    md_checks = {
        "REPORT_OUTLINE.md": ["# Report Outline", "## 0. Executive Summary"],
        "CASE_STUDY_TEMPLATE.md": ["# Case Study:", "## Problem", "## Outcome", "{case_id}"],
        "METADATA_SCHEMA.md": ["# Metadata Schema", "Required columns", "Optional columns"],
    }
    for name, needles in md_checks.items():
        txt = t.get(name, "")
        for n in needles:
            if n not in txt:
                issues.append(TemplateIssue(name, f"missing required marker: {n}"))
    csv = t.get("CASE_STUDIES_INDEX.csv", "")
    header = (csv.splitlines()[0].strip() if csv.strip() else "")
    required_cols = ["case_id", "title", "domain", "date", "owner", "status", "summary", "source_path", "tags"]
    if not header:
        issues.append(TemplateIssue("CASE_STUDIES_INDEX.csv", "missing header"))
    else:
        cols = [c.strip() for c in header.split(",")]
        for c in required_cols:
            if c not in cols:
                issues.append(TemplateIssue("CASE_STUDIES_INDEX.csv", f"missing required column: {c}"))
    return issues
