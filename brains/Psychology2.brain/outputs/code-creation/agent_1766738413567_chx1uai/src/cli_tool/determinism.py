"""Determinism utilities for reproducible runs.

This module centralizes deterministic preflight checks: config canonicalization,
stable hashing, environment normalization, seeding, and invariant validation.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence, Tuple
@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    config_hash: str
    normalized_env: dict
    normalized_config: Any
    invariants: dict
    timestamp_utc: str


_DETERMINISM_ENV_KEYS: Tuple[str, ...] = (
    "TZ",
    "LANG",
    "LC_ALL",
    "PYTHONHASHSEED",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "CUBLAS_WORKSPACE_CONFIG",
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def canonicalize(obj: Any) -> Any:
    """Recursively convert objects into a stable, JSON-serializable form."""
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            raise ValueError("Non-finite float values are not allowed in deterministic configs.")
        return obj
    if isinstance(obj, (Path,)):
        return str(obj)
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return {"__bytes__": hashlib.sha256(bytes(obj)).hexdigest(), "len": len(obj)}
    if isinstance(obj, Mapping):
        items = []
        for k, v in obj.items():
            if not isinstance(k, str):
                k = str(k)
            items.append((k, canonicalize(v)))
        items.sort(key=lambda kv: kv[0])
        return {k: v for k, v in items}
    if isinstance(obj, (list, tuple)):
        return [canonicalize(v) for v in obj]
    if isinstance(obj, set):
        return sorted(canonicalize(v) for v in obj)
    if hasattr(obj, "__dict__"):
        return {"__type__": f"{obj.__class__.__module__}.{obj.__class__.__name__}", "value": canonicalize(vars(obj))}
    return str(obj)


def canonical_json(obj: Any) -> str:
    """Stable JSON encoding (sorted keys, compact separators)."""
    norm = canonicalize(obj)
    return json.dumps(norm, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
def stable_hash(obj: Any, *, prefix: str = "sha256:") -> str:
    data = canonical_json(obj).encode("utf-8")
    return prefix + hashlib.sha256(data).hexdigest()


def normalize_environment(env: Optional[Mapping[str, str]] = None) -> dict:
    """Return a stable subset of environment and runtime identifiers."""
    env = dict(os.environ if env is None else env)
    subset = {k: env.get(k) for k in _DETERMINISM_ENV_KEYS if k in env}
    subset["python"] = {
        "executable": sys.executable,
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
    }
    subset["platform"] = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }
    return canonicalize(subset)  # type: ignore[return-value]
def seed_everything(seed: int) -> dict:
    """Seed stdlib RNGs; return a seed report (numpy optional)."""
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative int")
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    report: dict = {"seed": seed, "pythonhashseed": os.environ.get("PYTHONHASHSEED")}
    try:
        import numpy as np  # type: ignore

        np.random.seed(seed)
        report["numpy"] = {"available": True, "version": getattr(np, "__version__", None)}
    except Exception:
        report["numpy"] = {"available": False}
    return report


def validate_invariants(
    normalized_config: Any,
    *,
    risk_threshold: Optional[float] = None,
    claim_decomposition: Optional[bool] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> dict:
    inv: dict = {}
    if risk_threshold is not None:
        if not (0.0 <= float(risk_threshold) <= 1.0):
            raise ValueError("risk_threshold must be within [0.0, 1.0]")
        inv["risk_threshold"] = float(risk_threshold)
    if claim_decomposition is not None:
        if not isinstance(claim_decomposition, bool):
            raise ValueError("claim_decomposition must be a bool")
        inv["claim_decomposition"] = claim_decomposition
    if extra:
        inv["extra"] = canonicalize(dict(extra))
    inv["config_json_len"] = len(canonical_json(normalized_config))
    return inv
def preflight(
    config: Any,
    *,
    seed: int = 0,
    env: Optional[Mapping[str, str]] = None,
    risk_threshold: Optional[float] = None,
    claim_decomposition: Optional[bool] = None,
    extra_invariants: Optional[Mapping[str, Any]] = None,
    set_thread_env: bool = True,
) -> PreflightResult:
    """Run deterministic preflight: canonicalize, seed, normalize env, validate invariants."""
    if set_thread_env:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
    os.environ.setdefault("TZ", "UTC")
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

    seed_report = seed_everything(seed)
    normalized_config = canonicalize(config)
    config_hash = stable_hash(normalized_config)
    normalized_env = normalize_environment(env)
    invariants = validate_invariants(
        normalized_config,
        risk_threshold=risk_threshold,
        claim_decomposition=claim_decomposition,
        extra={**seed_report, **(dict(extra_invariants) if extra_invariants else {})},
    )
    return PreflightResult(
        ok=True,
        config_hash=config_hash,
        normalized_env=normalized_env,
        normalized_config=normalized_config,
        invariants=invariants,
        timestamp_utc=_utcnow_iso(),
    )
