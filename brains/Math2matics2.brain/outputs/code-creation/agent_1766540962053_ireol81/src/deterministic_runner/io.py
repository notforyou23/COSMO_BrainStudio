"""Deterministic I/O utilities.

This module is responsible for creating an outputs directory and writing:
- results.json (stable filenames; stable JSON formatting; fixed top-level keys)
- figure.png
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping, Optional

try:
    from importlib import metadata as importlib_metadata  # py3.8+
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore
@dataclass(frozen=True)
class OutputPaths:
    """Resolved output file locations."""

    outputs_dir: Path
    results_json: Path
    figure_png: Path


def prepare_outputs_dir(outputs_dir: Optional[os.PathLike[str] | str] = None) -> OutputPaths:
    """Create outputs directory and return resolved paths.

    If outputs_dir is None, uses the absolute directory '/outputs' to match the
    project contract.
    """
    out_dir = Path(outputs_dir) if outputs_dir is not None else Path("/outputs")
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return OutputPaths(
        outputs_dir=out_dir,
        results_json=out_dir / "results.json",
        figure_png=out_dir / "figure.png",
    )
def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _safe_run_git_rev_parse(cwd: Path) -> Optional[str]:
    git_dir = cwd / ".git"
    if not git_dir.exists():
        return None
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
        )
        sha = (res.stdout or "").strip()
        return sha if res.returncode == 0 and sha else None
    except Exception:
        return None


def collect_metadata(project_root: Optional[os.PathLike[str] | str] = None) -> dict[str, Any]:
    """Collect a small, deterministic metadata block."""
    root = Path(project_root).resolve() if project_root is not None else Path.cwd().resolve()
    versions: dict[str, Optional[str]] = {}
    for name in ("numpy", "matplotlib", "deterministic_runner"):
        try:
            versions[name] = importlib_metadata.version(name)
        except Exception:
            versions[name] = None

    meta: dict[str, Any] = {
        "git_hash": _safe_run_git_rev_parse(root),
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "package_versions": versions,
    }
    return meta
def write_results_json(
    paths: OutputPaths,
    results: Mapping[str, Any],
    metadata: Optional[Mapping[str, Any]] = None,
) -> None:
    """Write /outputs/results.json with stable formatting and fixed keys."""
    payload: dict[str, Any] = {
        "results": dict(results),
        "metadata": dict(metadata) if metadata is not None else collect_metadata(),
    }
    # Deterministic JSON: sorted keys; fixed separators; newline at EOF.
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text(paths.results_json, text)
def write_figure_png(paths: OutputPaths, figure: Any, *, dpi: int = 150) -> None:
    """Write /outputs/figure.png.

    Accepts a matplotlib.figure.Figure-like object (must implement savefig()).
    """
    if not hasattr(figure, "savefig"):
        raise TypeError("figure must be a matplotlib Figure (or Figure-like with savefig)")
    # Provide stable save parameters; avoid embedding varying timestamps/metadata.
    save_kwargs = {
        "format": "png",
        "dpi": dpi,
        "bbox_inches": "tight",
        "facecolor": "white",
        "edgecolor": "none",
        "metadata": {"Software": "deterministic_runner"},
    }
    figure.savefig(paths.figure_png, **save_kwargs)  # type: ignore[arg-type]
def write_outputs(
    results: Mapping[str, Any],
    figure: Any,
    *,
    outputs_dir: Optional[os.PathLike[str] | str] = None,
    project_root: Optional[os.PathLike[str] | str] = None,
) -> OutputPaths:
    """Convenience wrapper to prepare directory and write both outputs."""
    paths = prepare_outputs_dir(outputs_dir)
    meta = collect_metadata(project_root)
    write_results_json(paths, results=results, metadata=meta)
    write_figure_png(paths, figure=figure)
    return paths
