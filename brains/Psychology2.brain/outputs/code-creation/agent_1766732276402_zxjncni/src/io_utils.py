from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import io
import json
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union


JsonObj = Dict[str, Any]
Record = Dict[str, Any]


def _read_text(path: Union[str, Path], encoding: str = "utf-8") -> str:
    p = Path(path)
    data = p.read_bytes()
    # Handle UTF-8 BOM if present
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.decode(encoding, errors="replace")


def _maybe_parse_json_scalar(s: str) -> Any:
    t = s.strip()
    if t == "":
        return None
    if t.lower() in {"null", "none"}:
        return None
    if t.lower() == "true":
        return True
    if t.lower() == "false":
        return False
    # Numbers (avoid parsing IDs like 001)
    if t.replace(".", "", 1).isdigit() and not (t.startswith("0") and len(t) > 1 and "." not in t):
        try:
            return int(t) if "." not in t else float(t)
        except Exception:
            return s
    if (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]")):
        try:
            return json.loads(t)
        except Exception:
            return s
    return s


def normalize_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        return _maybe_parse_json_scalar(v)
    if isinstance(v, (int, float, bool)):
        return v
    if isinstance(v, list):
        return [normalize_value(x) for x in v]
    if isinstance(v, dict):
        return {str(k).strip(): normalize_value(val) for k, val in v.items()}
    return v


def normalize_record(rec: Any) -> Record:
    if not isinstance(rec, dict):
        raise ValueError(f"Record must be an object/dict, got: {type(rec).__name__}")
    out: Record = {}
    for k, v in rec.items():
        if k is None:
            continue
        ks = str(k).strip()
        if ks == "":
            continue
        out[ks] = normalize_value(v)
    return out


def normalize_records(recs: Iterable[Any]) -> List[Record]:
    return [normalize_record(r) for r in recs]
def read_json(path: Union[str, Path]) -> Any:
    return json.loads(_read_text(path))


def read_json_records(path: Union[str, Path]) -> List[Record]:
    obj = read_json(path)
    if isinstance(obj, list):
        return normalize_records(obj)
    if isinstance(obj, dict):
        return [normalize_record(obj)]
    raise ValueError("JSON must be an object or an array of objects.")


def iter_jsonl_records(path: Union[str, Path]) -> Iterator[Record]:
    text = _read_text(path)
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            raise ValueError(f"Invalid JSONL at line {i}: {e}") from e
        yield normalize_record(obj)


def read_csv_records(path: Union[str, Path]) -> List[Record]:
    text = _read_text(path)
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if reader.fieldnames is None:
        return []
    records: List[Record] = []
    for row in reader:
        # csv.DictReader can include None key for extra columns; ignore them
        clean = {k: v for k, v in row.items() if k is not None}
        records.append(normalize_record(clean))
    return records


def load_records(path: Union[str, Path], fmt: Optional[str] = None) -> List[Record]:
    p = Path(path)
    use = (fmt or p.suffix.lstrip(".")).lower()
    if use in {"json"}:
        return read_json_records(p)
    if use in {"jsonl", "ndjson"}:
        return list(iter_jsonl_records(p))
    if use in {"csv"}:
        return read_csv_records(p)
    raise ValueError(f"Unsupported format '{use}'. Expected one of: json, jsonl, csv.")
def write_json(path: Union[str, Path], obj: Any, indent: int = 2) -> None:
    p = Path(path)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def write_jsonl(path: Union[str, Path], records: Iterable[Dict[str, Any]]) -> None:
    p = Path(path)
    lines = []
    for r in records:
        lines.append(json.dumps(r, ensure_ascii=False))
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
