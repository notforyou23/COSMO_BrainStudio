"""Shared helpers for symbolic renormalization-group (RG) toy experiments.

The benchmark includes small "symbolic RG" experiment modules that should remain
dependency-free and deterministic. This module centralizes common parsing,
validation, and numeric housekeeping to keep those modules small and to avoid
import-time errors (e.g., missing `re` imports).
"""

from __future__ import annotations

import math
import re
from typing import Dict, Iterable, Mapping, MutableMapping, Tuple
# Accept monomials of the form "phi^4", "x_1^2", etc.
_MONOMIAL_RE = re.compile(r"^(?P<field>[A-Za-z_][A-Za-z0-9_]*)\^(?P<power>[0-9]+)$")


def parse_monomial(name: str) -> Tuple[str, int]:
    """Parse a monomial key like ``'phi^4'`` into ``('phi', 4)``.

    Raises:
        ValueError: if the name is not of the expected form.
    """
    m = _MONOMIAL_RE.match(name)
    if not m:
        raise ValueError(f"Invalid monomial: {name!r} (expected like 'phi^4')")
    return m.group("field"), int(m.group("power"))
def validate_couplings(couplings: Mapping[str, float]) -> None:
    """Validate that couplings are a mapping of monomial -> finite number."""
    if couplings is None:
        raise ValueError("couplings must not be None")
    if not isinstance(couplings, Mapping):
        raise TypeError(f"couplings must be a mapping, got {type(couplings).__name__}")
    for k, v in couplings.items():
        parse_monomial(str(k))
        if not isinstance(v, (int, float)):
            raise TypeError(f"Coupling {k!r} must be numeric, got {type(v).__name__}")
        if not math.isfinite(float(v)):
            raise ValueError(f"Coupling {k!r} must be finite, got {v!r}")
def sorted_couplings(couplings: Mapping[str, float]) -> Dict[str, float]:
    """Return a plain dict with string keys and float values, sorted by key."""
    return dict(sorted(((str(k), float(v)) for k, v in couplings.items()), key=lambda kv: kv[0]))


def drop_near_zero(couplings: Mapping[str, float], *, eps: float = 1e-15) -> Dict[str, float]:
    """Drop coefficients with absolute value <= eps (useful for stable JSON)."""
    out = {str(k): float(v) for k, v in couplings.items() if abs(float(v)) > eps}
    return dict(sorted(out.items()))
def accumulate(dst: MutableMapping[str, float], src: Mapping[str, float]) -> None:
    """In-place add coefficients from *src* into *dst* (both monomial-keyed)."""
    for k, v in src.items():
        dst[str(k)] = float(dst.get(str(k), 0.0)) + float(v)


def union_keys(*maps: Mapping[str, float]) -> Iterable[str]:
    """Return sorted union of keys across maps (deterministic)."""
    keys = set()
    for m in maps:
        keys.update(map(str, m.keys()))
    return sorted(keys)
__all__ = [
    "parse_monomial",
    "validate_couplings",
    "sorted_couplings",
    "drop_near_zero",
    "accumulate",
    "union_keys",
]
