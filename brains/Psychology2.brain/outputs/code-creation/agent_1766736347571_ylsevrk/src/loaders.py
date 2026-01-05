"""Robust loaders for extraction CSV, taxonomy JSONL, and prereg metadata.

These functions focus on resilient parsing + consistent, validation-friendly keys.
Validation (ID schema, uniqueness, referential integrity) is performed elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
_NONKEY_RE = re.compile(r"[^a-z0-9_]+")
_WS_RE = re.compile(r"\s+")


def _norm_key(k: Any) -> str:
    s = "" if k is None else str(k)
    s = s.strip().lower()
    s = _WS_RE.sub("_", s)
    s = s.replace("-", "_").replace("/", "_")
    s = _NONKEY_RE.sub("_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def _norm_val(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return None if s == "" else s
    return v


def _norm_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in (rec or {}).items():
        nk = _norm_key(k)
        if not nk:
            continue
        if nk in out:
            i = 2
            while f"{nk}_{i}" in out:
                i += 1
            nk = f"{nk}_{i}"
        out[nk] = _norm_val(v)
    return out
@dataclass(frozen=True)
class LoadedData:
    extraction: List[Dict[str, Any]]
    taxonomy: List[Dict[str, Any]]
    prereg: List[Dict[str, Any]]

    def as_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        return {"extraction": self.extraction, "taxonomy": self.taxonomy, "prereg": self.prereg}
def _read_text(path: Union[str, Path]) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8-sig")


def load_extraction_csv(path: Union[str, Path]) -> List[Dict[str, Any]]:
    p = Path(path)
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, Any]] = []
        for i, row in enumerate(reader, start=2):  # header is line 1
            rec = _norm_record(row)
            rec["_source"] = "extraction_csv"
            rec["_source_path"] = str(p)
            rec["_source_line"] = i
            rows.append(rec)
    return rows


def load_taxonomy_jsonl(path: Union[str, Path]) -> List[Dict[str, Any]]:
    p = Path(path)
    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8-sig") as f:
        for i, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if not isinstance(obj, dict):
                raise ValueError(f"taxonomy JSONL line {i} must be an object")
            rec = _norm_record(obj)
            rec["_source"] = "taxonomy_jsonl"
            rec["_source_path"] = str(p)
            rec["_source_line"] = i
            rows.append(rec)
    return rows
def _load_prereg_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows: List[Dict[str, Any]] = []
        for i, row in enumerate(reader, start=2):
            rec = _norm_record(row)
            rec["_source"] = "prereg_csv"
            rec["_source_path"] = str(path)
            rec["_source_line"] = i
            rows.append(rec)
    return rows


def _load_prereg_json(path: Path) -> List[Dict[str, Any]]:
    obj = json.loads(_read_text(path))
    rows: List[Dict[str, Any]] = []
    if isinstance(obj, dict):
        rows = [_norm_record(obj)]
    elif isinstance(obj, list):
        rows = [_norm_record(x) if isinstance(x, dict) else {"value": x} for x in obj]
    else:
        rows = [{"value": obj}]
    for idx, rec in enumerate(rows, start=1):
        rec["_source"] = "prereg_json"
        rec["_source_path"] = str(path)
        rec["_source_line"] = idx
    return rows


def load_prereg(path: Union[str, Path]) -> List[Dict[str, Any]]:
    p = Path(path)
    suf = p.suffix.lower()
    if suf == ".csv":
        return _load_prereg_csv(p)
    if suf in {".json", ".jsn"}:
        return _load_prereg_json(p)
    raise ValueError(f"Unsupported prereg file type: {p.suffix}")
def load_all(
    extraction_csv: Union[str, Path],
    taxonomy_jsonl: Union[str, Path],
    prereg: Union[str, Path],
) -> LoadedData:
    return LoadedData(
        extraction=load_extraction_csv(extraction_csv),
        taxonomy=load_taxonomy_jsonl(taxonomy_jsonl),
        prereg=load_prereg(prereg),
    )
