"""I/O utilities for reproducible toy experiments.

Provides:
- Deterministic seeding across Python / NumPy (if available).
- Output directory management with stable run identifiers.
- Structured result saving to JSON/CSV with atomic writes.

These helpers are intentionally lightweight and dependency-minimal.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
import csv
import hashlib
import json
import os
import random
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union


PathLike = Union[str, os.PathLike, Path]
def _try_import_numpy():
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    return np


def set_global_seed(seed: int) -> int:
    """Seed Python's RNG and NumPy's RNG (if installed). Returns the seed."""
    seed = int(seed)
    random.seed(seed)
    np = _try_import_numpy()
    if np is not None:
        np.random.seed(seed)
    return seed


def stable_hash(text: str, n: int = 10) -> str:
    """Short stable hex digest (useful for directory names)."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return h[: max(1, int(n))]
def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def make_run_dir(
    base_dir: PathLike,
    experiment: str,
    seed: int,
    tag: Optional[str] = None,
) -> Path:
    """Create a deterministic output directory for an experiment run.

    Directory name is stable given (experiment, seed, tag) to support
    reproducible reruns without timestamps.
    """
    base = ensure_dir(base_dir)
    key = f"{experiment}|{int(seed)}|{tag or ''}"
    run_id = stable_hash(key, n=12)
    name = f"{experiment}_seed{int(seed)}_{run_id}"
    if tag:
        name = f"{name}_{tag}"
    out = base / name
    out.mkdir(parents=True, exist_ok=True)
    return out
def _json_default(o: Any) -> Any:
    # dataclasses
    if is_dataclass(o):
        return asdict(o)
    # pathlib
    if isinstance(o, Path):
        return str(o)
    # numpy scalars/arrays (if present)
    np = _try_import_numpy()
    if np is not None:
        if isinstance(o, (np.integer, np.floating)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
    # sets/tuples
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")
def write_json(
    path: PathLike,
    obj: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
) -> Path:
    """Write JSON with an atomic replace to avoid partial files."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, sort_keys=sort_keys, default=_json_default)
        f.write("\n")
    tmp.replace(p)
    return p


def read_json(path: PathLike) -> Any:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
def write_csv(
    path: PathLike,
    rows: Iterable[Mapping[str, Any]],
    *,
    fieldnames: Optional[Sequence[str]] = None,
) -> Path:
    """Write a CSV file deterministically (stable column order).

    If fieldnames is None, uses sorted keys from the first row.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if not rows:
        raise ValueError("write_csv requires at least one row")
    if fieldnames is None:
        fieldnames = sorted(rows[0].keys())
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    tmp.replace(p)
    return p
def save_run_metadata(
    out_dir: PathLike,
    *,
    experiment: str,
    seed: int,
    params: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
    filename: str = "run_metadata.json",
) -> Path:
    """Save standard metadata for a run in a single JSON file."""
    payload: Dict[str, Any] = {
        "experiment": experiment,
        "seed": int(seed),
        "params": params or {},
    }
    if extra:
        payload.update(extra)
    return write_json(Path(out_dir) / filename, payload)
