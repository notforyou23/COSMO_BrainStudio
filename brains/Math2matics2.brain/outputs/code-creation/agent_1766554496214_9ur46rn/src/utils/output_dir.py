"""Shared, repo-relative outputs directory helper.

Default: <repo_root>/outputs
Override: env var OUTPUT_DIR (absolute or repo-relative)
"""

from __future__ import annotations

from pathlib import Path
import os
from typing import Iterable, Optional, Union

PathLike = Union[str, os.PathLike]

_REPO_MARKERS: tuple[str, ...] = (
    "pyproject.toml",
    "setup.cfg",
    "setup.py",
    ".git",
    "requirements.txt",
)
def _find_repo_root(start: Optional[Path] = None) -> Path:
    """Find repo root by scanning parents for common project markers."""
    here = (start or Path(__file__)).resolve()
    for p in (here, *here.parents):
        for m in _REPO_MARKERS:
            if (p / m).exists():
                return p
    # Fallback: treat src/ as one level below root if present
    for p in (here, *here.parents):
        if p.name == "src":
            return p.parent
    return here.parent
def _normalize_dir(p: Path) -> Path:
    try:
        return p.expanduser().resolve()
    except Exception:
        return p.expanduser()
def get_repo_root() -> Path:
    """Return the detected repository root directory."""
    return _find_repo_root()
def get_output_dir() -> Path:
    """Return the output directory (repo-relative by default, env override allowed).

    Env:
      OUTPUT_DIR: absolute path OR path relative to repo root.
    """
    root = get_repo_root()
    override = os.environ.get("OUTPUT_DIR", "").strip()
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = root / candidate
        return _normalize_dir(candidate)
    return _normalize_dir(root / "outputs")
# Module-level constant for convenience (resolved on import).
OUTPUT_DIR: Path = get_output_dir()
def ensure_dir(path: PathLike) -> Path:
    """Create a directory (and parents) if needed; return resolved Path."""
    p = Path(path)
    if not p.is_absolute():
        p = OUTPUT_DIR / p
    p.mkdir(parents=True, exist_ok=True)
    return _normalize_dir(p)
def resolve_output_path(*parts: PathLike, mkdir: bool = False) -> Path:
    """Resolve an output path under OUTPUT_DIR unless given an absolute path."""
    if len(parts) == 1:
        candidate = Path(parts[0])
        if candidate.is_absolute():
            p = candidate
        else:
            p = OUTPUT_DIR / candidate
    else:
        p = OUTPUT_DIR
        for part in parts:
            p = p / Path(part)
    if mkdir:
        (p if p.suffix == "" else p.parent).mkdir(parents=True, exist_ok=True)
    return _normalize_dir(p)
def output_file(*parts: PathLike, mkdir: bool = True) -> Path:
    """Convenience wrapper for a file path under OUTPUT_DIR."""
    return resolve_output_path(*parts, mkdir=mkdir)
def output_subdir(*parts: PathLike, mkdir: bool = True) -> Path:
    """Convenience wrapper for a directory path under OUTPUT_DIR."""
    p = resolve_output_path(*parts, mkdir=False)
    if mkdir:
        p.mkdir(parents=True, exist_ok=True)
    return p
def as_posix(path: PathLike) -> str:
    """Return a stable posix string for a path (useful in logs/artifacts)."""
    return str(resolve_output_path(path)) if not Path(path).is_absolute() else str(Path(path))
__all__ = [
    "OUTPUT_DIR",
    "PathLike",
    "as_posix",
    "ensure_dir",
    "get_output_dir",
    "get_repo_root",
    "output_file",
    "output_subdir",
    "resolve_output_path",
]
