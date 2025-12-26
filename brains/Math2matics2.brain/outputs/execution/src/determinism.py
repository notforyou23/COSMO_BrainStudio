from __future__ import annotations
import hashlib
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Union

import numpy as np
PathLike = Union[str, os.PathLike, Path]


def _maybe_import_torch():
    try:
        import torch  # type: ignore
        return torch
    except Exception:
        return None
@dataclass(frozen=True)
class DeterminismReport:
    seed: int
    torch_available: bool
    torch_deterministic: bool
    env: Dict[str, str]
def set_global_seed(
    seed: int,
    *,
    deterministic_torch: bool = True,
    set_pythonhashseed: bool = True,
) -> DeterminismReport:
    """Set RNG seeds across random/numpy/(optional) torch and enforce deterministic settings.

    Returns a report capturing environment settings relevant for determinism.
    """
    seed = int(seed)

    env_updates: Dict[str, str] = {}
    if set_pythonhashseed:
        os.environ["PYTHONHASHSEED"] = str(seed)
        env_updates["PYTHONHASHSEED"] = str(seed)

    # Recommended for deterministic CUDA GEMMs; harmless if CUDA absent.
    if deterministic_torch:
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        env_updates["CUBLAS_WORKSPACE_CONFIG"] = os.environ["CUBLAS_WORKSPACE_CONFIG"]

    random.seed(seed)
    np.random.seed(seed)

    torch = _maybe_import_torch()
    torch_available = torch is not None
    torch_did_deterministic = False

    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

        if deterministic_torch:
            # cuDNN + algorithm selection
            try:
                torch.backends.cudnn.deterministic = True
                torch.backends.cudnn.benchmark = False
            except Exception:
                pass
            try:
                torch.use_deterministic_algorithms(True)
            except Exception:
                pass
            torch_did_deterministic = True

    return DeterminismReport(
        seed=seed,
        torch_available=torch_available,
        torch_deterministic=torch_did_deterministic,
        env=dict(env_updates),
    )
def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: PathLike, *, chunk_size: int = 1024 * 1024) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()
def hash_artifacts(
    paths: Iterable[PathLike],
    *,
    base_dir: Optional[PathLike] = None,
) -> Dict[str, str]:
    """Compute SHA256 for each artifact path; keys are stable relative paths if base_dir given."""
    base = Path(base_dir).resolve() if base_dir is not None else None
    out: Dict[str, str] = {}
    for p in paths:
        pp = Path(p)
        key = str(pp)
        if base is not None:
            try:
                key = str(pp.resolve().relative_to(base))
            except Exception:
                key = str(pp)
        out[key] = sha256_file(pp)
    return out
