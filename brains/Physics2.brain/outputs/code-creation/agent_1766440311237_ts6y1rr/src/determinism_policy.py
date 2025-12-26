"""Determinism policy utilities.

This module centralizes repeatability controls for benchmarks:
- Sets seeds for Python's `random` and NumPy (if installed).
- Normalizes common environment variables that influence determinism.

It is intentionally lightweight and dependency-free (NumPy optional).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import random
from typing import Any, Dict, Optional, Tuple
def _import_numpy():
    try:
        import numpy as np  # type: ignore
    except Exception:
        return None
    return np


def set_global_seed(seed: int) -> None:
    """Seed Python's RNGs (and NumPy if available)."""
    if not isinstance(seed, int):
        raise TypeError(f"seed must be int, got {type(seed)!r}")
    random.seed(seed)
    np = _import_numpy()
    if np is not None:
        np.random.seed(seed)
def normalized_env_defaults() -> Dict[str, str]:
    """Environment variables commonly set for deterministic execution."""
    return {
        # Hash randomization affects iteration order of sets/dicts in some cases.
        "PYTHONHASHSEED": "0",
        # Prefer stable UTF-8 behavior across systems.
        "PYTHONUTF8": "1",
        # Keep locale/timezone stable for any incidental formatting.
        "TZ": "UTC",
        "LC_ALL": "C",
        "LANG": "C",
        # Reduce non-determinism from threaded BLAS backends (best effort).
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        # GPU libraries (if present) can require additional controls.
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    }


def apply_environment(env: Optional[Dict[str, str]] = None) -> Dict[str, Optional[str]]:
    """Apply environment overrides and return previous values for restoration."""
    overrides = normalized_env_defaults()
    if env:
        overrides.update({k: str(v) for k, v in env.items()})
    previous: Dict[str, Optional[str]] = {}
    for k, v in overrides.items():
        previous[k] = os.environ.get(k)
        os.environ[k] = v
    # Ensure tz changes take effect where supported.
    if "TZ" in overrides:
        try:
            import time

            time.tzset()  # type: ignore[attr-defined]
        except Exception:
            pass
    return previous


def restore_environment(previous: Dict[str, Optional[str]]) -> None:
    """Restore environment variables captured from `apply_environment`."""
    for k, old in previous.items():
        if old is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = old
    if "TZ" in previous:
        try:
            import time

            time.tzset()  # type: ignore[attr-defined]
        except Exception:
            pass
@dataclass
class DeterminismPolicy:
    """A small policy object for reproducible benchmark runs.

    Typical use from a runner:

        with DeterminismPolicy(seed=123).activate():
            ... run benchmark ...

    It captures/restores RNG and environment state so callers can nest policies.
    """

    seed: Optional[int] = 0
    env: Dict[str, str] = field(default_factory=dict)
    _prev_env: Dict[str, Optional[str]] = field(init=False, default_factory=dict)
    _py_random_state: Any = field(init=False, default=None)
    _np_random_state: Any = field(init=False, default=None)
    _active: bool = field(init=False, default=False)

    def activate(self) -> "DeterminismPolicy":
        if self._active:
            return self
        self._py_random_state = random.getstate()
        np = _import_numpy()
        if np is not None:
            self._np_random_state = np.random.get_state()
        self._prev_env = apply_environment(self.env)
        if self.seed is not None:
            set_global_seed(int(self.seed))
        self._active = True
        return self

    def close(self) -> None:
        if not self._active:
            return
        restore_environment(self._prev_env)
        if self._py_random_state is not None:
            random.setstate(self._py_random_state)
        np = _import_numpy()
        if np is not None and self._np_random_state is not None:
            np.random.set_state(self._np_random_state)
        self._active = False

    def __enter__(self) -> "DeterminismPolicy":
        return self.activate()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
