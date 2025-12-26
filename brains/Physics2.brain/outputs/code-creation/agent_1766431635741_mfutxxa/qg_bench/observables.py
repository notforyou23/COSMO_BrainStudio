"""Benchmark observables.

This module computes small, deterministic summary metrics from a list of
ingested per-example records (dicts). It is intentionally dependency-free
and tolerant to minor key-name variations in the input records.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
def _first_present(record: Dict[str, Any], keys: Sequence[str]) -> Tuple[bool, Any]:
    """Return (found, value) for the first key present in record."""
    for k in keys:
        if k in record:
            return True, record[k]
    return False, None
def _as_float(x: Any) -> Optional[float]:
    """Best-effort conversion to float; returns None on failure."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None
def accuracy(
    records: Iterable[Dict[str, Any]],
    *,
    prediction_keys: Sequence[str] = ("prediction", "pred", "y_pred"),
    label_keys: Sequence[str] = ("label", "gold", "y_true", "answer"),
) -> Dict[str, Any]:
    """Compute exact-match accuracy over records.

    A record is counted as scorable if both prediction and label are present.
    Values are compared after stringification to avoid type quirks.
    """
    n = 0
    n_correct = 0
    for r in records:
        has_p, p = _first_present(r, prediction_keys)
        has_y, y = _first_present(r, label_keys)
        if not (has_p and has_y):
            continue
        n += 1
        if str(p) == str(y):
            n_correct += 1

    value = (n_correct / n) if n else None
    return {
        "name": "accuracy",
        "value": None if value is None else round(float(value), 12),
        "n": n,
        "n_correct": n_correct,
    }
def mean_latency_ms(
    records: Iterable[Dict[str, Any]],
    *,
    latency_keys: Sequence[str] = ("latency_ms", "latency", "elapsed_ms", "duration_ms"),
) -> Dict[str, Any]:
    """Compute mean latency (milliseconds) over records.

    A record contributes if a latency field is present and parseable as float.
    """
    n = 0
    total = 0.0
    for r in records:
        has_l, l = _first_present(r, latency_keys)
        if not has_l:
            continue
        v = _as_float(l)
        if v is None:
            continue
        n += 1
        total += v

    value = (total / n) if n else None
    return {
        "name": "mean_latency_ms",
        "value": None if value is None else round(float(value), 12),
        "n": n,
    }
def compute_observables(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute the default observable set for the benchmark run.

    Returns a JSON-serializable dict intended to be embedded into the
    standardized results document.
    """
    acc = accuracy(records)
    lat = mean_latency_ms(records)
    return {
        "observables": {
            acc["name"]: acc,
            lat["name"]: lat,
        },
        "record_counts": {
            "total": len(records),
            "scorable": acc["n"],
            "with_latency": lat["n"],
        },
    }
