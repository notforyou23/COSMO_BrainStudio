from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, os.PathLike]


def project_root(start: Optional[PathLike] = None) -> Path:
    """Return repository/project root assuming this file lives under <root>/scripts/.

    Falls back to the current working directory if resolution fails.
    """
    if start is None:
        here = Path(__file__).resolve()
    else:
        here = Path(start).expanduser().resolve()
    for p in (here,) + tuple(here.parents):
        if p.name == "scripts" and p.parent.exists():
            return p.parent
    return Path.cwd().resolve()


def outputs_root(root: Optional[PathLike] = None, ensure: bool = True) -> Path:
    """Canonical outputs root with env overrides suitable for local/CI/Docker runs."""
    override = (
        os.environ.get("COSMO_OUTPUTS_DIR")
        or os.environ.get("OUTPUTS_DIR")
        or os.environ.get("OUTPUT_DIR")
    )
    base = Path(override).expanduser() if override else project_root(root) / "outputs"
    out = base.resolve() if base.exists() else base.absolute()
    if ensure:
        out.mkdir(parents=True, exist_ok=True)
    return out


def qa_root(root: Optional[PathLike] = None, ensure: bool = True) -> Path:
    p = outputs_root(root, ensure=ensure) / "qa"
    if ensure:
        p.mkdir(parents=True, exist_ok=True)
    return p


def qa_exec_logs_dir(root: Optional[PathLike] = None, ensure: bool = True) -> Path:
    """Canonical directory for full stdout/stderr artifacts: outputs/qa/exec_logs/."""
    p = qa_root(root, ensure=ensure) / "exec_logs"
    if ensure:
        p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_dir(path: PathLike) -> Path:
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def canonicalize(path: PathLike, root: Optional[PathLike] = None, ensure_parent: bool = True) -> Path:
    """Return an absolute path; if relative, interpret relative to project root."""
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = project_root(root) / p
    p = p.resolve() if p.exists() else p.absolute()
    if ensure_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


def artifact_path(
    filename: str,
    *,
    root: Optional[PathLike] = None,
    subdir: Optional[PathLike] = None,
    ensure_parent: bool = True,
) -> Path:
    """Build an artifact path under outputs/qa/exec_logs/ by default."""
    base = qa_exec_logs_dir(root, ensure=True)
    if subdir:
        base = base / Path(subdir)
    p = (base / filename).expanduser()
    if ensure_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


__all__ = [
    "project_root",
    "outputs_root",
    "qa_root",
    "qa_exec_logs_dir",
    "ensure_dir",
    "canonicalize",
    "artifact_path",
]
