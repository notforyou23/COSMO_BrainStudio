from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import json
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

@dataclass(frozen=True)
class NormalizedRecord:
    kind: str  # 'extraction' | 'taxonomy' | 'prereg'
    stable_id: str
    payload: Dict[str, Any]
    source_path: str
    source_ref: str  # row number, jsonl line number, key name, etc.

def _strip_bom(s: str) -> str:
    return s[1:] if s and s[0] == "\ufeff" else s

def _clean(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        vv = v.strip()
        if vv == "" or vv.lower() in {"na", "n/a", "null", "none"}:
            return None
        return vv
    return v

def _normalize_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        kk = _strip_bom(str(k)).strip()
        out[kk] = _clean(v)
    return out

def _guess_delimiter(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".tsv":
        return "\t"
    if ext == ".csv":
        return ","
    with path.open("r", encoding="utf-8", newline="") as f:
        sample = f.read(4096)
    try:
        return csv.Sniffer().sniff(sample, delimiters=[",", "\t", ";", "|"]).delimiter
    except Exception:
        return ","

def _iter_csv_rows(path: Path, delimiter: Optional[str] = None) -> Iterator[Tuple[int, Dict[str, Any]]]:
    delim = delimiter or _guess_delimiter(path)
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        for i, row in enumerate(reader, start=2):  # header is line 1
            if row is None:
                continue
            yield i, _normalize_keys(row)

def _stable_id_from_fields(rec: Dict[str, Any], fields: List[str]) -> Optional[str]:
    parts: List[str] = []
    for f in fields:
        v = rec.get(f)
        if v is None:
            return None
        parts.append(str(v))
    return "|".join(parts) if parts else None
def read_extraction_rows(
    path: str | Path,
    *,
    stable_id_col: str = "extraction_id",
    stable_id_fields: Optional[List[str]] = None,
    delimiter: Optional[str] = None,
) -> List[NormalizedRecord]:
    p = Path(path)
    out: List[NormalizedRecord] = []
    for line_no, row in _iter_csv_rows(p, delimiter=delimiter):
        stable_id = row.get(stable_id_col)
        if stable_id is None and stable_id_fields:
            stable_id = _stable_id_from_fields(row, stable_id_fields)
        if stable_id is None:
            raise ValueError(f"Missing stable extraction id at {p} line {line_no} (col '{stable_id_col}')")
        out.append(
            NormalizedRecord(
                kind="extraction",
                stable_id=str(stable_id),
                payload=row,
                source_path=str(p),
                source_ref=f"line:{line_no}",
            )
        )
    return out

def read_taxonomy_jsonl(
    path: str | Path,
    *,
    stable_id_key: str = "extraction_id",
) -> List[NormalizedRecord]:
    p = Path(path)
    out: List[NormalizedRecord] = []
    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL object must be dict at {p} line {i}")
            obj = _normalize_keys(obj)
            sid = obj.get(stable_id_key)
            if sid is None:
                raise ValueError(f"Missing taxonomy stable id key '{stable_id_key}' at {p} line {i}")
            out.append(
                NormalizedRecord(
                    kind="taxonomy",
                    stable_id=str(sid),
                    payload=obj,
                    source_path=str(p),
                    source_ref=f"line:{i}",
                )
            )
    return out

def read_prereg_fields(
    path: str | Path,
    *,
    stable_id: str,
    key_col: str = "field",
    value_col: str = "value",
    delimiter: Optional[str] = None,
) -> List[NormalizedRecord]:
    p = Path(path)
    ext = p.suffix.lower()
    payload: Dict[str, Any] = {}
    if ext == ".json":
        payload = _normalize_keys(json.loads(p.read_text(encoding="utf-8")))
        if not isinstance(payload, dict):
            raise ValueError(f"Prereg JSON must be an object/dict: {p}")
    else:
        for line_no, row in _iter_csv_rows(p, delimiter=delimiter):
            k = row.get(key_col)
            if k is None:
                raise ValueError(f"Missing prereg key_col '{key_col}' at {p} line {line_no}")
            payload[str(k)] = row.get(value_col)
    return [
        NormalizedRecord(
            kind="prereg",
            stable_id=str(stable_id),
            payload=payload,
            source_path=str(p),
            source_ref="file",
        )
    ]

def index_by_id(records: Iterable[NormalizedRecord]) -> Dict[str, List[NormalizedRecord]]:
    idx: Dict[str, List[NormalizedRecord]] = {}
    for r in records:
        idx.setdefault(r.stable_id, []).append(r)
    return idx
