from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional, Union

PathLike = Union[str, os.PathLike]


def _is_absolute_outputs_dir(p: Path) -> bool:
    try:
        p = Path(p)
    except TypeError:
        return False
    if not p.is_absolute():
        return False
    parts = p.parts
    return len(parts) >= 2 and parts[0] == os.sep and parts[1] == "outputs"


def _reject_absolute_outputs(p: Path, *, where: str = "path") -> None:
    if _is_absolute_outputs_dir(p):
        raise ValueError(f"{where} must not be an absolute '/outputs' path: {p}")


def get_output_dir(
    *,
    create: bool = True,
    env_var: str = "OUTPUT_DIR",
    default: PathLike = "outputs",
) -> Path:
    """Return the configured output directory.

    Uses env_var (default OUTPUT_DIR) when set; otherwise uses default (./outputs).
    Rejects an absolute '/outputs' directory to prevent writing to container-root paths.
    """
    raw = os.environ.get(env_var)
    base = Path(raw).expanduser() if raw else Path(default)
    _reject_absolute_outputs(base, where=env_var)
    base = (Path.cwd() / base) if not base.is_absolute() else base
    if create:
        base.mkdir(parents=True, exist_ok=True)
    return base


def within_output_dir(path: PathLike, *, output_dir: Optional[PathLike] = None) -> bool:
    """True iff path resolves within output_dir (default get_output_dir(create=False))."
    base = Path(output_dir).expanduser() if output_dir is not None else get_output_dir(create=False)
    _reject_absolute_outputs(base, where="output_dir")
    base = (Path.cwd() / base) if not base.is_absolute() else base
    try:
        base_r = base.resolve(strict=False)
        path_r = Path(path).expanduser()
        _reject_absolute_outputs(path_r, where="path")
        path_r = ((Path.cwd() / path_r) if not path_r.is_absolute() else path_r).resolve(strict=False)
        path_r.relative_to(base_r)
        return True
    except Exception:
        return False


def output_path(
    *parts: PathLike,
    create_parent: bool = True,
    output_dir: Optional[PathLike] = None,
) -> Path:
    """Build a path under the output directory and optionally create its parent."
    base = Path(output_dir).expanduser() if output_dir is not None else get_output_dir(create=True)
    _reject_absolute_outputs(base, where="output_dir")
    base = (Path.cwd() / base) if not base.is_absolute() else base

    rel = Path()
    for p in parts:
        pth = Path(p).expanduser()
        if pth.is_absolute():
            _reject_absolute_outputs(pth, where="path part")
            raise ValueError(f"path parts must be relative (got absolute): {pth}")
        rel = rel / pth

    full = base / rel
    if not within_output_dir(full, output_dir=base):
        raise ValueError(f"refusing to create path outside output_dir: {full}")

    if create_parent:
        full.parent.mkdir(parents=True, exist_ok=True)
    return full


def ensure_output_dir(*, env_var: str = "OUTPUT_DIR", default: PathLike = "outputs") -> Path:
    """Compatibility alias for get_output_dir(create=True)."
    return get_output_dir(create=True, env_var=env_var, default=default)
