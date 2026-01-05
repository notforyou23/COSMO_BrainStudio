"""Template generators for the meta-analysis starter kit.

This module writes two CSVs:
- extraction_template.csv: effect-size extraction sheet with example rows
- screening_log.csv: study screening log with example rows
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Iterable, List, Dict, Optional, Sequence, Union


PathLike = Union[str, Path]


DEFAULT_EXTRACTION_COLUMNS: List[str] = [
    "study_id",
    "citation",
    "year",
    "country",
    "design",
    "outcome",
    "effect_type",      # e.g., RR, OR, SMD, MD, FisherZ
    "effect",
    "se",
    "ci_lower",
    "ci_upper",
    "n_treat",
    "n_control",
    "notes",
]

DEFAULT_SCREENING_COLUMNS: List[str] = [
    "record_id",
    "source",           # database/search source
    "title",
    "authors",
    "year",
    "doi_or_url",
    "deduped",          # yes/no
    "screen_title_abstract_decision",  # include/exclude/unclear
    "screen_fulltext_decision",        # include/exclude
    "exclude_reason",
    "included_in_meta", # yes/no
    "reviewer",
    "date",
    "notes",
]


@dataclass(frozen=True)
class TemplateSpec:
    filename: str
    columns: Sequence[str]
    example_rows: Sequence[Dict[str, object]]


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, columns: Sequence[str], rows: Iterable[Dict[str, object]], overwrite: bool) -> Path:
    if path.exists() and not overwrite:
        return path
    _ensure_parent(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(columns), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in columns})
    return path


def extraction_template_spec() -> TemplateSpec:
    rows = [
        {
            "study_id": "S001",
            "citation": "Doe et al.",
            "year": 2020,
            "country": "USA",
            "design": "RCT",
            "outcome": "primary",
            "effect_type": "SMD",
            "effect": 0.20,
            "se": 0.10,
            "ci_lower": 0.00,
            "ci_upper": 0.40,
            "n_treat": 100,
            "n_control": 100,
            "notes": "Example placeholder row",
        },
        {
            "study_id": "S002",
            "citation": "Roe et al.",
            "year": 2018,
            "country": "UK",
            "design": "Quasi-experimental",
            "outcome": "primary",
            "effect_type": "SMD",
            "effect": 0.05,
            "se": 0.12,
            "ci_lower": -0.18,
            "ci_upper": 0.28,
            "n_treat": 80,
            "n_control": 85,
            "notes": "Example placeholder row",
        },
    ]
    return TemplateSpec("extraction_template.csv", DEFAULT_EXTRACTION_COLUMNS, rows)


def screening_log_spec() -> TemplateSpec:
    rows = [
        {
            "record_id": "R001",
            "source": "ExampleSearch",
            "title": "An example intervention study",
            "authors": "Doe, A.; Smith, B.",
            "year": 2020,
            "doi_or_url": "https://doi.org/10.0000/example1",
            "deduped": "yes",
            "screen_title_abstract_decision": "include",
            "screen_fulltext_decision": "include",
            "exclude_reason": "",
            "included_in_meta": "yes",
            "reviewer": "initials",
            "date": "2025-01-01",
            "notes": "Example placeholder row",
        },
        {
            "record_id": "R002",
            "source": "ExampleSearch",
            "title": "An example excluded study",
            "authors": "Roe, C.",
            "year": 2018,
            "doi_or_url": "https://doi.org/10.0000/example2",
            "deduped": "yes",
            "screen_title_abstract_decision": "exclude",
            "screen_fulltext_decision": "",
            "exclude_reason": "Wrong population",
            "included_in_meta": "no",
            "reviewer": "initials",
            "date": "2025-01-01",
            "notes": "Example placeholder row",
        },
    ]
    return TemplateSpec("screening_log.csv", DEFAULT_SCREENING_COLUMNS, rows)


def write_extraction_template(path: PathLike, overwrite: bool = False, columns: Optional[Sequence[str]] = None) -> Path:
    p = Path(path)
    spec = extraction_template_spec()
    cols = list(columns) if columns is not None else list(spec.columns)
    return _write_csv(p, cols, spec.example_rows, overwrite=overwrite)


def write_screening_log(path: PathLike, overwrite: bool = False, columns: Optional[Sequence[str]] = None) -> Path:
    p = Path(path)
    spec = screening_log_spec()
    cols = list(columns) if columns is not None else list(spec.columns)
    return _write_csv(p, cols, spec.example_rows, overwrite=overwrite)


def write_all_templates(output_dir: PathLike, overwrite: bool = False) -> Dict[str, Path]:
    out = Path(output_dir)
    spec1 = extraction_template_spec()
    spec2 = screening_log_spec()
    p1 = write_extraction_template(out / spec1.filename, overwrite=overwrite)
    p2 = write_screening_log(out / spec2.filename, overwrite=overwrite)
    return {"extraction_template": p1, "screening_log": p2}
