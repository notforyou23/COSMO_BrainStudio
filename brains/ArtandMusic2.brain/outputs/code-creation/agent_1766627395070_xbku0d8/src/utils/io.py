from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Union
import json
import os
import re
import time
import uuid


JSON = Union[None, bool, int, float, str, List["JSON"], Dict[str, "JSON"]]


def _now_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def ensure_dir(p: Union[str, Path]) -> Path:
    path = Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str, max_len: int = 120) -> str:
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("._-")
    if not name:
        name = "run"
    return name[:max_len]


def make_run_dir(base_dir: Union[str, Path], run_name: Optional[str] = None, *, add_uuid: bool = True) -> Path:
    base = ensure_dir(base_dir)
    stem = sanitize_filename(run_name or f"run_{_now_stamp()}")
    suffix = f"_{uuid.uuid4().hex[:8]}" if add_uuid else ""
    run_dir = base / f"{stem}{suffix}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _to_jsonable(obj: Any, *, _depth: int = 0) -> JSON:
    if _depth > 50:
        return repr(obj)
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj), _depth=_depth + 1)
    if isinstance(obj, Mapping):
        return {str(k): _to_jsonable(v, _depth=_depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v, _depth=_depth + 1) for v in obj]
    if isinstance(obj, set):
        return sorted([_to_jsonable(v, _depth=_depth + 1) for v in obj], key=lambda x: str(x))
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return _to_jsonable(obj.model_dump(), _depth=_depth + 1)
        except Exception:
            return repr(obj)
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return _to_jsonable(obj.dict(), _depth=_depth + 1)
        except Exception:
            return repr(obj)
    try:
        import numpy as np  # type: ignore
        if isinstance(obj, (np.integer, np.floating, np.bool_)):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return _to_jsonable(obj.tolist(), _depth=_depth + 1)
    except Exception:
        pass
    if hasattr(obj, "__json__") and callable(getattr(obj, "__json__")):
        try:
            return _to_jsonable(obj.__json__(), _depth=_depth + 1)
        except Exception:
            return repr(obj)
    return repr(obj)


def dumps_json(data: Any, *, indent: Optional[int] = 2, sort_keys: bool = True) -> str:
    return json.dumps(_to_jsonable(data), ensure_ascii=False, indent=indent, sort_keys=sort_keys)


def write_json(path: Union[str, Path], data: Any, *, indent: Optional[int] = 2, sort_keys: bool = True) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(dumps_json(data, indent=indent, sort_keys=sort_keys) + "
", encoding="utf-8")
    os.replace(tmp, p)
    return p


def read_json(path: Union[str, Path]) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: Union[str, Path]) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return iter(())
    def _iter() -> Iterator[Dict[str, Any]]:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)
    return _iter()


def write_jsonl(path: Union[str, Path], rows: Iterable[Mapping[str, Any]], *, append: bool = False) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with p.open(mode, encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(_to_jsonable(dict(r)), ensure_ascii=False, sort_keys=True) + "
")
    return p


def canonicalize_citations(citations: Any) -> List[Dict[str, Any]]:
    if citations is None:
        return []
    if isinstance(citations, Mapping):
        citations = [citations]
    out: List[Dict[str, Any]] = []
    for c in citations:
        if not isinstance(c, Mapping):
            out.append({"raw": _to_jsonable(c)})
            continue
        d = dict(c)
        if "doc_id" not in d and "source_id" in d:
            d["doc_id"] = d.get("source_id")
        if "span" in d and isinstance(d["span"], (list, tuple)) and len(d["span"]) == 2:
            d["span"] = {"start": d["span"][0], "end": d["span"][1]}
        out.append(_to_jsonable(d))  # type: ignore[arg-type]
    return out


def pack_record(*, prompt: Any = None, response: Any = None, scores: Any = None, citations: Any = None, **extra: Any) -> Dict[str, Any]:
    rec: Dict[str, Any] = {}
    if prompt is not None:
        rec["prompt"] = _to_jsonable(prompt)
    if response is not None:
        rec["response"] = _to_jsonable(response)
    if scores is not None:
        rec["scores"] = _to_jsonable(scores)
    if citations is not None:
        rec["citations"] = canonicalize_citations(citations)
    for k, v in extra.items():
        rec[str(k)] = _to_jsonable(v)
    return rec
