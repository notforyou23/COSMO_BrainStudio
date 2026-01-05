"""Path and filesystem utilities for project-relative build outputs.

All build artifacts should be written under the project-level "_build/" directory.

Example:
    from scripts.path_utils import build_dir, build_path, clean_dir
    out = build_path("logs", "artifact_gate.log", ensure_parent=True)
    clean_dir(build_dir())
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
from typing import Iterable, Optional, Union

PathLike = Union[str, os.PathLike, Path]
def project_root(start: Optional[PathLike] = None) -> Path:
    """Return the project root directory.

    Default: the parent of the 'scripts' directory containing this file.
    If 'start' is provided, walk upward to find a likely root marker.
    """
    if start is None:
        return Path(__file__).resolve().parents[1]

    p = Path(start).resolve()
    if p.is_file():
        p = p.parent

    markers = ("pyproject.toml", "requirements.txt", ".git", "scripts")
    for cur in (p, *p.parents):
        for m in markers:
            if (cur / m).exists():
                if m == "scripts":
                    return cur
                return cur
    return Path(start).resolve() if Path(start).resolve().is_dir() else Path(start).resolve().parent
def build_dir(root: Optional[PathLike] = None, ensure: bool = True) -> Path:
    """Return the '_build' directory under the project root."""
    r = project_root(root)
    b = r / "_build"
    if ensure:
        b.mkdir(parents=True, exist_ok=True)
    return b


def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_path(*parts: PathLike, root: Optional[PathLike] = None, ensure_parent: bool = False) -> Path:
    """Resolve a path under '_build' with optional parent creation."""
    p = build_dir(root=root, ensure=True).joinpath(*(Path(x) for x in parts))
    if ensure_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p
def safe_unlink(path: PathLike, missing_ok: bool = True) -> None:
    p = Path(path)
    try:
        p.unlink()
    except FileNotFoundError:
        if not missing_ok:
            raise
    except IsADirectoryError:
        # Fall back to rmtree for directories.
        safe_rmtree(p, missing_ok=missing_ok)


def safe_rmtree(path: PathLike, missing_ok: bool = True) -> None:
    p = Path(path)
    if not p.exists():
        if missing_ok:
            return
        raise FileNotFoundError(str(p))
    shutil.rmtree(p)


def clean_dir(path: PathLike, keep_dir: bool = True) -> Path:
    """Delete all contents of a directory; optionally delete the directory itself."""
    p = Path(path)
    if p.exists() and p.is_dir():
        for child in p.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    elif p.exists():
        raise NotADirectoryError(str(p))
    if keep_dir:
        p.mkdir(parents=True, exist_ok=True)
    else:
        safe_rmtree(p, missing_ok=True)
    return p
@dataclass(frozen=True)
class BuildLayout:
    """Convenience accessors for common build output locations."""
    root: Path

    @classmethod
    def from_root(cls, root: Optional[PathLike] = None) -> "BuildLayout":
        return cls(build_dir(root=root, ensure=True))

    def logs_dir(self) -> Path:
        return ensure_dir(self.root / "logs")

    def step_dir(self, step_name: str) -> Path:
        return ensure_dir(self.root / "steps" / step_name)

    def log_file(self, step_name: str, filename: str = "run.log") -> Path:
        d = self.step_dir(step_name)
        return d / filename
