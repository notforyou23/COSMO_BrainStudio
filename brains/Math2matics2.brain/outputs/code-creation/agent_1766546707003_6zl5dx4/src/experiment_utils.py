"""experiment_utils.py

Small helpers shared by toy experiments.

Goals:
- Deterministic seeding across common RNG libraries.
- Safe output directory creation.
- Stable, reproducible JSON artifact writing.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
import random
from typing import Any, Mapping, Optional
def seed_everything(seed: int) -> int:
    """Seed common PRNGs and return the normalized seed.

    This function tries to seed:
    - Python's `random`
    - NumPy (if available)
    - PyTorch (if available)

    It also sets PYTHONHASHSEED to make hashing deterministic in subprocesses.
    """
    if seed is None:
        raise TypeError("seed must be an int, not None")
    seed = int(seed) & 0xFFFFFFFF
    os.environ["PYTHONHASHSEED"] = str(seed)

    random.seed(seed)

    try:
        import numpy as np  # type: ignore

        np.random.seed(seed)
    except Exception:
        pass

    try:
        import torch  # type: ignore

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True  # type: ignore[attr-defined]
        torch.backends.cudnn.benchmark = False  # type: ignore[attr-defined]
    except Exception:
        pass

    return seed
def ensure_dir(path: str | Path) -> Path:
    """Create *path* as a directory (including parents) and return it."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
def _json_default(obj: Any) -> Any:
    """Best-effort JSON conversion for a few common numeric/container types."""
    try:
        import numpy as np  # type: ignore

        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
    except Exception:
        pass

    # Fallback: let json raise for unsupported types.
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
def write_json(
    path: str | Path,
    data: Mapping[str, Any],
    *,
    indent: int = 2,
    sort_keys: bool = True,
    newline: str = "\n",
) -> Path:
    """Write JSON deterministically and atomically.

    - Sorts keys by default.
    - Uses a stable indentation.
    - Writes to a temporary file then replaces to avoid partial artifacts.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    text = json.dumps(
        data,
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=False,
        default=_json_default,
    )
    if not text.endswith(newline):
        text += newline

    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(out_path)
    return out_path
def read_json(path: str | Path) -> Any:
    """Read JSON from *path* using UTF-8 encoding."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
