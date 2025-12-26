from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Union

Json = Union[None, bool, int, float, str, List["Json"], Dict[str, "Json"]]


def ensure_dir(path: Union[str, Path]) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now_utc_compact() -> str:
    return _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _slug(s: str, max_len: int = 64) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "-", s).strip("-")
    return s[:max_len] if s else "run"


def make_run_dir(
    base_dir: Union[str, Path],
    name: Optional[str] = None,
    prefix: str = "run",
    exist_ok: bool = False,
) -> Path:
    base = ensure_dir(base_dir)
    stem = f"{prefix}-{_now_utc_compact()}"
    if name:
        stem += f"-{_slug(name)}"
    out = base / stem
    if exist_ok:
        out.mkdir(parents=True, exist_ok=True)
        return out
    for i in range(1000):
        p = out if i == 0 else base / f"{stem}-{i:03d}"
        try:
            p.mkdir(parents=True, exist_ok=False)
            return p
        except FileExistsError:
            continue
    raise RuntimeError("Failed to allocate a unique run directory")


def atomic_write_text(path: Union[str, Path], text: str, encoding: str = "utf-8") -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    tmp = p.with_suffix(p.suffix + f".tmp.{os.getpid()}.{int(time.time()*1000)}")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(p)
    return p


def to_jsonable(x: Any) -> Json:
    if x is None or isinstance(x, (bool, int, float, str)):
        return x
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, (bytes, bytearray, memoryview)):
        return {"__type__": "bytes", "len": len(x)}
    if dataclasses.is_dataclass(x):
        return to_jsonable(dataclasses.asdict(x))
    if hasattr(x, "model_dump") and callable(getattr(x, "model_dump")):
        return to_jsonable(x.model_dump())
    if hasattr(x, "dict") and callable(getattr(x, "dict")):
        try:
            return to_jsonable(x.dict())
        except TypeError:
            pass
    if isinstance(x, _dt.datetime):
        return x.isoformat()
    if isinstance(x, _dt.date):
        return x.isoformat()
    if isinstance(x, Mapping):
        return {str(k): to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [to_jsonable(v) for v in x]
    if hasattr(x, "tolist") and callable(getattr(x, "tolist")):
        try:
            return to_jsonable(x.tolist())
        except Exception:
            pass
    if hasattr(x, "__dict__"):
        try:
            return to_jsonable(vars(x))
        except Exception:
            pass
    return {"__type__": type(x).__name__, "repr": repr(x)}


def dumps(obj: Any, *, indent: Optional[int] = None, sort_keys: bool = True) -> str:
    return json.dumps(to_jsonable(obj), ensure_ascii=False, indent=indent, sort_keys=sort_keys)


def read_jsonl(path: Union[str, Path]) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(
    path: Union[str, Path],
    rows: Iterable[Any],
    *,
    append: bool = False,
) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    mode = "a" if append else "w"
    with p.open(mode, encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(to_jsonable(r), ensure_ascii=False))
            f.write("\n")
    return p


def write_json(path: Union[str, Path], obj: Any, *, indent: int = 2) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    return atomic_write_text(p, dumps(obj, indent=indent) + "\n")


def standardize_citation(c: Any) -> Dict[str, Any]:
    if c is None:
        return {}
    if isinstance(c, str):
        return {"ref": c}
    if isinstance(c, Mapping):
        d = dict(c)
    else:
        d = {"value": c}
    out: Dict[str, Any] = {}
    for k in ("doc_id", "source", "url", "title", "chunk_id", "span", "start", "end", "ref", "quote"):
        if k in d and d[k] is not None:
            out[k] = d[k]
    if not out:
        out = {"ref": str(d.get("ref") or d.get("value") or "")}
    return to_jsonable(out)  # type: ignore[return-value]


def standardize_score(s: Any) -> Dict[str, Any]:
    if s is None:
        return {}
    if isinstance(s, (int, float)):
        return {"value": float(s)}
    if isinstance(s, Mapping):
        d = dict(s)
    else:
        d = {"value": s}
    out: Dict[str, Any] = {}
    if "name" in d:
        out["name"] = str(d["name"])
    if "value" in d and d["value"] is not None:
        try:
            out["value"] = float(d["value"])
        except Exception:
            out["value"] = d["value"]
    for k in ("label", "rationale", "confidence", "threshold", "passed"):
        if k in d and d[k] is not None:
            out[k] = d[k]
    return to_jsonable(out)  # type: ignore[return-value]
