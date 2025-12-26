"""Shared utilities for the experiment suite.

This module is intentionally lightweight (std-lib + numpy) and provides:
- Deterministic RNG seeding across common libraries.
- Simple, reproducible result saving (JSON/NPZ) with atomic writes.
- Small table/markdown formatting helpers.
- Cached diagnostics (e.g., entropy/purity) keyed by array content.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union
import functools
import hashlib
import json
import math
import os
import random

import numpy as np
# -----------------------------
# RNG seeding
# -----------------------------

def seed_everything(seed: int) -> np.random.Generator:
    """Seed python/random + numpy and return a fresh default numpy Generator."""
    seed = int(seed)
    random.seed(seed)
    np.random.seed(seed)  # legacy global RNG (some libs still use it)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import torch  # type: ignore
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True  # type: ignore[attr-defined]
        torch.backends.cudnn.benchmark = False  # type: ignore[attr-defined]
    except Exception:
        pass
    return np.random.default_rng(seed)


def rng_from_seed(seed: Optional[int] = None) -> np.random.Generator:
    """Construct a numpy Generator (seed=None uses entropy)."""
    return np.random.default_rng(None if seed is None else int(seed))
# -----------------------------
# Result saving (atomic)
# -----------------------------

def ensure_dir(path: Union[str, Path]) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def save_json(path: Union[str, Path], obj: Any, *, indent: int = 2) -> Path:
    p = Path(path)
    data = json.dumps(obj, indent=indent, sort_keys=True, default=_json_default).encode("utf-8")
    _atomic_write_bytes(p, data)
    return p


def save_npz(path: Union[str, Path], **arrays: np.ndarray) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    np.savez_compressed(tmp, **arrays)
    os.replace(tmp, p)
    return p


def _json_default(x: Any) -> Any:
    if isinstance(x, (np.integer, np.int64)):
        return int(x)
    if isinstance(x, (np.floating, np.float64)):
        return float(x)
    if isinstance(x, np.ndarray):
        return {"__ndarray__": True, "shape": list(x.shape), "dtype": str(x.dtype)}
    if hasattr(x, "__dict__"):
        return x.__dict__
    return str(x)


@dataclass(frozen=True)
class RunPaths:
    root: Path
    out_dir: Path
    cache_dir: Path


def make_run_paths(root: Union[str, Path], experiment: str) -> RunPaths:
    root = Path(root)
    out_dir = ensure_dir(root / "results" / experiment)
    cache_dir = ensure_dir(root / ".cache" / experiment)
    return RunPaths(root=root, out_dir=out_dir, cache_dir=cache_dir)
# -----------------------------
# Table formatting
# -----------------------------

def format_table(rows: Sequence[Mapping[str, Any]], columns: Optional[Sequence[str]] = None, *,
                 floatfmt: str = ".6g") -> str:
    """Return a GitHub-flavored markdown table from a list of dict-like rows."""
    if not rows:
        return ""
    cols = list(columns) if columns is not None else sorted({k for r in rows for k in r.keys()})
    def fmt(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, (float, np.floating)):
            return format(float(v), floatfmt)
        return str(v)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = ["| " + " | ".join(fmt(r.get(c, "")) for c in cols) + " |" for r in rows]
    return "\n".join([header, sep] + body)
# -----------------------------
# Cached diagnostics
# -----------------------------

def _arr_key(a: np.ndarray, *, digest_size: int = 16) -> Tuple[str, Tuple[int, ...], str]:
    a = np.ascontiguousarray(a)
    h = hashlib.blake2b(a.view(np.uint8), digest_size=digest_size).hexdigest()
    return h, tuple(a.shape), str(a.dtype)


@functools.lru_cache(maxsize=2048)
def _cached_entropy_from_key(key: Tuple[str, Tuple[int, ...], str], log_base: float) -> float:
    # Key-only cache; the actual array content is incorporated via the hash.
    # Callers should compute the entropy and then store it via this shim.
    raise RuntimeError("internal cache shim must not be called directly")


def _cache_set(key: Tuple[str, Tuple[int, ...], str], log_base: float, value: float) -> float:
    # Abuse lru_cache by memoizing a closure-free function; we store via __wrapped__.
    try:
        _cached_entropy_from_key.cache_clear  # type: ignore[attr-defined]
    except Exception:
        pass
    # Implement our own tiny dict on the function object to avoid fragile lru_cache hacks.
    store: Dict[Tuple[Tuple[str, Tuple[int, ...], str], float], float] = getattr(_cache_set, "_store", {})
    store[(key, log_base)] = float(value)
    setattr(_cache_set, "_store", store)
    return float(value)


def _cache_get(key: Tuple[str, Tuple[int, ...], str], log_base: float) -> Optional[float]:
    store: Dict[Tuple[Tuple[str, Tuple[int, ...], str], float], float] = getattr(_cache_set, "_store", {})
    return store.get((key, log_base))


def spectral_entropy(p: np.ndarray, *, base: float = 2.0, eps: float = 1e-15) -> float:
    """Shannon entropy of a probability vector (normalized if needed)."""
    p = np.asarray(p, dtype=float).ravel()
    s = float(p.sum())
    if s <= 0:
        return 0.0
    p = p / s
    p = np.clip(p, eps, 1.0)
    return float(-(p * (np.log(p) / math.log(base))).sum())


def von_neumann_entropy(rho: np.ndarray, *, base: float = 2.0, eps: float = 1e-15) -> float:
    """Von Neumann entropy S(ρ) = -Tr ρ log ρ for a density matrix."""
    rho = np.asarray(rho)
    key = _arr_key(rho)
    cached = _cache_get(key, base)
    if cached is not None:
        return cached
    # Hermitize for numerical stability.
    r = (rho + rho.conj().T) / 2.0
    evals = np.linalg.eigvalsh(r)
    evals = np.clip(np.real(evals), 0.0, 1.0)
    val = spectral_entropy(evals, base=base, eps=eps)
    return _cache_set(key, base, val)


def purity(rho: np.ndarray) -> float:
    """Purity Tr(ρ²)."""
    r = np.asarray(rho)
    return float(np.real(np.trace(r @ r)))


def participation_ratio(vec: np.ndarray, *, eps: float = 1e-15) -> float:
    """Effective number of components: 1 / sum |v_i|^4 for normalized vectors."""
    v = np.asarray(vec).ravel()
    nrm = np.linalg.norm(v)
    if nrm <= eps:
        return 0.0
    v = v / nrm
    return float(1.0 / np.sum(np.abs(v) ** 4))
