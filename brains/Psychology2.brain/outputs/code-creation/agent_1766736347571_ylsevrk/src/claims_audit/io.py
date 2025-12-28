"""claims_audit.io

JSONL I/O utilities with stable record envelopes + schema/version fields.

This module is intentionally lightweight and dependency-free; it operates on
plain dict records and can wrap/unwrap common record types used by the project.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Union

SCHEMA_VERSION = "1.0"
ENCODING = "utf-8"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_plain(obj: Any) -> Any:
    if obj is None:
        return None
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "model_dump"):  # pydantic v2
        return obj.model_dump()
    if hasattr(obj, "dict"):  # pydantic v1
        return obj.dict()
    return obj


def _jsonable(obj: Any) -> Any:
    obj = _to_plain(obj)
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return obj.replace(microsecond=0).isoformat()
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return str(obj)


def envelope(
    record_type: str,
    payload: Dict[str, Any],
    *,
    schema_version: str = SCHEMA_VERSION,
    created_at: Optional[str] = None,
    tool: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Wrap a payload in a stable envelope used for JSONL persistence."""
    env = {
        "schema_version": schema_version,
        "record_type": record_type,
        "created_at": created_at or _now_iso(),
        "payload": payload,
    }
    if tool is not None:
        env["tool"] = tool
    return env


def write_jsonl(path: Union[str, Path], records: Iterable[Dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding=ENCODING) as f:
        for rec in records:
            f.write(json.dumps(_jsonable(rec), ensure_ascii=False, sort_keys=True))
            f.write("\n")


def append_jsonl(path: Union[str, Path], records: Iterable[Dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding=ENCODING) as f:
        for rec in records:
            f.write(json.dumps(_jsonable(rec), ensure_ascii=False, sort_keys=True))
            f.write("\n")


def read_jsonl(path: Union[str, Path]) -> Iterator[Dict[str, Any]]:
    p = Path(path)
    with p.open("r", encoding=ENCODING) as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            yield json.loads(s)


def unwrap_envelopes(
    records: Iterable[Dict[str, Any]],
    *,
    record_type: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield payloads from envelope records; optionally filter by record_type."""
    for rec in records:
        if "payload" in rec and "record_type" in rec:
            if record_type is None or rec.get("record_type") == record_type:
                yield rec["payload"]
        else:
            if record_type is None:
                yield rec


def write_claims_jsonl(
    path: Union[str, Path],
    claims: Iterable[Union[Dict[str, Any], Any]],
    *,
    tool: Optional[Dict[str, Any]] = None,
    schema_version: str = SCHEMA_VERSION,
) -> None:
    recs = (envelope("atomic_claim", _to_plain(c), schema_version=schema_version, tool=tool) for c in claims)
    write_jsonl(path, recs)


def write_audits_jsonl(
    path: Union[str, Path],
    audits: Iterable[Union[Dict[str, Any], Any]],
    *,
    tool: Optional[Dict[str, Any]] = None,
    schema_version: str = SCHEMA_VERSION,
) -> None:
    recs = (envelope("claim_audit", _to_plain(a), schema_version=schema_version, tool=tool) for a in audits)
    write_jsonl(path, recs)


def write_metrics_jsonl(
    path: Union[str, Path],
    reports: Iterable[Union[Dict[str, Any], Any]],
    *,
    tool: Optional[Dict[str, Any]] = None,
    schema_version: str = SCHEMA_VERSION,
) -> None:
    recs = (envelope("metric_report", _to_plain(r), schema_version=schema_version, tool=tool) for r in reports)
    write_jsonl(path, recs)


def read_claims_jsonl(path: Union[str, Path]) -> List[Dict[str, Any]]:
    return list(unwrap_envelopes(read_jsonl(path), record_type="atomic_claim"))


def read_audits_jsonl(path: Union[str, Path]) -> List[Dict[str, Any]]:
    return list(unwrap_envelopes(read_jsonl(path), record_type="claim_audit"))


def read_metrics_jsonl(path: Union[str, Path]) -> List[Dict[str, Any]]:
    return list(unwrap_envelopes(read_jsonl(path), record_type="metric_report"))
