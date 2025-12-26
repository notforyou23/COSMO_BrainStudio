"""Machine-checkable scaffold specifications for deterministic QA.

This module defines required project artifacts and minimal content assertions
(markers/sections) that tools/qa_run.py can validate after scaffold generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence


@dataclass(frozen=True)
class ContentSpec:
    """Rules for validating file contents."""

    must_contain: Sequence[str] = ()
    must_not_contain: Sequence[str] = ()


@dataclass(frozen=True)
class ArtifactSpec:
    """A single required artifact and its validation rules."""

    path: str
    kind: str = "file"  # file|dir
    encoding: str = "utf-8"
    content: Optional[ContentSpec] = None


def _cs(must: Sequence[str] = (), must_not: Sequence[str] = ()) -> ContentSpec:
    return ContentSpec(must_contain=tuple(must), must_not_contain=tuple(must_not))


def _a(path: str, *, kind: str = "file", content: Optional[ContentSpec] = None) -> ArtifactSpec:
    return ArtifactSpec(path=path, kind=kind, content=content)
# Canonical markers expected in generated artifacts (kept stable for QA).
REPORT_OUTLINE_MARKERS = (
    "# Report Outline",
    "## Executive Summary",
    "## Background / Context",
    "## Methodology",
    "## Findings",
    "## Recommendations",
    "## Risks & Mitigations",
    "## Appendix",
)

CASE_STUDY_MARKERS = (
    "# Case Study Template",
    "## Problem Statement",
    "## Context",
    "## Stakeholders",
    "## Approach",
    "## Data & Methods",
    "## Results",
    "## Discussion",
    "## Limitations",
    "## Next Steps",
)

QA_REPORT_MARKERS = (
    "# QA Report",
    "## Summary",
    "## Checks",
    "## Results",
)
# Required artifacts for a successful scaffold.
# NOTE: These are relative to project root (the working directory used by qa_run).
REQUIRED_ARTIFACTS: List[ArtifactSpec] = [
    _a("REPORT_OUTLINE.md", content=_cs(must=REPORT_OUTLINE_MARKERS)),
    _a("CASE_STUDY_TEMPLATE.md", content=_cs(must=CASE_STUDY_MARKERS)),
    _a("outputs/qa", kind="dir"),
    # Baseline/stub QA report files (names are stable, content has stable headers).
    _a("outputs/qa/qa_report.md", content=_cs(must=QA_REPORT_MARKERS)),
    _a("outputs/qa/qa_report.json", content=_cs(must=("{", "}",), must_not=("TODO", "TBD"))),
]

# Template sources used by scaffolder (validated for presence so QA can suggest fixes).
TEMPLATE_ARTIFACTS: List[ArtifactSpec] = [
    _a("templates/REPORT_OUTLINE.md", content=_cs(must=REPORT_OUTLINE_MARKERS)),
    _a("templates/CASE_STUDY_TEMPLATE.md", content=_cs(must=CASE_STUDY_MARKERS)),
]
def as_dict() -> Dict[str, object]:
    """Return a JSON-serializable view of the specification."""
    def c2d(c: Optional[ContentSpec]) -> Optional[Dict[str, List[str]]]:
        if c is None:
            return None
        return {"must_contain": list(c.must_contain), "must_not_contain": list(c.must_not_contain)}

    def a2d(a: ArtifactSpec) -> Dict[str, object]:
        return {"path": a.path, "kind": a.kind, "encoding": a.encoding, "content": c2d(a.content)}

    return {
        "required_artifacts": [a2d(a) for a in REQUIRED_ARTIFACTS],
        "template_artifacts": [a2d(a) for a in TEMPLATE_ARTIFACTS],
    }


def iter_all_artifacts() -> List[ArtifactSpec]:
    """Ordered list of all artifacts qa_run should consider."""
    return list(TEMPLATE_ARTIFACTS) + list(REQUIRED_ARTIFACTS)
