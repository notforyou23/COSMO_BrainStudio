"""Scaffolding utilities for the single blessed metadata workflow.

This module intentionally has no side effects on import; it is used by the
authoritative CLI entrypoint (tools/metadata_cli.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import json
import re
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
@dataclass(frozen=True)
class ScaffoldPlan:
    root: Path
    slug: str
    case_dir: Path
    metadata_path: Path
    created_paths: tuple[Path, ...]
def _today() -> str:
    return date.today().isoformat()


def normalize_slug(value: str) -> str:
    s = value.strip().lower().replace("_", "-").replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]+", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    if not s or not _SLUG_RE.match(s):
        raise ValueError(f"Invalid slug: {value!r} -> {s!r}")
    return s
def default_case_study_layout(root: Path, slug: str) -> Dict[str, Any]:
    """Return the canonical layout for a case study directory."""
    case_dir = root / "case_studies" / slug
    return {
        "case_dir": case_dir,
        "dirs": [
            case_dir,
            case_dir / "assets",
            case_dir / "data",
            case_dir / "outputs",
            case_dir / "notes",
        ],
        "files": [
            case_dir / "metadata.json",
            case_dir / "README.md",
        ],
    }
def metadata_template(slug: str, *, schema_ref: str = "../../schemas/METADATA_SCHEMA.json") -> Dict[str, Any]:
    """Create a conservative metadata template intended to validate widely.

    The authoritative schema may be more specific; this template uses common,
    minimal fields and keeps optional structures empty but well-typed.
    """
    return {
        "$schema": schema_ref,
        "id": slug,
        "title": "",
        "summary": "",
        "date_created": _today(),
        "version": "1.0.0",
        "owners": [],
        "contributors": [],
        "tags": [],
        "links": [],
        "inputs": [],
        "methods": [],
        "results": [],
        "artifacts": [],
        "notes": "",
    }
def readme_template(slug: str) -> str:
    return (
        f"# {slug}\n\n"
        "This directory was scaffolded by the repository metadata tooling.\n\n"
        "## Contents\n"
        "- metadata.json: Case study metadata (validated against METADATA_SCHEMA.json)\n"
        "- assets/: Figures, images, supporting documents\n"
        "- data/: Input data (or pointers/links if data is external)\n"
        "- outputs/: Generated outputs, reports, exports\n"
        "- notes/: Working notes\n"
    )
def scaffold_case_study(
    root: Path,
    slug: str,
    *,
    force: bool = False,
    schema_ref: str = "../../schemas/METADATA_SCHEMA.json",
) -> ScaffoldPlan:
    """Create the canonical case study directory and template files.

    Parameters
    ----------
    root:
        Repository root or working directory.
    slug:
        URL/filename-safe identifier (lowercase, hyphen-separated).
    force:
        If True, overwrite template files if they already exist.
    schema_ref:
        Value written into metadata.json as $schema.
    """
    root = Path(root)
    slug_n = normalize_slug(slug)
    layout = default_case_study_layout(root, slug_n)
    case_dir: Path = layout["case_dir"]
    created: list[Path] = []

    for d in layout["dirs"]:
        d.mkdir(parents=True, exist_ok=True)
        created.append(d)

    meta_path = case_dir / "metadata.json"
    if force or not meta_path.exists():
        meta = metadata_template(slug_n, schema_ref=schema_ref)
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        created.append(meta_path)

    readme_path = case_dir / "README.md"
    if force or not readme_path.exists():
        readme_path.write_text(readme_template(slug_n), encoding="utf-8")
        created.append(readme_path)

    return ScaffoldPlan(
        root=root,
        slug=slug_n,
        case_dir=case_dir,
        metadata_path=meta_path,
        created_paths=tuple(created),
    )
def ensure_parent(path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
