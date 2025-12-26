"""Seed and reproducibility utilities.

This module centralizes seed handling across common ML/science stacks and
provides metadata helpers for recording determinism/replay info in artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import os
import random
import secrets
from typing import Any, Dict, Optional, Tuple
def _try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None


def normalize_seed(seed: Optional[Any] = None, *, env_keys: Tuple[str, ...] = ("COSMO_SEED", "SEED")) -> int:
    """Return a stable int seed in [0, 2**32-1].

    If seed is None, checks environment variables in env_keys; if still unset,
    generates a cryptographically-random 32-bit seed.
    """
    if seed is None:
        for k in env_keys:
            v = os.environ.get(k)
            if v not in (None, ""):
                seed = v
                break
    if seed is None:
        return secrets.randbits(32)
    if isinstance(seed, bool):
        seed = int(seed)
    if isinstance(seed, (int,)):
        n = int(seed)
    elif isinstance(seed, (bytes, bytearray)):
        n = int.from_bytes(seed, "big", signed=False)
    else:
        s = str(seed).strip()
        if s.lower().startswith("0x"):
            n = int(s, 16)
        else:
            n = int(s)
    return n % (2**32)


def set_python_seed(seed: int) -> None:
    random.seed(int(seed))


def set_numpy_seed(seed: int) -> bool:
    np = _try_import("numpy")
    if np is None:
        return False
    try:
        np.random.seed(int(seed))
        return True
    except Exception:
        return False


def set_torch_seed(seed: int, *, deterministic: bool = True) -> bool:
    torch = _try_import("torch")
    if torch is None:
        return False
    try:
        torch.manual_seed(int(seed))
        if getattr(torch, "cuda", None) is not None and torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(seed))
        if deterministic:
            try:
                torch.use_deterministic_algorithms(True)
            except Exception:
                pass
            try:
                if getattr(torch, "backends", None) is not None:
                    torch.backends.cudnn.deterministic = True
                    torch.backends.cudnn.benchmark = False
            except Exception:
                pass
        return True
    except Exception:
        return False
@dataclass(frozen=True)
class SeedReport:
    seed: int
    python: bool
    numpy: bool
    torch: bool
    torch_deterministic: bool
    env_seed_key: Optional[str] = None
    env_seed_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def apply_global_seed(
    seed: Optional[Any] = None,
    *,
    deterministic_torch: bool = True,
    set_python_hash_seed: bool = False,
) -> SeedReport:
    """Normalize and apply seed across libraries; returns a report.

    Note: PYTHONHASHSEED must be set before interpreter start to fully take
    effect; optionally set env var for subprocesses via set_python_hash_seed.
    """
    env_seed_key = None
    env_seed_value = None
    if seed is None:
        for k in ("COSMO_SEED", "SEED"):
            v = os.environ.get(k)
            if v not in (None, ""):
                env_seed_key, env_seed_value = k, v
                break
    s = normalize_seed(seed)
    if set_python_hash_seed:
        os.environ["PYTHONHASHSEED"] = str(s)
    set_python_seed(s)
    np_ok = set_numpy_seed(s)
    torch_ok = set_torch_seed(s, deterministic=deterministic_torch)
    return SeedReport(
        seed=int(s),
        python=True,
        numpy=bool(np_ok),
        torch=bool(torch_ok),
        torch_deterministic=bool(deterministic_torch and torch_ok),
        env_seed_key=env_seed_key,
        env_seed_value=env_seed_value,
    )


def seed_metadata(report: SeedReport, *, include_env: bool = True) -> Dict[str, Any]:
    """Metadata dict suitable for embedding in results.json."""
    d: Dict[str, Any] = {
        "seed": int(report.seed),
        "seed_applied": {
            "python_random": bool(report.python),
            "numpy": bool(report.numpy),
            "torch": bool(report.torch),
            "torch_deterministic": bool(report.torch_deterministic),
        },
    }
    if include_env:
        d["seed_source_env"] = {
            "key": report.env_seed_key,
            "value": report.env_seed_value,
        }
    return d
