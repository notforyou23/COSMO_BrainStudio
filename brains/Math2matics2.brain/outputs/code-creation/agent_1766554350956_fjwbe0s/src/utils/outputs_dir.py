from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_ENV_VAR = "OUTPUTS_DIR"
_DEFAULT = Path("./outputs")


def resolve_outputs_dir(base_dir: Optional[os.PathLike | str] = None) -> Path:
    """
    Resolve and (if needed) create the configured outputs directory.

    Precedence:
      1) Environment variable OUTPUTS_DIR (if set and non-empty)
      2) default ./outputs (relative to the current working directory)

    If base_dir is provided, the resolved outputs directory is interpreted
    relative to base_dir when it is not absolute.
    """
    raw = os.environ.get(_ENV_VAR, "")
    chosen = Path(raw) if raw.strip() else _DEFAULT

    if base_dir is not None:
        base = Path(base_dir)
        if not chosen.is_absolute():
            chosen = base / chosen

    out_dir = chosen.expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def outputs_path(*parts: str, base_dir: Optional[os.PathLike | str] = None) -> Path:
    """Convenience helper: resolve_outputs_dir(...)/Path(*parts)."""
    return resolve_outputs_dir(base_dir=base_dir).joinpath(*parts)


__all__ = ["resolve_outputs_dir", "outputs_path"]
