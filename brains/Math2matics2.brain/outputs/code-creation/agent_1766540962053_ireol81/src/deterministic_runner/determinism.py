"""Determinism utilities for reproducible runs.

This module centralizes seeding of RNGs and collection of small metadata to
support deterministic, comparable outputs across executions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform
import random
import subprocess
import sys
from typing import Any, Dict, Optional, Tuple
@dataclass(frozen=True)
class DeterminismConfig:
    """Configuration for deterministic behavior."""

    seed: int = 0
    python_hash_seed: int = 0
    set_source_date_epoch: bool = True
def set_global_determinism(config: DeterminismConfig = DeterminismConfig()) -> None:
    """Seed RNGs and set relevant environment variables.

    Notes
    -----
    - PYTHONHASHSEED only fully affects hashing if set before interpreter start.
      We still set it here for downstream subprocesses and to document intent.
    - numpy seeding is best-effort and is skipped if numpy is not installed.
    """
    if config.set_source_date_epoch:
        # Used by various tooling to avoid embedding current time in outputs.
        os.environ.setdefault("SOURCE_DATE_EPOCH", "0")

    os.environ.setdefault("PYTHONHASHSEED", str(config.python_hash_seed))

    random.seed(config.seed)

    try:
        import numpy as np  # type: ignore

        np.random.seed(config.seed)
    except Exception:
        # numpy is optional at library level; CLI may depend on it.
        pass
def make_numpy_generator(seed: int = 0):
    """Return a NumPy Generator seeded deterministically.

    Raises ImportError if numpy is not available.
    """
    import numpy as np  # type: ignore

    return np.random.default_rng(seed)
def stable_output_paths(base_dir: os.PathLike | str = "/outputs") -> Tuple[Path, Path]:
    """Return stable output paths (results.json, figure.png) under base_dir."""
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base / "results.json", base / "figure.png"
def _pkg_version(name: str) -> Optional[str]:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return None
def _git_hash(cwd: Optional[os.PathLike | str] = None) -> Optional[str]:
    """Best-effort short git hash; returns None if unavailable."""
    try:
        cp = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(cwd) if cwd is not None else None,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        out = cp.stdout.strip()
        return out or None
    except Exception:
        return None
def metadata(cwd: Optional[os.PathLike | str] = None) -> Dict[str, Any]:
    """Return a small, stable metadata block for result provenance."""
    return {
        "git_hash": _git_hash(cwd),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {
            "numpy": _pkg_version("numpy"),
            "matplotlib": _pkg_version("matplotlib"),
        },
    }
__all__ = [
    "DeterminismConfig",
    "make_numpy_generator",
    "metadata",
    "set_global_determinism",
    "stable_output_paths",
]
