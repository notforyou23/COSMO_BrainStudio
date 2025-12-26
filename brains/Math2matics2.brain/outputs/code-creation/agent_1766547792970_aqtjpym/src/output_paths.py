from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

_DEFAULT_ENV_VAR = "PIPELINE_OUTPUT_DIR"
_DEFAULT_DIRNAME = "outputs"


def _repo_root_from_here(here: Optional[Union[str, Path]] = None) -> Path:
    p = Path(here).resolve() if here is not None else Path(__file__).resolve()
    # Expected layout: <repo_root>/src/output_paths.py
    # If that isn't true, fall back to current working directory.
    try:
        return p.parents[1]
    except IndexError:
        return Path.cwd().resolve()


def resolve_output_dir(
    env_var: str = _DEFAULT_ENV_VAR,
    default_dirname: str = _DEFAULT_DIRNAME,
    create: bool = True,
    repo_root: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Resolve the canonical pipeline output directory.

    Default: repo-relative ./outputs/ (i.e., <repo_root>/outputs).
    Override: set environment variable (default PIPELINE_OUTPUT_DIR) to either:
      - a relative path (resolved against <repo_root>)
      - an absolute path (used as-is)

    The returned path is created when create=True.
    """
    root = Path(repo_root).resolve() if repo_root is not None else _repo_root_from_here()
    raw = (os.environ.get(env_var) or "").strip()

    if raw:
        candidate = Path(raw)
        out_dir = candidate if candidate.is_absolute() else (root / candidate)
    else:
        out_dir = root / default_dirname

    out_dir = out_dir.resolve()

    if create:
        out_dir.mkdir(parents=True, exist_ok=True)

    return out_dir


def output_path(*parts: Union[str, Path], **kwargs) -> Path:
    """
    Convenience helper: join path parts under the resolved output directory.
    Accepts the same kwargs as resolve_output_dir (env_var, create, repo_root, etc.).
    """
    base = resolve_output_dir(**kwargs)
    return base.joinpath(*map(str, parts))
