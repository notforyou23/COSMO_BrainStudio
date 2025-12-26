from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional, Union

PathLike = Union[str, os.PathLike]


def repo_root(start: Optional[PathLike] = None) -> Path:
    """Return the repository root directory.

    Uses common sentinel files/dirs when available; otherwise falls back to the
    expected layout of this file at <root>/src/utils/paths.py.
    """
    if start is None:
        here = Path(__file__).resolve()
    else:
        here = Path(start).expanduser().resolve()

    sentinels = ("pyproject.toml", "setup.cfg", "setup.py", ".git", "requirements.txt")
    for p in (here,) + tuple(here.parents):
        for s in sentinels:
            if (p / s).exists():
                return p
        if (p / "src").is_dir():
            return p

    # Expected layout: <root>/src/utils/paths.py
    return Path(__file__).resolve().parents[2]


def _assert_writable_dir(p: Path) -> None:
    """Ensure p exists as a directory and is writable."""
    p.mkdir(parents=True, exist_ok=True)
    if not p.is_dir():
        raise NotADirectoryError(f"Outputs path exists but is not a directory: {p}")

    try:
        with tempfile.NamedTemporaryFile(prefix=".write_test_", dir=str(p), delete=True):
            pass
    except Exception as e:
        raise PermissionError(f"Outputs directory is not writable: {p}") from e


def outputs_path(*parts: PathLike, ensure_dir: bool = True) -> Path:
    """Resolve a writable outputs directory.

    Resolution order:
      1) OUTPUT_DIR environment variable (absolute or relative to repo root)
      2) <repo_root>/outputs

    If ensure_dir is True (default), the directory (and parents) are created and
    a small write test is performed.
    """
    base_env = os.environ.get("OUTPUT_DIR")
    root = repo_root()
    if base_env:
        base = Path(base_env).expanduser()
        if not base.is_absolute():
            base = (root / base).resolve()
    else:
        base = (root / "outputs").resolve()

    out = base.joinpath(*map(lambda x: Path(x), parts))
    if ensure_dir:
        _assert_writable_dir(out if not parts else out.parent if out.suffix else out)
        # If a filename was provided (has suffix), ensure parent exists; else ensure out exists.
        if parts and out.suffix:
            out.parent.mkdir(parents=True, exist_ok=True)
        else:
            out.mkdir(parents=True, exist_ok=True)
    return out
