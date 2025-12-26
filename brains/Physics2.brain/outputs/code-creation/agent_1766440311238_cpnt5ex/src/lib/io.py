"""src.lib.io

Small I/O helpers for reproducible prototype experiments.

Design goals:
- Deterministic JSON serialization (stable key order, stable float formatting).
- Atomic writes (write to temp file then replace).
- Lightweight metadata capture for run reproducibility.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
import csv
import datetime as _dt
import hashlib
import json
import os
import platform
import sys
Jsonable = Union[None, bool, int, float, str, List["Jsonable"], Dict[str, "Jsonable"]]


def _to_jsonable(obj: Any) -> Jsonable:
    """Convert common Python objects to JSON-compatible structures."""
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (tuple, set)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    return obj  # assume already JSON-serializable
class _DeterministicFloatEncoder(json.JSONEncoder):
    """JSON encoder with stable float formatting."""

    def iterencode(self, o: Any, _one_shot: bool = False):  # type: ignore[override]
        # Adapted from CPython encoder: force float repr via format.
        def floatstr(
            obj: float,
            allow_nan=self.allow_nan,
            _inf=float("inf"),
            _neginf=-float("inf"),
        ):
            if obj != obj:
                text = "NaN"
            elif obj == _inf:
                text = "Infinity"
            elif obj == _neginf:
                text = "-Infinity"
            else:
                # 17 significant digits round-trips IEEE754 and is deterministic.
                text = format(obj, ".17g")
            if not allow_nan and text in {"NaN", "Infinity", "-Infinity"}:
                raise ValueError("Out of range float values are not JSON compliant")
            return text

        encoder = json.encoder._make_iterencode(  # type: ignore[attr-defined]
            None,
            self.default,
            json.encoder.encode_basestring,  # type: ignore[attr-defined]
            self.indent,
            floatstr,
            self.key_separator,
            self.item_separator,
            self.sort_keys,
            self.skipkeys,
            _one_shot,
        )
        return encoder(o, 0)
def stable_json_dumps(data: Any, *, indent: int = 2) -> str:
    """Deterministically serialize to JSON (sorted keys + stable floats)."""
    payload = _to_jsonable(data)
    return json.dumps(
        payload,
        cls=_DeterministicFloatEncoder,
        sort_keys=True,
        ensure_ascii=False,
        indent=indent,
        separators=(",", ": "),
    ) + "\n"


def _atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)
def save_json(path: Union[str, Path], data: Any, *, indent: int = 2) -> Path:
    """Save JSON deterministically and atomically."""
    p = Path(path)
    _atomic_write_text(p, stable_json_dumps(data, indent=indent))
    return p


def load_json(path: Union[str, Path]) -> Any:
    """Load JSON from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
def save_csv(
    path: Union[str, Path],
    rows: Sequence[Mapping[str, Any]],
    *,
    fieldnames: Optional[Sequence[str]] = None,
) -> Path:
    """Save rows (dicts) to CSV with stable column order.

    If fieldnames is not provided, it is the sorted union of keys across rows.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys = set()
        for r in rows:
            keys.update(r.keys())
        fieldnames = sorted(str(k) for k in keys)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fieldnames))
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    os.replace(tmp, p)
    return p


def load_csv(path: Union[str, Path]) -> List[Dict[str, str]]:
    """Load CSV into list of dicts (all values as strings)."""
    p = Path(path)
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))
def capture_metadata(
    *,
    params: Optional[Mapping[str, Any]] = None,
    extra: Optional[Mapping[str, Any]] = None,
    packages: Sequence[str] = ("numpy", "sympy", "pandas", "matplotlib"),
) -> Dict[str, Any]:
    """Capture lightweight metadata for reproducible runs."""
    meta: Dict[str, Any] = {
        "timestamp_utc": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "argv": sys.argv[:],
    }
    # Optional package versions (best-effort).
    vers: Dict[str, str] = {}
    for name in packages:
        try:
            mod = __import__(name)
            v = getattr(mod, "__version__", None)
            if v:
                vers[name] = str(v)
        except Exception:
            continue
    if vers:
        meta["packages"] = dict(sorted(vers.items()))
    if params is not None:
        meta["params"] = _to_jsonable(dict(params))
    if extra is not None:
        meta["extra"] = _to_jsonable(dict(extra))
    meta["fingerprint_sha256"] = hashlib.sha256(
        stable_json_dumps(meta, indent=0).encode("utf-8")
    ).hexdigest()
    return meta
