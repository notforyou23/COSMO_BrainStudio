from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union


PathLike = Union[str, Path]


def ensure_parent_dir(path: PathLike) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: PathLike) -> Any:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(obj: Any, path: PathLike, *, indent: int = 2, sort_keys: bool = True) -> Path:
    p = ensure_parent_dir(path)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent, sort_keys=sort_keys)
        f.write("\n")
    return p


def read_jsonl(path: PathLike) -> List[Dict[str, Any]]:
    p = Path(path)
    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"Expected JSON object per line in {p}, got {type(obj).__name__}")
            rows.append(obj)
    return rows


def write_jsonl(records: Iterable[Mapping[str, Any]], path: PathLike, *, append: bool = False) -> Path:
    p = ensure_parent_dir(path)
    mode = "a" if append else "w"
    with p.open(mode, encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(dict(rec), ensure_ascii=False))
            f.write("\n")
    return p


def read_csv_dicts(path: PathLike) -> List[Dict[str, str]]:
    p = Path(path)
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def write_csv_dicts(
    rows: Sequence[Mapping[str, Any]],
    path: PathLike,
    *,
    fieldnames: Optional[Sequence[str]] = None,
    extrasaction: str = "ignore",
) -> Path:
    p = ensure_parent_dir(path)
    if fieldnames is None:
        keys = []
        seen = set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
        fieldnames = keys
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction=extrasaction)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})
    return p


def save_sweep_curve(
    curve_rows: Sequence[Mapping[str, Any]],
    out_path: PathLike,
    *,
    fmt: Optional[str] = None,
) -> Path:
    p = Path(out_path)
    if fmt is None:
        suf = p.suffix.lower().lstrip(".")
        fmt = suf if suf else "jsonl"
    fmt = fmt.lower()
    if fmt in ("jsonl", "jl"):
        return write_jsonl(curve_rows, p)
    if fmt == "json":
        return write_json(list(curve_rows), p)
    if fmt == "csv":
        return write_csv_dicts(curve_rows, p)
    raise ValueError(f"Unsupported sweep curve format: {fmt}")


def save_decision_traces(
    traces: Sequence[Mapping[str, Any]],
    out_path: PathLike,
    *,
    fmt: Optional[str] = None,
) -> Path:
    p = Path(out_path)
    if fmt is None:
        suf = p.suffix.lower().lstrip(".")
        fmt = suf if suf else "jsonl"
    fmt = fmt.lower()
    if fmt in ("jsonl", "jl"):
        return write_jsonl(traces, p)
    if fmt == "json":
        return write_json(list(traces), p)
    if fmt == "csv":
        return write_csv_dicts(traces, p)
    raise ValueError(f"Unsupported decision trace format: {fmt}")
