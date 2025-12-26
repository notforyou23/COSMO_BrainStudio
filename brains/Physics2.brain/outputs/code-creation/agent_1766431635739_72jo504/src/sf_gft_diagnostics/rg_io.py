"""rg_io.py: lightweight loaders/adapters for RG/coarse-graining outputs.

This module normalizes heterogeneous logs (tensor-network/lattice RG, or
GFT/spinfoam coarse-graining) into a simple in-memory dataset: a sequence of
"steps" with scale information, couplings/parameters, observables, and optional
distributional payloads.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union
import json


Json = Union[dict, list, str, int, float, bool, None]


@dataclass
class RGStep:
    """One RG/coarse-graining step."""
    index: int
    scale: Optional[float] = None          # e.g., lattice spacing, blocking factor, k
    level: Optional[int] = None            # e.g., iteration / coarse-graining level
    params: Dict[str, float] = field(default_factory=dict)
    observables: Dict[str, Any] = field(default_factory=dict)
    distributions: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RGDataset:
    """Normalized dataset holding a flow/trajectory."""
    name: str = "rg_dataset"
    kind: str = "auto"                     # 'tnrg', 'lattice_rg', 'gft', 'spinfoam', ...
    meta: Dict[str, Any] = field(default_factory=dict)
    steps: List[RGStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "meta": self.meta,
                "steps": [s.__dict__ for s in self.steps]}
def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _coerce_num_map(m: Mapping[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k, v in m.items():
        fv = _as_float(v)
        if fv is not None:
            out[str(k)] = fv
    return out


def _normalize_step(rec: Mapping[str, Any], idx: int) -> RGStep:
    # Accept a few common synonyms across ecosystems.
    scale = _as_float(rec.get("scale", rec.get("k", rec.get("a", rec.get("lambda")))))
    level = rec.get("level", rec.get("iter", rec.get("iteration", rec.get("n"))))
    try:
        level = int(level) if level is not None else None
    except Exception:
        level = None

    params_raw = rec.get("params", rec.get("couplings", rec.get("theta", {}))) or {}
    obs_raw = rec.get("observables", rec.get("obs", rec.get("measurements", {}))) or {}
    dist_raw = rec.get("distributions", rec.get("dists", rec.get("histograms", {}))) or {}

    meta = dict(rec.get("meta", {}))
    # Preserve unrecognized top-level keys without duplicating common fields.
    skip = {"scale","k","a","lambda","level","iter","iteration","n",
            "params","couplings","theta","observables","obs","measurements",
            "distributions","dists","histograms","meta"}
    for k, v in rec.items():
        if k not in skip:
            meta.setdefault(k, v)

    return RGStep(
        index=idx,
        scale=scale,
        level=level,
        params=_coerce_num_map(params_raw) if isinstance(params_raw, Mapping) else {},
        observables=dict(obs_raw) if isinstance(obs_raw, Mapping) else {"_value": obs_raw},
        distributions=dict(dist_raw) if isinstance(dist_raw, Mapping) else {"_value": dist_raw},
        meta=meta,
    )
def from_records(
    records: Sequence[Mapping[str, Any]],
    *,
    name: str = "rg_dataset",
    kind: str = "auto",
    meta: Optional[Mapping[str, Any]] = None,
) -> RGDataset:
    """Build a normalized dataset from a list of dict records."""
    ds = RGDataset(name=name, kind=kind, meta=dict(meta or {}))
    ds.steps = [_normalize_step(r, i) for i, r in enumerate(records)]
    return ds


def _load_json_any(path: Path) -> Json:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> List[dict]:
    out: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(json.loads(line))
    return out


def load_rg_dataset(
    path: Union[str, Path],
    *,
    kind: str = "auto",
    name: Optional[str] = None,
) -> RGDataset:
    """Load a dataset from .json or .jsonl (newline-delimited JSON).

    Accepted structures:
      - list[dict]: step records
      - dict with key 'steps'/'records'/'flow'/'trajectory': container
      - dict-of-dicts: keys sortable to steps (e.g., {0:{...},1:{...}})
    """
    p = Path(path)
    nm = name or p.stem

    if p.suffix.lower() in {".jsonl", ".ndjson"}:
        return from_records(_load_jsonl(p), name=nm, kind=kind, meta={"source": str(p)})

    obj = _load_json_any(p)
    if isinstance(obj, list):
        return from_records(obj, name=nm, kind=kind, meta={"source": str(p)})
    if not isinstance(obj, dict):
        raise TypeError(f"Unsupported JSON root type: {type(obj).__name__}")

    steps = None
    for key in ("steps", "records", "flow", "trajectory"):
        if key in obj:
            steps = obj[key]
            break

    if steps is None and all(isinstance(v, dict) for v in obj.values()):
        try:
            steps = [v for _, v in sorted(obj.items(), key=lambda kv: int(str(kv[0])))]
        except Exception:
            steps = list(obj.values())

    if not isinstance(steps, list):
        raise ValueError("Could not locate a list of step records in JSON.")

    meta = dict(obj.get("meta", {})) if isinstance(obj.get("meta", {}), dict) else {}
    meta.setdefault("source", str(p))
    meta.setdefault("container_keys", sorted(obj.keys()))
    return from_records(steps, name=nm, kind=kind, meta=meta)


def merge_datasets(*datasets: RGDataset, name: str = "merged") -> RGDataset:
    """Concatenate multiple datasets (useful for multi-run ensembles)."""
    meta = {"merged_from": [d.name for d in datasets]}
    steps: List[RGStep] = []
    for di, d in enumerate(datasets):
        for s in d.steps:
            s2 = RGStep(**s.__dict__)
            s2.meta = dict(s2.meta)
            s2.meta.setdefault("run_index", di)
            steps.append(s2)
    return RGDataset(name=name, kind="merged", meta=meta, steps=steps)
