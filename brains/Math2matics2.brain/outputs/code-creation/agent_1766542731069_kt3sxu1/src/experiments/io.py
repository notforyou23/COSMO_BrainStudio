"""I/O helpers for experiment sweeps.

This module provides small, reusable functions to read/write sweep artifacts with
consistent schemas and friendly errors. It is intentionally dependency-light
(only stdlib) to keep it usable in scripts and tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple
import csv
import json
import os
import tempfile
class SweepIOError(RuntimeError):
    """Raised when a sweep artifact cannot be read/written or validated."""

@dataclass(frozen=True)
class SweepPaths:
    """Conventional file layout for a single sweep run directory."""

    run_dir: Path
    config_name: str = "config.json"
    results_name: str = "results.csv"
    metadata_name: str = "metadata.json"

    @property
    def config_path(self) -> Path:
        return self.run_dir / self.config_name

    @property
    def results_path(self) -> Path:
        return self.run_dir / self.results_name

    @property
    def metadata_path(self) -> Path:
        return self.run_dir / self.metadata_name
def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text atomically (best-effort) to avoid partially-written files."""
    _ensure_parent(path)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception as e:  # pragma: no cover (cleanup path)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise SweepIOError(f"Failed writing {path}: {e}") from e

def _require_mapping(obj: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise SweepIOError(f"{context} must be a JSON object (mapping), got {type(obj).__name__}")
    return obj

def _require_keys(d: Mapping[str, Any], keys: Sequence[str], *, context: str) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise SweepIOError(f"{context} missing required keys: {missing}")
def read_json(path: Path) -> Any:
    """Read JSON from *path* with consistent error messages."""
    try:
        text = Path(path).read_text(encoding="utf-8")
        return json.loads(text)
    except FileNotFoundError as e:
        raise SweepIOError(f"JSON file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise SweepIOError(f"Invalid JSON in {path}: {e}") from e
    except OSError as e:
        raise SweepIOError(f"Failed reading {path}: {e}") from e

def write_json(path: Path, obj: Any, *, indent: int = 2, sort_keys: bool = True) -> None:
    """Write JSON to *path* atomically."""
    try:
        text = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False) + "\n"
    except TypeError as e:
        raise SweepIOError(f"Object not JSON-serializable for {path}: {e}") from e
    _atomic_write_text(Path(path), text)
def read_config(path: Path) -> Dict[str, Any]:
    """Read an experiment/sweep config JSON object."""
    obj = read_json(path)
    cfg = dict(_require_mapping(obj, context=f"Config {path}"))
    # Convention: allow 'params' for sweep parameters; optional.
    if "params" in cfg:
        _require_mapping(cfg["params"], context=f"Config {path}['params']")
        cfg["params"] = dict(cfg["params"])
    return cfg

def write_config(path: Path, config: Mapping[str, Any]) -> None:
    _require_mapping(config, context="config")
    write_json(path, dict(config))
def _coerce_scalar(s: str) -> Any:
    """Best-effort parse for CSV cells written from python scalars."""
    if s == "":
        return ""
    sl = s.lower()
    if sl == "null" or sl == "none":
        return None
    if sl == "true":
        return True
    if sl == "false":
        return False
    try:
        if "." in s or "e" in sl:
            return float(s)
        return int(s)
    except ValueError:
        return s

def read_results_csv(path: Path) -> List[Dict[str, Any]]:
    """Read a results table from CSV as a list of dict rows."""
    try:
        with Path(path).open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return []
            rows: List[Dict[str, Any]] = []
            for r in reader:
                rows.append({k: _coerce_scalar(v) for k, v in r.items()})
            return rows
    except FileNotFoundError as e:
        raise SweepIOError(f"Results CSV not found: {path}") from e
    except csv.Error as e:
        raise SweepIOError(f"Invalid CSV in {path}: {e}") from e
    except OSError as e:
        raise SweepIOError(f"Failed reading {path}: {e}") from e

def write_results_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write a results table to CSV atomically.

    Fieldnames are the union of keys across rows (stable order by first occurrence).
    """
    rows_l = [dict(r) for r in rows]
    fieldnames: List[str] = []
    seen = set()
    for r in rows_l:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)
    text_io: List[str] = []
    try:
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows_l:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in r.items()})
        text = buf.getvalue()
    except Exception as e:
        raise SweepIOError(f"Failed serializing results for {path}: {e}") from e
    _atomic_write_text(Path(path), text)
def read_metadata(path: Path) -> Dict[str, Any]:
    """Read metadata JSON object (e.g., timing, git sha, host info)."""
    meta = dict(_require_mapping(read_json(path), context=f"Metadata {path}"))
    return meta

def write_metadata(path: Path, metadata: Mapping[str, Any]) -> None:
    _require_mapping(metadata, context="metadata")
    write_json(path, dict(metadata))
def load_run(run_dir: Path, *, required: Tuple[str, ...] = ("config", "results", "metadata")) -> Dict[str, Any]:
    """Load a conventional run directory into a dict with keys: config/results/metadata."""
    sp = SweepPaths(Path(run_dir))
    out: Dict[str, Any] = {}
    if "config" in required or sp.config_path.exists():
        out["config"] = read_config(sp.config_path)
    if "results" in required or sp.results_path.exists():
        out["results"] = read_results_csv(sp.results_path)
    if "metadata" in required or sp.metadata_path.exists():
        out["metadata"] = read_metadata(sp.metadata_path)
    for k in required:
        if k not in out:
            raise SweepIOError(f"Run {run_dir} missing required artifact: {k}")
    return out

def save_run(run_dir: Path, *, config: Mapping[str, Any], results: Iterable[Mapping[str, Any]], metadata: Mapping[str, Any]) -> SweepPaths:
    """Save config/results/metadata to the conventional files within *run_dir*."""
    sp = SweepPaths(Path(run_dir))
    sp.run_dir.mkdir(parents=True, exist_ok=True)
    write_config(sp.config_path, config)
    write_results_csv(sp.results_path, results)
    write_metadata(sp.metadata_path, metadata)
    return sp
