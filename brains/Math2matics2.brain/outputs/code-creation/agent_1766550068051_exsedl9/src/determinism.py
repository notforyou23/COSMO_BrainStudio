"""Determinism utilities: stable seeding, JSON writing, and PNG saving."""

from __future__ import annotations

import io
import json
import os
import random
import tempfile
from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any, Mapping, Optional


def set_determinism(seed: int = 0, threads: int = 1) -> None:
    """Best-effort deterministic configuration for common libs."""
    os.environ.setdefault("PYTHONHASHSEED", str(int(seed)))
    os.environ.setdefault("OMP_NUM_THREADS", str(int(threads)))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", str(int(threads)))
    os.environ.setdefault("MKL_NUM_THREADS", str(int(threads)))
    os.environ.setdefault("VECLIB_MAXIMUM_THREADS", str(int(threads)))
    os.environ.setdefault("NUMEXPR_NUM_THREADS", str(int(threads)))

    random.seed(int(seed))
    try:
        import numpy as np  # type: ignore

        np.random.seed(int(seed))
    except Exception:
        pass

    try:
        import matplotlib  # type: ignore

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt  # type: ignore

        plt.ioff()
        _apply_matplotlib_determinism()
    except Exception:
        pass


def _apply_matplotlib_determinism() -> None:
    import matplotlib as mpl  # type: ignore

    mpl.rcParams.update(
        {
            "figure.dpi": 100,
            "savefig.dpi": 100,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.1,
            "savefig.facecolor": "white",
            "savefig.edgecolor": "white",
            "font.family": "DejaVu Sans",
            "text.usetex": False,
            "axes.unicode_minus": False,
            "path.simplify": False,
            "agg.path.chunksize": 0,
        }
    )


def _to_builtin(obj: Any) -> Any:
    """Convert common non-JSON-native types into JSON-friendly values."""
    if is_dataclass(obj):
        return {k: _to_builtin(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return obj.hex()
    if isinstance(obj, Mapping):
        return {str(k): _to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_builtin(v) for v in obj]
    try:
        import numpy as np  # type: ignore

        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except Exception:
        pass
    return obj


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=str(path.parent), delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def stable_json_dumps(obj: Any) -> str:
    """Stable JSON serialization for byte-identical outputs."""
    built = _to_builtin(obj)
    text = json.dumps(
        built,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    return text + "\n"


def stable_write_json(path: Path, obj: Any) -> None:
    _atomic_write_bytes(Path(path), stable_json_dumps(obj).encode("utf-8"))


def stable_savefig_png(fig: Any, path: Path, dpi: int = 100) -> None:
    """Save a matplotlib figure as deterministic PNG bytes."""
    try:
        _apply_matplotlib_determinism()
    except Exception:
        pass

    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=int(dpi),
        facecolor="white",
        edgecolor="white",
        bbox_inches="tight",
        pad_inches=0.1,
        metadata={"Software": "matplotlib", "Creation Time": "0"},
    )
    _atomic_write_bytes(Path(path), buf.getvalue())


def stable_read_text(path: Path, encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)


def stable_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    if not text.endswith("\n"):
        text += "\n"
    _atomic_write_bytes(Path(path), text.encode(encoding))
