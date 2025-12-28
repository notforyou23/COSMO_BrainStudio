"""I/O utilities for taxonomy annotations (JSONL/CSV) and validation reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple
import csv
import json


def _clean_scalar(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        if s.lower() in {"null", "none", "na", "n/a"}:
            return None
        return s
    return v


def normalize_record(obj: Mapping[str, Any], *, source_path: Optional[str] = None, row_index: Optional[int] = None) -> Dict[str, Any]:
    rec: Dict[str, Any] = {str(k).strip(): _clean_scalar(v) for k, v in dict(obj).items() if str(k).strip() != ""}
    meta = rec.get("_meta")
    if meta is None or not isinstance(meta, dict):
        meta = {}
    if source_path is not None:
        meta.setdefault("source_path", source_path)
    if row_index is not None:
        meta.setdefault("row_index", row_index)
    rec["_meta"] = meta
    if "record_id" in rec and rec["record_id"] is not None:
        rec["record_id"] = str(rec["record_id"])
    return rec


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL row must be an object at {path}:{i}")
            yield normalize_record(obj, source_path=str(path), row_index=i)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return list(iter_jsonl(path))


def iter_csv(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return
        for i, row in enumerate(reader, start=2):  # header is line 1
            row = {k: v for k, v in row.items() if k is not None}
            yield normalize_record(row, source_path=str(path), row_index=i)


def read_csv(path: Path) -> List[Dict[str, Any]]:
    return list(iter_csv(path))


def iter_annotations(path: Path) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    suf = p.suffix.lower()
    if suf == ".jsonl":
        yield from iter_jsonl(p)
    elif suf == ".csv":
        yield from iter_csv(p)
    else:
        raise ValueError(f"Unsupported annotation format: {p.suffix} (expected .jsonl or .csv)")


def read_annotations(path: Path) -> List[Dict[str, Any]]:
    return list(iter_annotations(path))


def write_validation_report(report_path: Path, report: Mapping[str, Any]) -> Path:
    p = Path(report_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return p
