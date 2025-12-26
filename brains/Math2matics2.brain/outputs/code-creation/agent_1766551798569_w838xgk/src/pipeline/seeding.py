from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
@dataclass(frozen=True)
class SeedRecord:
    seed: int
    pythonhashseed: str
    numpy_seeded: bool
    torch_seeded: bool
    torch_deterministic: bool
    created_unix: float
def _normalize_seed(seed: Optional[int]) -> int:
    if seed is None:
        try:
            import secrets
            seed = secrets.randbits(32)
        except Exception:
            seed = int(time.time_ns() & 0xFFFFFFFF)
    try:
        seed_int = int(seed)
    except Exception as e:
        raise TypeError(f"seed must be int-like or None, got {type(seed)!r}") from e
    return seed_int % (2**32)
def seed_everything(
    seed: Optional[int] = None,
    *,
    set_hash_seed: bool = True,
    seed_numpy: bool = True,
    seed_torch: bool = True,
    deterministic_torch: bool = True,
) -> Dict[str, Any]:
    """Deterministically seed Python, NumPy, and (optionally) torch.

    Returns a JSON-serializable dict capturing the chosen seed and key settings.
    """
    s = _normalize_seed(seed)

    if set_hash_seed:
        os.environ["PYTHONHASHSEED"] = str(s)

    random.seed(s)

    numpy_seeded = False
    if seed_numpy:
        try:
            import numpy as np  # type: ignore
            np.random.seed(s)
            numpy_seeded = True
        except Exception:
            numpy_seeded = False

    torch_seeded = False
    torch_det = False
    if seed_torch:
        try:
            import torch  # type: ignore

            torch.manual_seed(s)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(s)

            torch_seeded = True
            torch_det = bool(deterministic_torch)

            if deterministic_torch:
                try:
                    torch.use_deterministic_algorithms(True)
                except Exception:
                    pass
                try:
                    import torch.backends.cudnn as cudnn  # type: ignore

                    cudnn.deterministic = True
                    cudnn.benchmark = False
                except Exception:
                    pass
        except Exception:
            torch_seeded = False
            torch_det = False

    rec = SeedRecord(
        seed=s,
        pythonhashseed=os.environ.get("PYTHONHASHSEED", ""),
        numpy_seeded=numpy_seeded,
        torch_seeded=torch_seeded,
        torch_deterministic=torch_det,
        created_unix=time.time(),
    )
    return asdict(rec)
__all__ = ["seed_everything", "SeedRecord"]
