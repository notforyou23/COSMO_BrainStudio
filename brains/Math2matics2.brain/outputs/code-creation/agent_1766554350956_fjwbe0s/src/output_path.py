"""
Centralized output-path helper.

Motivation:
- Avoid hard-coding absolute "/outputs" paths (which can be unwritable/non-portable).
- Provide one consistent mechanism for writers to place artifacts under a configurable base.

Usage note:
    from output_path import output_path, ensure_parent_dir

    p = output_path("runs", "run_001", "metrics.json", ensure_parent=True)
    p.write_text("{}", encoding="utf-8")

Configuration:
- Base output directory defaults to "./outputs"
- Override via environment variable OUTPUT_DIR (relative or absolute)
"""

from __future__ import annotations

from pathlib import Path
import os
from typing import Iterable, Optional, Union

ENV_OUTPUT_DIR = "OUTPUT_DIR"
DEFAULT_OUTPUT_DIR = Path("./outputs")


PathLike = Union[str, Path]


def get_output_dir() -> Path:
    """Return the configured output directory Path (not resolved)."""
    raw = os.environ.get(ENV_OUTPUT_DIR, "").strip()
    return Path(raw) if raw else DEFAULT_OUTPUT_DIR


def _coerce_parts(parts: Iterable[PathLike]) -> list[str]:
    out: list[str] = []
    for p in parts:
        if p is None:
            continue
        s = str(p)
        if s:
            out.append(s)
    return out


def safe_join(base: PathLike, *parts: PathLike) -> Path:
    """Join paths while preventing traversal outside base (checked via resolved paths)."""
    base_p = Path(base)
    rel_parts = _coerce_parts(parts)
    candidate = base_p.joinpath(*rel_parts)

    # Security/portability check: ensure resolved candidate stays within resolved base.
    # Return the non-resolved candidate so callers can keep paths relative if base is relative.
    base_abs = base_p.expanduser().resolve()
    cand_abs = candidate.expanduser().resolve()
    try:
        cand_abs.relative_to(base_abs)
    except Exception as e:
        raise ValueError(f"Refusing to write outside output dir: {candidate}") from e
    return candidate


def ensure_dir(path: PathLike) -> Path:
    """Ensure directory exists and return it."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_parent_dir(path: PathLike) -> Path:
    """Ensure parent directory exists and return the file path."""
    p = Path(path)
    ensure_dir(p.parent)
    return p


def output_path(*parts: PathLike, ensure_parent: bool = False) -> Path:
    """Build a path under the configured output directory."""
    base = get_output_dir()
    p = safe_join(base, *parts)
    return ensure_parent_dir(p) if ensure_parent else p


def output_dir(*parts: PathLike, ensure: bool = False) -> Path:
    """Build a directory path under the configured output directory."""
    base = get_output_dir()
    p = safe_join(base, *parts)
    return ensure_dir(p) if ensure else p
