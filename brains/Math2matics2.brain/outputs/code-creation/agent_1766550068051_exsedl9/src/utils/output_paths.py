from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional, Union

PathLike = Union[str, os.PathLike, Path]

def _default_output_dir() -> Path:
    # Safe, portable default: project-relative "./outputs"
    return Path(os.getenv("OUTPUT_DIR", "./outputs")).expanduser()

OUTPUT_DIR: Path = _default_output_dir()

def get_output_dir(*parts: PathLike, create: bool = True) -> Path:
    """Return OUTPUT_DIR / parts, optionally creating the directory."""
    p = OUTPUT_DIR.joinpath(*map(str, parts)) if parts else OUTPUT_DIR
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p

def ensure_dir(path: PathLike) -> Path:
    """Create directory (and parents) if missing and return Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def out_path(*parts: PathLike, parent: Optional[PathLike] = None, create_parent: bool = True) -> Path:
    """Join paths under OUTPUT_DIR (or a provided parent); optionally create parent directory."""
    base = Path(parent) if parent is not None else OUTPUT_DIR
    p = base.joinpath(*map(str, parts)) if parts else base
    if create_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p

def out_file(relpath: PathLike, *, create_parent: bool = True) -> Path:
    """Convenience for a single relative file path under OUTPUT_DIR."""
    rp = Path(relpath)
    return out_path(*rp.parts, create_parent=create_parent)

def list_output_files(subdir: Optional[PathLike] = None, pattern: str = "*") -> Iterable[Path]:
    """List files under OUTPUT_DIR (or a subdir) matching a glob pattern."""
    base = get_output_dir(subdir, create=False) if subdir is not None else OUTPUT_DIR
    if not base.exists():
        return ()
    return (p for p in base.glob(pattern) if p.is_file())

__all__ = [
    "OUTPUT_DIR",
    "get_output_dir",
    "ensure_dir",
    "out_path",
    "out_file",
    "list_output_files",
]
