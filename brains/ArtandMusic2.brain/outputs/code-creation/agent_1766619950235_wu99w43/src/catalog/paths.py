from __future__ import annotations

from pathlib import Path
import os
from typing import Optional


def _default_project_root() -> Path:
    # This file lives at: <root>/src/catalog/paths.py
    return Path(__file__).resolve().parents[2]


def project_root() -> Path:
    """Return the project root directory.

    Resolution order:
      1) COSMO_PROJECT_ROOT (if set)
      2) derived from this file location
    """
    env = os.environ.get("COSMO_PROJECT_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return _default_project_root()


def outputs_root() -> Path:
    """Return the outputs root directory.

    Resolution order:
      1) COSMO_OUTPUTS_ROOT (if set)
      2) <project_root>/outputs
    """
    env = os.environ.get("COSMO_OUTPUTS_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return project_root() / "outputs"


def catalog_dir(ensure: bool = False) -> Path:
    """Return outputs/catalog."""
    p = outputs_root() / "catalog"
    if ensure:
        p.mkdir(parents=True, exist_ok=True)
    return p


def case_studies_dir(ensure: bool = False) -> Path:
    """Return outputs/case_studies."""
    p = outputs_root() / "case_studies"
    if ensure:
        p.mkdir(parents=True, exist_ok=True)
    return p


def metadata_schema_path() -> Path:
    """Return outputs/catalog/METADATA_SCHEMA.json."""
    return catalog_dir() / "METADATA_SCHEMA.json"


def case_studies_index_path(ensure_parent: bool = False) -> Path:
    """Return outputs/case_studies/index.json."""
    p = case_studies_dir() / "index.json"
    if ensure_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


def case_study_dir(slug: str, ensure: bool = False) -> Path:
    """Return outputs/case_studies/<slug>."""
    if not slug or not slug.strip():
        raise ValueError("slug must be a non-empty string")
    slug = slug.strip()
    p = case_studies_dir() / slug
    if ensure:
        p.mkdir(parents=True, exist_ok=True)
    return p


def case_study_json_path(slug: str, ensure_parent: bool = False) -> Path:
    """Return outputs/case_studies/<slug>/case_study.json."""
    p = case_study_dir(slug) / "case_study.json"
    if ensure_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


def resolve_under_outputs(*parts: str, ensure_parent: bool = False) -> Path:
    """Resolve a path under outputs_root for misc tooling needs."""
    p = outputs_root().joinpath(*parts)
    if ensure_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p
