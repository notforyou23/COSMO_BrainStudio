"""Shared, dependency-light utilities for experiments.

This module intentionally avoids heavy dependencies; integrations with NumPy/Torch
are optional and only activated if those libraries are installed.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as _dt
import getpass as _getpass
import hashlib as _hashlib
import json as _json
import os as _os
import platform as _platform
import random as _random
import socket as _socket
import subprocess as _subprocess
import sys as _sys
from typing import Any, Dict, Mapping, Optional
__all__ = [
    "RunInfo",
    "now_utc_iso",
    "stable_hash",
    "set_global_seed",
    "deep_update",
    "flatten_dict",
    "collect_env_metadata",
]
def now_utc_iso(timespec: str = "seconds") -> str:
    """Return current UTC time in ISO-8601 format with 'Z'."""
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec=timespec).replace("+00:00", "Z")


def stable_hash(obj: Any, *, n_hex: int = 10) -> str:
    """Deterministic short hash for JSON-serializable objects."""
    payload = _json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _hashlib.sha256(payload).hexdigest()[:n_hex]
def set_global_seed(seed: int, *, deterministic: bool = False) -> None:
    """Seed common RNGs (random, NumPy, Torch if available)."""
    seed = int(seed)
    _os.environ["PYTHONHASHSEED"] = str(seed)
    _random.seed(seed)

    try:  # optional numpy
        import numpy as np  # type: ignore

        np.random.seed(seed)
    except Exception:
        pass

    try:  # optional torch
        import torch  # type: ignore

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if deterministic:
            try:
                torch.use_deterministic_algorithms(True)
            except Exception:
                pass
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except Exception:
        pass
def deep_update(base: Mapping[str, Any], updates: Mapping[str, Any]) -> Dict[str, Any]:
    """Recursively merge updates into base (returns a new dict)."""
    out: Dict[str, Any] = dict(base)
    for k, v in updates.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
            out[k] = deep_update(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def flatten_dict(d: Mapping[str, Any], *, sep: str = ".", prefix: str = "") -> Dict[str, Any]:
    """Flatten nested dictionaries into a single-level dict with joined keys."""
    items: Dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{sep}{k}" if prefix else str(k)
        if isinstance(v, Mapping):
            items.update(flatten_dict(v, sep=sep, prefix=key))
        else:
            items[key] = v
    return items
def _git_commit(cwd: Optional[str] = None) -> Optional[str]:
    try:
        p = _subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            stdout=_subprocess.PIPE,
            stderr=_subprocess.DEVNULL,
            check=True,
            text=True,
        )
        return p.stdout.strip() or None
    except Exception:
        return None


def collect_env_metadata(*, extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Collect lightweight runtime metadata for provenance."""
    meta: Dict[str, Any] = {
        "time_utc": now_utc_iso(),
        "python": _sys.version.split()[0],
        "platform": _platform.platform(),
        "hostname": _socket.gethostname(),
        "user": _getpass.getuser(),
        "cwd": _os.getcwd(),
        "git_commit": _git_commit(_os.getcwd()),
    }
    if extra:
        meta.update(dict(extra))
    return meta
@dataclass(frozen=True)
class RunInfo:
    """Minimal run identifier + metadata helper."""

    seed: int
    created_utc: str
    config_hash: str

    @classmethod
    def create(cls, *, seed: int, config: Mapping[str, Any]) -> "RunInfo":
        return cls(seed=int(seed), created_utc=now_utc_iso(), config_hash=stable_hash(config))

    @property
    def run_id(self) -> str:
        ts = self.created_utc.replace(":", "").replace("-", "")
        return f"{ts}_{self.config_hash}"
