"""Reproducibility utilities: seeding, deterministic settings, and artifact hashing."""

from __future__ import annotations

import contextlib
import hashlib
import os
import random
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

try:
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover
    _np = None  # type: ignore

try:
    import torch as _torch  # type: ignore
except Exception:  # pragma: no cover
    _torch = None  # type: ignore

PathLike = Union[str, os.PathLike]


def set_seed(seed: int = 0, deterministic: bool = True, *, cublas_workspace: str = ":4096:8") -> None:
    """Seed Python/NumPy/PyTorch and request deterministic behavior where possible."""
    seed = int(seed)
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)

    if _np is not None:
        _np.random.seed(seed)

    if _torch is not None:
        _torch.manual_seed(seed)
        if _torch.cuda.is_available():
            _torch.cuda.manual_seed_all(seed)

        if deterministic:
            os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", cublas_workspace)
            try:
                _torch.use_deterministic_algorithms(True)
            except Exception:
                pass
            try:
                _torch.backends.cudnn.deterministic = True  # type: ignore[attr-defined]
                _torch.backends.cudnn.benchmark = False  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                _torch.backends.cuda.matmul.allow_tf32 = False  # type: ignore[attr-defined]
                _torch.backends.cudnn.allow_tf32 = False  # type: ignore[attr-defined]
            except Exception:
                pass
@contextlib.contextmanager
def deterministic_context(seed: int = 0, deterministic: bool = True) -> Iterator[None]:
    """Context manager that sets seeds and deterministic flags and restores RNG states."""
    py_state = random.getstate()
    np_state = _np.random.get_state() if _np is not None else None
    torch_state = None
    torch_cuda_state = None
    if _torch is not None:
        torch_state = _torch.random.get_rng_state()
        if _torch.cuda.is_available():
            try:
                torch_cuda_state = _torch.cuda.get_rng_state_all()
            except Exception:
                torch_cuda_state = None
    try:
        set_seed(seed, deterministic=deterministic)
        yield
    finally:
        random.setstate(py_state)
        if _np is not None and np_state is not None:
            _np.random.set_state(np_state)
        if _torch is not None and torch_state is not None:
            _torch.random.set_rng_state(torch_state)
            if _torch.cuda.is_available() and torch_cuda_state is not None:
                try:
                    _torch.cuda.set_rng_state_all(torch_cuda_state)
                except Exception:
                    pass
def _iter_files(paths: Sequence[PathLike], *, follow_symlinks: bool = False) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for f in sorted(path.rglob("*")):
                try:
                    if f.is_file():
                        if not follow_symlinks and f.is_symlink():
                            continue
                        files.append(f)
                except OSError:
                    continue
    return sorted(set(files), key=lambda x: str(x))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: PathLike, *, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    p = Path(path)
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_artifacts(paths: Sequence[PathLike], *, base_dir: Optional[PathLike] = None) -> Dict[str, str]:
    """Return mapping of relative artifact paths -> sha256 for all files under given paths."""
    base = Path(base_dir) if base_dir is not None else None
    out: Dict[str, str] = {}
    for f in _iter_files(paths):
        key = str(f)
        if base is not None:
            try:
                key = str(f.relative_to(base))
            except Exception:
                key = str(f)
        out[key] = sha256_file(f)
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def combined_hash(hashes: Mapping[str, str]) -> str:
    """Stable combined hash from a mapping produced by hash_artifacts."""
    h = hashlib.sha256()
    for k, v in sorted(hashes.items(), key=lambda kv: kv[0]):
        h.update(k.encode("utf-8", "surrogatepass"))
        h.update(b"\0")
        h.update(v.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()
