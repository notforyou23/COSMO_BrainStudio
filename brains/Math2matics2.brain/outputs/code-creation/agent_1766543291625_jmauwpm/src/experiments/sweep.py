"""Parameter sweep utilities.

This module is dependency-light and focuses on:
- building cartesian grids from parameter spaces,
- running a user-provided experiment function over the grid,
- collecting structured results (including errors),
- persisting/reloading sweep manifests as JSON.

All functions are deterministic given deterministic inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha1
from itertools import product
from pathlib import Path
from time import time
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union
import json
Jsonable = Union[None, bool, int, float, str, List["Jsonable"], Dict[str, "Jsonable"]]


def _json_default(obj: Any) -> Jsonable:
    """Best-effort JSON fallback for common python objects."""
    if hasattr(obj, "__dict__"):
        return {k: _json_default(v) for k, v in vars(obj).items()}
    return str(obj)


def _stable_hash(data: Any) -> str:
    b = json.dumps(data, sort_keys=True, default=_json_default, separators=(",", ":")).encode("utf-8")
    return sha1(b).hexdigest()[:12]
def normalize_space(space: Mapping[str, Union[Sequence[Any], Any]]) -> Dict[str, List[Any]]:
    """Normalize a parameter space to dict[str, list]. Scalars become 1-length lists."""
    out: Dict[str, List[Any]] = {}
    for k, v in space.items():
        if isinstance(v, (str, bytes)) or not isinstance(v, Sequence):
            out[k] = [v]
        else:
            out[k] = list(v)
    return out


def iter_grid(space: Mapping[str, Union[Sequence[Any], Any]]) -> Iterator[Dict[str, Any]]:
    """Yield parameter dicts for the cartesian product of a parameter space."""
    sp = normalize_space(space)
    keys = sorted(sp.keys())
    for values in product(*(sp[k] for k in keys)):
        yield dict(zip(keys, values))
@dataclass(frozen=True)
class SweepItem:
    """A single sweep evaluation input."""

    params: Dict[str, Any]
    run_id: str

    @staticmethod
    def from_params(params: Mapping[str, Any], run_id: Optional[str] = None) -> "SweepItem":
        p = dict(params)
        rid = run_id or _stable_hash(p)
        return SweepItem(params=p, run_id=rid)


@dataclass
class SweepResult:
    """A single sweep evaluation output."""

    run_id: str
    params: Dict[str, Any]
    ok: bool
    result: Any = None
    error: Optional[str] = None
    started_s: float = 0.0
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # ensure result is jsonable-ish
        d["result"] = json.loads(json.dumps(d["result"], default=_json_default))
        return d
def build_sweep(space: Mapping[str, Union[Sequence[Any], Any]]) -> List[SweepItem]:
    """Create a concrete sweep list from a space."""
    return [SweepItem.from_params(p) for p in iter_grid(space)]


def run_sweep(
    items: Iterable[SweepItem],
    run_fn: Callable[[Mapping[str, Any]], Any],
) -> List[SweepResult]:
    """Run a sweep sequentially and return a list of SweepResult.

    run_fn(params) should return any json-serializable result (or convertible).
    Exceptions are caught and stored in the result.
    """
    out: List[SweepResult] = []
    for it in items:
        t0 = time()
        try:
            res = run_fn(it.params)
            out.append(SweepResult(run_id=it.run_id, params=it.params, ok=True, result=res, started_s=t0, duration_s=time() - t0))
        except Exception as e:  # pragma: no cover
            out.append(SweepResult(run_id=it.run_id, params=it.params, ok=False, error=f"{type(e).__name__}: {e}", started_s=t0, duration_s=time() - t0))
    return out
def manifest_dict(
    results: Sequence[SweepResult],
    space: Optional[Mapping[str, Union[Sequence[Any], Any]]] = None,
    meta: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a JSON-ready sweep manifest."""
    m: Dict[str, Any] = {
        "format": "experiments.sweep.v1",
        "created_s": time(),
        "n": len(results),
        "results": [r.to_dict() for r in results],
    }
    if space is not None:
        m["space"] = normalize_space(space)
    if meta:
        m["meta"] = json.loads(json.dumps(dict(meta), default=_json_default))
    # convenience: overall hash to detect changes
    m["sweep_id"] = _stable_hash({"space": m.get("space"), "meta": m.get("meta"), "results": [(r.run_id, r.ok) for r in results]})
    return m


def save_manifest(path: Union[str, Path], manifest: Mapping[str, Any]) -> Path:
    """Write a manifest as UTF-8 JSON (pretty, deterministic keys)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    return p


def load_manifest(path: Union[str, Path]) -> Dict[str, Any]:
    """Load a manifest written by save_manifest."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
def best_by(
    results: Sequence[SweepResult],
    key: Callable[[Any], float],
    maximize: bool = True,
) -> Optional[SweepResult]:
    """Pick the best successful result by key(result)."""
    ok = [r for r in results if r.ok]
    if not ok:
        return None
    return max(ok, key=lambda r: key(r.result)) if maximize else min(ok, key=lambda r: key(r.result))
