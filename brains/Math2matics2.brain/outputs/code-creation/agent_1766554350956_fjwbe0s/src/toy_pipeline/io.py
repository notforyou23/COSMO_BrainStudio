"""I/O utilities for reproducible toy-pipeline artifacts.

This module provides:
- ensure_outputs_dir: create (if needed) and return an outputs directory Path.
- write_json_canonical: write JSON with stable formatting for reproducibility.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
from typing import Any, Mapping, Optional


DEFAULT_OUTPUTS_DIRNAME = "outputs"


def ensure_outputs_dir(base_dir: Optional[Path] = None, dirname: str = DEFAULT_OUTPUTS_DIRNAME) -> Path:
    """Create and return the outputs directory.

    Parameters
    ----------
    base_dir:
        Base directory to create the outputs directory within. If None, uses the
        current working directory.
    dirname:
        Name of the outputs directory.

    Returns
    -------
    Path
        The outputs directory path (created if it did not exist).
    """
    base = Path.cwd() if base_dir is None else Path(base_dir)
    out_dir = base / dirname
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _canonical_json_dumps(obj: Any) -> str:
    """Serialize to stable JSON (sorted keys, fixed indentation, LF newline)."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ": "),
        indent=2,
    ) + "\n"


def write_json_canonical(path: Path, data: Any, *, make_parents: bool = True) -> Path:
    """Write canonical JSON to `path` atomically.

    The write is performed via a temporary file in the same directory and then
    replaced to avoid partial writes.

    Parameters
    ----------
    path:
        Target file path.
    data:
        JSON-serializable object.
    make_parents:
        If True, create parent directories as needed.

    Returns
    -------
    Path
        The written file path.
    """
    p = Path(path)
    if make_parents:
        p.parent.mkdir(parents=True, exist_ok=True)

    text = _canonical_json_dumps(data)
    dir_path = p.parent

    fd, tmp_name = tempfile.mkstemp(prefix=f".{p.name}.", suffix=".tmp", dir=str(dir_path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, p)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except OSError:
            pass
    return p


def write_metrics_json(outputs_dir: Path, metrics: Mapping[str, Any], filename: str = "metrics.json") -> Path:
    """Convenience helper to write metrics JSON to an outputs directory."""
    out_dir = ensure_outputs_dir(outputs_dir, dirname=".")
    return write_json_canonical(out_dir / filename, dict(metrics))
