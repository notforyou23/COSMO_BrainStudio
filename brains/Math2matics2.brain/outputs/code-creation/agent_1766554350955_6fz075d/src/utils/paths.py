from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional, Union

PathLike = Union[str, os.PathLike, Path]

_DEFAULT_OUTPUT_DIR_STR = "./outputs"


def _norm_pathlike(p: PathLike) -> Path:
    return p if isinstance(p, Path) else Path(p)


def resolve_output_dir(
    value: Optional[PathLike] = None,
    *,
    env_var: str = "OUTPUT_DIR",
    default: PathLike = _DEFAULT_OUTPUT_DIR_STR,
    cwd: Optional[PathLike] = None,
) -> Path:
    """Resolve the configured output directory as an absolute Path.

    Precedence:
      1) `value` argument if provided
      2) environment variable `env_var` if set and non-empty
      3) `default` (defaults to ./outputs)

    Relative paths are interpreted relative to `cwd` if provided, else Path.cwd().
    """
    if value is None:
        env_val = os.environ.get(env_var)
        if env_val:
            value = env_val
        else:
            value = default

    base = _norm_pathlike(cwd) if cwd is not None else Path.cwd()
    p = _norm_pathlike(value)
    if not p.is_absolute():
        p = base / p
    return p.resolve()


OUTPUT_DIR: Path = resolve_output_dir()


def ensure_dir(path: PathLike) -> Path:
    """Create directory (and parents) if missing; return it as Path."""
    p = _norm_pathlike(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def output_path(
    *parts: PathLike,
    output_dir: Optional[PathLike] = None,
    ensure_parent: bool = True,
) -> Path:
    """Build a path under OUTPUT_DIR (or a provided override).

    Example:
        output_path("runs", "exp1", "metrics.json")
    """
    root = resolve_output_dir(output_dir) if output_dir is not None else OUTPUT_DIR
    p = root
    for part in parts:
        p = p / _norm_pathlike(part)
    if ensure_parent:
        ensure_dir(p.parent)
    return p


def output_paths(
    items: Iterable[PathLike],
    *,
    prefix: Optional[PathLike] = None,
    output_dir: Optional[PathLike] = None,
    ensure_parent: bool = True,
) -> list[Path]:
    """Vectorized variant of `output_path` for many leaf items."""
    out: list[Path] = []
    for item in items:
        if prefix is None:
            out.append(output_path(item, output_dir=output_dir, ensure_parent=ensure_parent))
        else:
            out.append(output_path(prefix, item, output_dir=output_dir, ensure_parent=ensure_parent))
    return out
