"""I/O utilities for experiment outputs.

Provides standardized run directories, CSV result export/import, and
figure writing with JSON sidecar metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import csv
import json
import os
import uuid
def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_run_id(prefix: str | None = None) -> str:
    """Create a sortable run identifier (UTC timestamp + random suffix)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suf = uuid.uuid4().hex[:8]
    return f"{prefix + '-' if prefix else ''}{ts}-{suf}"


def default_base_dir() -> Path:
    """Base directory for outputs; controlled via EXPERIMENTS_OUT."""
    return Path(os.environ.get("EXPERIMENTS_OUT", "outputs")).resolve()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
@dataclass(frozen=True)
class RunPaths:
    """Standard locations for a single run."""

    base_dir: Path
    run_id: str

    @property
    def run_dir(self) -> Path:
        return self.base_dir / "runs" / self.run_id

    @property
    def figures_dir(self) -> Path:
        return self.run_dir / "figures"

    @property
    def results_dir(self) -> Path:
        return self.run_dir / "results"

    @property
    def metadata_path(self) -> Path:
        return self.run_dir / "run_metadata.json"

    def mkdirs(self) -> "RunPaths":
        ensure_dir(self.figures_dir)
        ensure_dir(self.results_dir)
        ensure_dir(self.run_dir)
        return self
def init_run(
    base_dir: str | Path | None = None,
    run_id: str | None = None,
    *,
    prefix: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> RunPaths:
    """Create a run directory and write run-level metadata."""
    base = Path(base_dir) if base_dir is not None else default_base_dir()
    rid = run_id or make_run_id(prefix=prefix)
    paths = RunPaths(base_dir=base, run_id=rid).mkdirs()
    meta = {"run_id": rid, "created_utc": utc_now(), **(dict(metadata or {}))}
    paths.metadata_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return paths
def save_results_csv(
    rows: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]],
    path: str | Path,
    *,
    dialect: str = "excel",
) -> Path:
    """Write a list/iterable of dict-like rows to CSV with stable headers."""
    p = Path(path)
    ensure_dir(p.parent)
    rows_list = list(rows)
    keys: list[str] = sorted({k for r in rows_list for k in r.keys()})
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, dialect=dialect)
        w.writeheader()
        for r in rows_list:
            w.writerow({k: r.get(k, "") for k in keys})
    return p


def load_results_csv(path: str | Path, *, dialect: str = "excel") -> list[dict[str, str]]:
    """Load CSV results previously written by :func:`save_results_csv`."""
    p = Path(path)
    with p.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f, dialect=dialect)
        return [dict(row) for row in r]
def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    ensure_dir(path.parent)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")
    return path


def save_figure(
    fig: Any,
    paths: RunPaths,
    name: str,
    *,
    formats: Sequence[str] = ("png", "svg"),
    dpi: int = 200,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Path]:
    """Save a matplotlib-like figure to standard locations with metadata."""
    out: dict[str, Path] = {}
    ensure_dir(paths.figures_dir)
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name).strip("._") or "figure"
    for fmt in formats:
        fp = paths.figures_dir / f"{safe}.{fmt}"
        fig.savefig(fp, dpi=dpi, bbox_inches="tight")
        out[fmt] = fp
    _write_json(
        paths.figures_dir / f"{safe}.json",
        {
            "run_id": paths.run_id,
            "name": safe,
            "created_utc": utc_now(),
            "formats": list(formats),
            **(dict(metadata or {})),
        },
    )
    return out
def standard_results_path(paths: RunPaths, stem: str = "results") -> Path:
    """Convenience helper for placing CSV results under a run directory."""
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in stem).strip("._") or "results"
    return paths.results_dir / f"{safe}.csv"
