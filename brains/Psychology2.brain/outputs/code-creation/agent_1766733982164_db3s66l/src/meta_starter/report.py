"""Report/output writer for the minimal meta-analysis starter kit.

This module is intentionally small: given numeric results (rows of dicts),
it writes reproducible CSV tables into runtime/outputs/_build/.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
import csv
import json


@dataclass(frozen=True)
class ReportPaths:
    root: Path
    build_dir: Path
    tables_dir: Path
    manifest_path: Path

    @staticmethod
    def from_root(root: Path) -> "ReportPaths":
        build_dir = root / "_build"
        tables_dir = build_dir / "tables"
        manifest_path = build_dir / "manifest.json"
        return ReportPaths(root=root, build_dir=build_dir, tables_dir=tables_dir, manifest_path=manifest_path)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_build_dirs(root: Path) -> ReportPaths:
    paths = ReportPaths.from_root(root)
    paths.tables_dir.mkdir(parents=True, exist_ok=True)
    return paths


def _normalize_rows(rows: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(dict(r))
    return out


def write_csv_table(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Optional[Sequence[str]] = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    norm = _normalize_rows(rows)
    if not fieldnames:
        keys = set()
        for r in norm:
            keys.update(r.keys())
        fieldnames = sorted(keys)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        w.writeheader()
        for r in norm:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_manifest(paths: ReportPaths, *, tables: Sequence[str], meta: Optional[Mapping[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {
        "created_utc": _utc_now_iso(),
        "build_dir": str(paths.build_dir),
        "tables": list(tables),
    }
    if meta:
        payload["meta"] = dict(meta)
    paths.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    paths.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_and_write_outputs(
    *,
    output_root: Path,
    tables: Mapping[str, Sequence[Mapping[str, Any]]],
    meta: Optional[Mapping[str, Any]] = None,
) -> ReportPaths:
    """Write one or more numeric summary tables into output_root/_build/.

    Parameters
    ----------
    output_root:
        Typically Path('runtime/outputs') in the repository layout.
    tables:
        Mapping from filename (e.g., 'meta_summary.csv') to rows (list of dicts).
    meta:
        Optional metadata to record in the manifest.
    """
    paths = ensure_build_dirs(output_root)
    written: List[str] = []
    for name, rows in tables.items():
        fname = name if name.lower().endswith(".csv") else f"{name}.csv"
        out_path = paths.tables_dir / fname
        write_csv_table(out_path, rows)
        written.append(str(out_path.relative_to(paths.build_dir)))
    write_manifest(paths, tables=sorted(written), meta=meta)
    return paths


def write_minimal_meta_summary(
    *,
    output_root: Path,
    summary_row: Mapping[str, Any],
    filename: str = "meta_summary.csv",
    meta: Optional[Mapping[str, Any]] = None,
) -> ReportPaths:
    """Convenience helper: write a single-row meta-analysis summary table."""
    return build_and_write_outputs(output_root=output_root, tables={filename: [summary_row]}, meta=meta)
