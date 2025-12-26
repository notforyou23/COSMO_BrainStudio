from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional, Union

PathLike = Union[str, os.PathLike]


def project_root(start: Optional[PathLike] = None) -> Path:
    """Best-effort repository root (walks up looking for pyproject/setup/.git)."""
    p = Path(start).resolve() if start is not None else Path.cwd().resolve()
    for cur in (p, *p.parents):
        if (cur / "pyproject.toml").is_file() or (cur / "setup.cfg").is_file() or (cur / ".git").exists():
            return cur
    return p


def resolve_output_dir(
    base_dir: Optional[PathLike] = None,
    env_var: str = "OUTPUT_DIR",
    default: PathLike = "./outputs",
) -> Path:
    """Resolve the output directory path.

    Precedence:
      1) env var (default OUTPUT_DIR), if set and non-empty
      2) default (./outputs)

    If the resolved path is relative, it is interpreted relative to base_dir
    (default: project_root()).
    """
    raw = os.getenv(env_var, "").strip() or str(default)
    p = Path(raw).expanduser()
    if not p.is_absolute():
        base = project_root(base_dir) if base_dir is not None else project_root()
        p = (base / p).resolve()
    else:
        p = p.resolve()

    # Guardrail: discourage the common mistake of hardcoding "/outputs"
    if str(p) == "/outputs":
        raise ValueError('Invalid OUTPUT_DIR="/outputs". Use a repo-relative path (e.g. "./outputs") or a configured absolute path.')

    return p


def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def output_dir(base_dir: Optional[PathLike] = None) -> Path:
    """Convenience accessor for the resolved OUTPUT_DIR."""
    return resolve_output_dir(base_dir=base_dir)


def output_path(
    *parts: PathLike,
    base_dir: Optional[PathLike] = None,
    mkdir: bool = False,
) -> Path:
    """Build a path under OUTPUT_DIR.

    Example:
        output_path("runs", "exp1", "metrics.json", mkdir=True)
    """
    out = output_dir(base_dir=base_dir)
    p = out.joinpath(*map(str, parts))
    if mkdir:
        ensure_dir(p.parent)
    return p


def is_within(child: PathLike, parent: PathLike) -> bool:
    """Return True if child is the same as or located under parent."""
    c = Path(child).resolve()
    p = Path(parent).resolve()
    try:
        c.relative_to(p)
        return True
    except Exception:
        return False


def require_within_output(path: PathLike, base_dir: Optional[PathLike] = None) -> Path:
    """Resolve a path and require it to be within OUTPUT_DIR."""
    p = Path(path).expanduser().resolve()
    out = output_dir(base_dir=base_dir)
    if not is_within(p, out):
        raise ValueError(f"Path must be within OUTPUT_DIR ({out}): {p}")
    return p
