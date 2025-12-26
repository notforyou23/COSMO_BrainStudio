from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Union


JsonLike = Union[Dict[str, Any], Sequence[Any], str, int, float, bool, None]
def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str, encoding: str = "utf-8") -> str:
    return sha256_bytes(text.encode(encoding))


def sha256_json(obj: Any) -> str:
    return sha256_text(stable_json_dumps(obj))


def sha256_file(path: Union[str, Path], chunk_size: int = 1024 * 1024) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()
def init_seeds(seed: int = 0) -> Dict[str, Any]:
    seed = int(seed)
    random.seed(seed)
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    out: Dict[str, Any] = {"seed": seed, "numpy_seeded": False}
    try:
        import numpy as np  # type: ignore

        np.random.seed(seed)
        out["numpy_seeded"] = True
    except Exception:
        pass
    return out
def capture_environment(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    env_keys = ("PYTHONHASHSEED", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "executable": sys.executable,
        "cwd": str(Path.cwd()),
        "argv": list(sys.argv),
        "env": {k: os.environ.get(k) for k in env_keys if os.environ.get(k) is not None},
        "extra": dict(extra or {}),
    }
def ensure_dir(path: Union[str, Path]) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def atomic_write_bytes(path: Union[str, Path], data: bytes) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def atomic_write_text(path: Union[str, Path], text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def atomic_write_json(path: Union[str, Path], obj: Any, encoding: str = "utf-8") -> None:
    atomic_write_text(path, stable_json_dumps(obj) + "\n", encoding=encoding)
