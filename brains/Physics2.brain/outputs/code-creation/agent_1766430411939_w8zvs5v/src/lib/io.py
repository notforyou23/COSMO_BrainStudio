"""Output management utilities.

Provides deterministic run IDs / filenames and small helpers to write
manifests and parameter dumps for reproducible experiments.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Union
import hashlib
import json
import os
import time


Jsonable = Union[None, bool, int, float, str, list, dict]


def _to_jsonable(obj: Any) -> Jsonable:
    """Best-effort conversion to something json.dumps can handle."""
    if is_dataclass(obj):
        obj = asdict(obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Mapping):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    # Fallback: stable string repr (avoid non-deterministic object ids).
    return str(obj)


def stable_json_dumps(data: Any) -> str:
    """Canonical JSON string for hashing (sorted keys, no whitespace)."""
    return json.dumps(_to_jsonable(data), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def short_hash(data: Any, n: int = 12) -> str:
    """Deterministic short hash of data (via canonical JSON)."""
    h = hashlib.sha256(stable_json_dumps(data).encode("utf-8")).hexdigest()
    return h[: max(4, int(n))]


def build_run_id(params: Any, *, prefix: str = "run", tag: str = "", n: int = 12) -> str:
    """Build a deterministic run identifier from parameters.

    The returned value is suitable for directory/file naming.
    """
    core = short_hash(params, n=n)
    if tag:
        tag = "-" + "".join(c for c in str(tag) if c.isalnum() or c in "-_")[:40]
    return f"{prefix}-{core}{tag}"


def ensure_dir(path: Union[str, Path]) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def atomic_write_text(path: Union[str, Path], text: str, *, encoding: str = "utf-8") -> Path:
    """Atomic-ish write (write temp then replace)."""
    path = Path(path)
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(path)
    return path


def write_json(path: Union[str, Path], data: Any, *, indent: int = 2) -> Path:
    path = Path(path)
    txt = json.dumps(_to_jsonable(data), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"
    return atomic_write_text(path, txt)


def write_params_dump(out_dir: Union[str, Path], params: Any, *, name: str = "params.json") -> Path:
    out_dir = ensure_dir(out_dir)
    return write_json(out_dir / name, params)


def write_run_manifest(
    out_dir: Union[str, Path],
    *,
    params: Any,
    run_id: Optional[str] = None,
    argv: Optional[list[str]] = None,
    extra: Optional[Mapping[str, Any]] = None,
    name: str = "manifest.json",
) -> Path:
    """Write a manifest.json capturing params + execution metadata."""
    out_dir = ensure_dir(out_dir)
    rid = run_id or build_run_id(params)
    manifest: dict[str, Any] = {
        "run_id": rid,
        "created_unix": int(time.time()),
        "cwd": str(Path.cwd()),
        "params_hash": short_hash(params),
        "params": _to_jsonable(params),
        "argv": list(argv) if argv is not None else None,
        "env": {k: os.environ.get(k) for k in ("PYTHONHASHSEED", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
    }
    if extra:
        manifest["extra"] = _to_jsonable(dict(extra))
    return write_json(out_dir / name, manifest)


def deterministic_path(
    out_dir: Union[str, Path],
    *,
    stem: str,
    params: Any,
    ext: str = ".json",
    tag: str = "",
) -> Path:
    """Deterministically name an output file based on params."""
    out_dir = ensure_dir(out_dir)
    safe_stem = "".join(c for c in str(stem) if c.isalnum() or c in "-_") or "out"
    if ext and not ext.startswith("."):
        ext = "." + ext
    return out_dir / f"{safe_stem}-{short_hash(params)}{('-'+tag) if tag else ''}{ext}"
