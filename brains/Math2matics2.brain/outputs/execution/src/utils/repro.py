"""Reproducibility utilities.

- set_global_seed(): seed Python/NumPy/PyTorch (if installed) and enable deterministic behavior.
- hashing helpers: stable hashes for files/directories to support determinism tests.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union


def set_global_seed(
    seed: int = 0,
    deterministic: bool = True,
    *,
    set_pythonhashseed: bool = True,
    set_cublas_workspace_config: bool = True,
) -> Dict[str, Union[int, bool, str]]:
    """Seed common RNGs and (optionally) force deterministic settings where available.

    Returns a small report dict describing what was applied.
    """
    if not isinstance(seed, int):
        raise TypeError(f"seed must be int, got {type(seed)!r}")

    report: Dict[str, Union[int, bool, str]] = {"seed": seed, "deterministic": bool(deterministic)}

    if set_pythonhashseed:
        os.environ["PYTHONHASHSEED"] = str(seed)
        report["PYTHONHASHSEED"] = os.environ["PYTHONHASHSEED"]

    # Python RNG
    random.seed(seed)
    report["python_random_seeded"] = True

    # NumPy RNG (optional)
    try:
        import numpy as np  # type: ignore

        np.random.seed(seed)
        report["numpy_seeded"] = True
    except Exception:
        report["numpy_seeded"] = False

    # PyTorch RNG + deterministic settings (optional)
    try:
        import torch  # type: ignore

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

        report["torch_seeded"] = True

        if deterministic:
            # cuDNN determinism
            try:
                torch.backends.cudnn.deterministic = True
                torch.backends.cudnn.benchmark = False
                report["torch_cudnn_deterministic"] = True
            except Exception:
                report["torch_cudnn_deterministic"] = False

            # Deterministic algorithms (PyTorch>=1.8)
            try:
                torch.use_deterministic_algorithms(True)  # may throw on unsupported ops later
                report["torch_use_deterministic_algorithms"] = True
            except Exception:
                report["torch_use_deterministic_algorithms"] = False

            # cuBLAS workspace config is recommended for determinism on some CUDA versions
            if set_cublas_workspace_config:
                os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
                report["CUBLAS_WORKSPACE_CONFIG"] = os.environ.get("CUBLAS_WORKSPACE_CONFIG", "")
    except Exception:
        report["torch_seeded"] = False

    return report


def _iter_files(
    paths: Sequence[Union[str, Path]],
    *,
    ignore_globs: Sequence[str] = (),
) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
        else:
            for fp in sorted(path.rglob("*")):
                if fp.is_file():
                    rel = fp.relative_to(path)
                    rel_s = rel.as_posix()
                    if any(fnmatch.fnmatch(rel_s, g) for g in ignore_globs):
                        continue
                    files.append(fp)
    # Sort by full (posix) path for stability across platforms
    return sorted(files, key=lambda x: x.as_posix())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Union[str, Path], *, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    p = Path(path)
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(
    path: Union[str, Path],
    *,
    ignore_globs: Sequence[str] = (),
) -> str:
    """Compute a stable hash of a directory tree (or a single file).

    The hash includes file relative paths and file contents, in a stable order.
    """
    base = Path(path)
    files = _iter_files([base], ignore_globs=ignore_globs)
    h = hashlib.sha256()
    if base.is_file():
        h.update(base.name.encode("utf-8"))
        h.update(b"\0")
        h.update(bytes.fromhex(sha256_file(base)))
        return h.hexdigest()

    for fp in files:
        rel = fp.relative_to(base).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(bytes.fromhex(sha256_file(fp)))
        h.update(b"\n")
    return h.hexdigest()


def sha256_artifacts(
    paths: Sequence[Union[str, Path]],
    *,
    ignore_globs: Sequence[str] = (),
) -> Dict[str, str]:
    """Hash a set of files/directories; returns {normalized_path: hash}."""
    out: Dict[str, str] = {}
    for p in paths:
        pp = Path(p)
        if not pp.exists():
            continue
        key = pp.as_posix()
        out[key] = sha256_tree(pp, ignore_globs=ignore_globs)
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


@dataclass(frozen=True)
class DeterminismConfig:
    seed: int = 0
    deterministic: bool = True
    ignore_globs: Tuple[str, ...] = ("**/__pycache__/**", "**/*.pyc", "**/.DS_Store")


def apply_determinism(cfg: DeterminismConfig) -> Dict[str, Union[int, bool, str]]:
    return set_global_seed(cfg.seed, deterministic=cfg.deterministic)
