"""Parameter sweep harness.

Provides grid and Latin hypercube sweeps with deterministic seeding and
tidy tabular aggregation (list-of-dicts) plus CSV I/O helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import csv
import numpy as np
Row = Dict[str, Any]
Params = Dict[str, Any]
RunFn = Callable[[Params], Mapping[str, Any]]


def _stable_items(d: Mapping[str, Any]) -> List[Tuple[str, Any]]:
    return sorted(d.items(), key=lambda kv: kv[0])


def grid_points(param_grid: Mapping[str, Sequence[Any]]) -> List[Params]:
    """Cartesian product of parameter values.

    Returns a list of dicts with stable key order (sorted keys).
    """
    keys = [k for k, _ in _stable_items(param_grid)]
    values = [list(param_grid[k]) for k in keys]
    return [dict(zip(keys, vals)) for vals in product(*values)]


def latin_hypercube_points(
    bounds: Mapping[str, Tuple[float, float]],
    n: int,
    *,
    seed: Optional[int] = None,
) -> List[Params]:
    """Latin hypercube sample in [low, high] per parameter.

    Uses one RNG stream and permutes bins per dimension for LHS structure.
    """
    if n <= 0:
        return []
    rng = np.random.default_rng(seed)
    keys = [k for k, _ in _stable_items(bounds)]
    u = (np.arange(n) + rng.random(n)) / n  # stratified in [0,1)
    pts: List[Params] = [dict() for _ in range(n)]
    for k in keys:
        lo, hi = bounds[k]
        perm = rng.permutation(n)
        x = lo + (hi - lo) * u[perm]
        for i in range(n):
            pts[i][k] = float(x[i])
    return pts
@dataclass(frozen=True)
class SweepSpec:
    """Defines either a grid or Latin hypercube sweep."""

    kind: str  # "grid" or "latin"
    grid: Optional[Mapping[str, Sequence[Any]]] = None
    bounds: Optional[Mapping[str, Tuple[float, float]]] = None
    n: int = 0
    seed: Optional[int] = None

    def points(self) -> List[Params]:
        if self.kind == "grid":
            if self.grid is None:
                raise ValueError("grid sweep requires 'grid'")
            return grid_points(self.grid)
        if self.kind == "latin":
            if self.bounds is None:
                raise ValueError("latin sweep requires 'bounds'")
            return latin_hypercube_points(self.bounds, self.n, seed=self.seed)
        raise ValueError(f"unknown sweep kind: {self.kind!r}")
def run_sweep(
    run_fn: RunFn,
    points: Sequence[Params],
    *,
    seed: Optional[int] = None,
    include_index: bool = True,
    seed_key: str = "run_seed",
) -> List[Row]:
    """Execute run_fn across points and aggregate into tidy rows.

    Determinism: if seed is provided, each run receives a derived integer seed
    under `seed_key` and the master RNG is not otherwise used.
    """
    rows: List[Row] = []
    ss = np.random.SeedSequence(seed) if seed is not None else None
    child_seeds = ss.spawn(len(points)) if ss is not None else [None] * len(points)
    for i, (p, cs) in enumerate(zip(points, child_seeds)):
        params: Params = dict(p)
        if cs is not None:
            params[seed_key] = int(np.random.default_rng(cs).integers(0, 2**32 - 1))
        out = dict(run_fn(params))
        row: Row = {}
        if include_index:
            row["run"] = i
        row.update(params)
        row.update(out)
        rows.append(row)
    return rows


def sweep(
    run_fn: RunFn,
    spec: SweepSpec,
    *,
    master_seed: Optional[int] = None,
    include_index: bool = True,
) -> List[Row]:
    """Convenience wrapper: generate points from spec and execute."""
    pts = spec.points()
    return run_sweep(run_fn, pts, seed=master_seed, include_index=include_index)
def save_csv(rows: Sequence[Mapping[str, Any]], path: str) -> None:
    """Save tidy rows to CSV (union of keys across rows)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    keys: List[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})


def load_csv(path: str) -> List[Row]:
    """Load CSV produced by save_csv."""
    with Path(path).open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]
