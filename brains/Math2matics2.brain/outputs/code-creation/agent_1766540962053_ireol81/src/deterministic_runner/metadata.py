"""Reproducibility metadata helpers.

This module intentionally keeps metadata small and deterministic:
- Git commit hash (if available)
- Python version info
- Selected installed package versions
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
import platform
import subprocess
from typing import Iterable, Optional, Dict, Any
def _find_git_root(start: Path) -> Optional[Path]:
    """Walk parents looking for a .git directory."""
    cur = start
    for parent in [cur, *cur.parents]:
        if (parent / ".git").exists():
            return parent
    return None
def _git_commit_hash(repo_root: Optional[Path] = None) -> Optional[str]:
    """Return the current Git commit hash if available; otherwise None."""
    try:
        root = repo_root or _find_git_root(Path(__file__).resolve())
        if root is None:
            return None
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return out.decode("utf-8", "replace").strip() or None
    except Exception:
        return None
def _python_info() -> Dict[str, str]:
    """Return a small, stable python information mapping."""
    return {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
    }
def _package_versions(names: Iterable[str]) -> Dict[str, str]:
    """Return installed versions for the provided distributions."""
    versions: Dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib_metadata.version(name)
        except Exception:
            # Keep output deterministic: missing packages are simply omitted.
            continue
    return versions
def collect_metadata(
    package_names: Optional[Iterable[str]] = None,
    *,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Collect reproducibility metadata.

    Parameters
    ----------
    package_names:
        Iterable of distribution names to report versions for. If None, a small
        default set is used.
    repo_root:
        Optional path to a git repository root. If not provided, this module
        tries to discover a .git directory by walking parents.

    Returns
    -------
    dict
        Mapping with fixed top-level keys: git_commit, python, packages.
    """
    default_pkgs = ("deterministic-runner", "numpy", "matplotlib")
    pkgs = tuple(package_names) if package_names is not None else default_pkgs
    return {
        "git_commit": _git_commit_hash(repo_root=repo_root),
        "python": _python_info(),
        "packages": _package_versions(pkgs),
    }
