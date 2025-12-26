"""Determinism utilities.

Provides a single place to configure deterministic behavior across common libs
and to serialize JSON in a stable way for reproducible artifact hashing.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
from typing import Any, Mapping, Optional, Tuple
def set_global_determinism(seed: int = 0, threads: int = 1) -> dict:
    """Set RNG seeds and environment flags for determinism.

    Returns a small report dict to record in results.json.
    """
    seed = int(seed)
    threads = int(threads) if threads is not None else 1

    _set_env_flags(seed=seed, threads=threads)
    report = {
        "seed": seed,
        "threads": threads,
        "python_random": _seed_python_random(seed),
        "numpy": _seed_numpy(seed),
        "torch": _seed_torch(seed),
        "tensorflow": _seed_tensorflow(seed),
    }
    return report
def _set_env_flags(seed: int, threads: int) -> None:
    # Must be set as early as possible in the process for full effect.
    os.environ.setdefault("PYTHONHASHSEED", str(seed))

    # Threading / BLAS determinism.
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ.setdefault(k, str(max(1, threads)))

    # CUDA / cuBLAS deterministic workspace (if CUDA is used).
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

    # TensorFlow determinism (only effective if TF is used and supports it).
    os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
    os.environ.setdefault("TF_CUDNN_DETERMINISTIC", "1")
def _seed_python_random(seed: int) -> dict:
    random.seed(seed)
    return {"available": True}
def _seed_numpy(seed: int) -> dict:
    try:
        import numpy as np  # type: ignore
    except Exception:
        return {"available": False}
    np.random.seed(seed)
    return {"available": True, "version": getattr(np, "__version__", None)}
def _seed_torch(seed: int) -> dict:
    try:
        import torch  # type: ignore
    except Exception:
        return {"available": False}

    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # Prefer determinism; if not supported by current ops, this may raise.
    try:
        torch.use_deterministic_algorithms(True)
        deterministic_algos = True
    except Exception:
        deterministic_algos = False

    try:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass

    return {
        "available": True,
        "version": getattr(torch, "__version__", None),
        "cuda_available": bool(torch.cuda.is_available()),
        "deterministic_algorithms": deterministic_algos,
    }
def _seed_tensorflow(seed: int) -> dict:
    try:
        import tensorflow as tf  # type: ignore
    except Exception:
        return {"available": False}
    try:
        tf.random.set_seed(seed)
    except Exception:
        pass
    return {"available": True, "version": getattr(tf, "__version__", None)}
def stable_json_dumps(obj: Any) -> str:
    """Stable JSON for hashing/version control (sorted keys, compact separators)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
def stable_json_dump(path, obj: Any) -> None:
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = stable_json_dumps(obj) + "\n"
    p.write_text(text, encoding="utf-8")
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
def sha256_file(path) -> str:
    from pathlib import Path
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
def snapshot_env(keys: Optional[Tuple[str, ...]] = None) -> Mapping[str, str]:
    """Capture a small set of determinism-relevant env vars for reporting."""
    if keys is None:
        keys = (
            "PYTHONHASHSEED",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "CUBLAS_WORKSPACE_CONFIG",
            "TF_DETERMINISTIC_OPS",
            "TF_CUDNN_DETERMINISTIC",
        )
    return {k: os.environ.get(k, "") for k in keys}
