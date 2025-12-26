"""Unified RNG seed control for reproducible pipelines.

This module sets and propagates a single seed across Python stdlib RNG,
NumPy, and common ML libraries when available. It returns a SeedContext
for downstream use (e.g., passing a JAX key).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
import os
import random
def _seed_to_int(seed: Optional[int]) -> int:
    if seed is None:
        seed = int.from_bytes(os.urandom(8), "little", signed=False)
    if not isinstance(seed, int):
        raise TypeError(f"seed must be int or None, got {type(seed)!r}")
    return seed & 0x7FFFFFFF


def _try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None


def _record(status: Dict[str, Any], lib: str, ok: bool, detail: str = "") -> None:
    status[lib] = {"ok": bool(ok), "detail": detail}
@dataclass(frozen=True)
class SeedContext:
    """Context describing applied seeding and carrying downstream RNG objects."""

    seed: int
    status: Dict[str, Any] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {"seed": self.seed, "status": self.status, "extras": self.extras}
def set_global_seed(seed: Optional[int], deterministic: bool = True) -> SeedContext:
    """Set a single seed across available RNG sources and return a context.

    Args:
        seed: Integer seed, or None to generate one.
        deterministic: Best-effort deterministic settings for some libraries.

    Returns:
        SeedContext with the resolved seed, per-library status, and extras.
    """
    s = _seed_to_int(seed)
    status: Dict[str, Any] = {}
    extras: Dict[str, Any] = {}

    os.environ.setdefault("PYTHONHASHSEED", str(s))
    if deterministic:
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")

    random.seed(s)
    _record(status, "python_random", True, "random.seed set")

    np = _try_import("numpy")
    if np is not None:
        try:
            np.random.seed(s)
            _record(status, "numpy", True, "np.random.seed set")
        except Exception as e:
            _record(status, "numpy", False, repr(e))
    else:
        _record(status, "numpy", False, "not installed")

    torch = _try_import("torch")
    if torch is not None:
        try:
            torch.manual_seed(s)
            if getattr(torch, "cuda", None) is not None:
                try:
                    torch.cuda.manual_seed_all(s)
                except Exception:
                    pass
            if deterministic:
                try:
                    torch.use_deterministic_algorithms(True)
                except Exception:
                    pass
                try:
                    torch.backends.cudnn.deterministic = True
                    torch.backends.cudnn.benchmark = False
                except Exception:
                    pass
            _record(status, "torch", True, "manual_seed set")
        except Exception as e:
            _record(status, "torch", False, repr(e))
    else:
        _record(status, "torch", False, "not installed")

    tf = _try_import("tensorflow")
    if tf is not None:
        try:
            tf.random.set_seed(s)
            _record(status, "tensorflow", True, "tf.random.set_seed set")
        except Exception as e:
            _record(status, "tensorflow", False, repr(e))
    else:
        _record(status, "tensorflow", False, "not installed")

    jax = _try_import("jax")
    if jax is not None:
        try:
            # JAX has no global seed; provide a key for downstream use.
            key = jax.random.PRNGKey(s)
            extras["jax_key"] = key
            _record(status, "jax", True, "provided PRNGKey(seed)")
        except Exception as e:
            _record(status, "jax", False, repr(e))
    else:
        _record(status, "jax", False, "not installed")

    mpl = _try_import("matplotlib")
    if mpl is not None:
        try:
            # Matplotlib itself doesn't have an RNG; keep a stable hashsalt if present.
            try:
                import matplotlib as _mpl
                if hasattr(_mpl, "rcParams"):
                    _mpl.rcParams["svg.hashsalt"] = str(s)
            except Exception:
                pass
            _record(status, "matplotlib", True, "best-effort rcParams applied")
        except Exception as e:
            _record(status, "matplotlib", False, repr(e))
    else:
        _record(status, "matplotlib", False, "not installed")

    return SeedContext(seed=s, status=status, extras=extras)
from contextlib import contextmanager


@contextmanager
def seed_context(seed: Optional[int], deterministic: bool = True):
    """Context manager to apply global seeding once and yield a SeedContext."""
    ctx = set_global_seed(seed=seed, deterministic=deterministic)
    yield ctx
