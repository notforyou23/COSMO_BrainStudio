"""Seed and determinism utilities.

This module centralizes seed handling for reproducible runs and for consistent
recording into artifact metadata (e.g., results.json).
"""

from __future__ import annotations

import os
import platform
import random
import secrets
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple
DEFAULT_SEED_ENV_VAR = "COSMO_SEED"


def _int_from_env(name: str) -> Optional[int]:
    v = os.environ.get(name)
    if v is None or v == "":
        return None
    try:
        return int(v, 10)
    except Exception:
        return None


def choose_seed(seed: Optional[int] = None, *, env_var: str = DEFAULT_SEED_ENV_VAR) -> Tuple[int, str]:
    """Return (seed, source). Source is one of: explicit|env|random."""
    if seed is not None:
        return int(seed), "explicit"
    env_seed = _int_from_env(env_var)
    if env_seed is not None:
        return int(env_seed), "env"
    # 32-bit seed for cross-lib compatibility
    return int(secrets.randbits(32)), "random"(
@dataclass(frozen=True)
class SeedMetadata:
    seed: int
    seed_source: str
    deterministic: bool
    pythonhashseed: Optional[str]
    libs: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _set_numpy_seed(seed: int) -> Dict[str, Any]:
    try:
        import numpy as np  # type: ignore
    except Exception:
        return {"available": False}
    try:
        np.random.seed(int(seed))
        return {"available": True, "version": getattr(np, "__version__", None)}
    except Exception as e:
        return {"available": True, "error": repr(e)}


def _set_torch_seed(seed: int, deterministic: bool) -> Dict[str, Any]:
    try:
        import torch  # type: ignore
    except Exception:
        return {"available": False}
    info: Dict[str, Any] = {"available": True, "version": getattr(torch, "__version__", None)}
    try:
        torch.manual_seed(int(seed))
        if getattr(torch, "cuda", None) is not None and torch.cuda.is_available():
            torch.cuda.manual_seed_all(int(seed))
            info["cuda_available"] = True
        else:
            info["cuda_available"] = False
    except Exception as e:
        info["error_seed"] = repr(e)

    if deterministic:
        try:
            if hasattr(torch, "use_deterministic_algorithms"):
                torch.use_deterministic_algorithms(True)
                info["use_deterministic_algorithms"] = True
        except Exception as e:
            info["error_deterministic_algorithms"] = repr(e)
        try:
            if hasattr(torch.backends, "cudnn"):
                torch.backends.cudnn.deterministic = True  # type: ignore[attr-defined]
                torch.backends.cudnn.benchmark = False  # type: ignore[attr-defined]
                info["cudnn_deterministic"] = True
        except Exception as e:
            info["error_cudnn"] = repr(e)
    return info
def set_global_seed(
    seed: int,
    *,
    deterministic: bool = False,
    set_pythonhashseed_env: bool = True,
) -> SeedMetadata:
    """Set seeds for common RNG providers and optionally enable deterministic modes.

    Notes:
      - Setting PYTHONHASHSEED at runtime may not affect the current process'
        hash randomization; it is recorded for replay and impacts child processes.
    """
    seed_i = int(seed)

    if set_pythonhashseed_env and "PYTHONHASHSEED" not in os.environ:
        os.environ["PYTHONHASHSEED"] = str(seed_i)

    random.seed(seed_i)

    libs: Dict[str, Any] = {}
    libs["python"] = {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
    }
    libs["numpy"] = _set_numpy_seed(seed_i)
    libs["torch"] = _set_torch_seed(seed_i, deterministic)

    return SeedMetadata(
        seed=seed_i,
        seed_source="unknown",
        deterministic=bool(deterministic),
        pythonhashseed=os.environ.get("PYTHONHASHSEED"),
        libs=libs,
    )


def resolve_and_set_seed(
    seed: Optional[int] = None,
    *,
    env_var: str = DEFAULT_SEED_ENV_VAR,
    deterministic: bool = False,
    set_pythonhashseed_env: bool = True,
) -> Tuple[int, Dict[str, Any]]:
    """Choose a seed, set global RNG state, and return (seed, metadata_dict)."""
    chosen, source = choose_seed(seed, env_var=env_var)
    md = set_global_seed(chosen, deterministic=deterministic, set_pythonhashseed_env=set_pythonhashseed_env)
    md_dict = md.to_dict()
    md_dict["seed_source"] = source
    return chosen, md_dict
