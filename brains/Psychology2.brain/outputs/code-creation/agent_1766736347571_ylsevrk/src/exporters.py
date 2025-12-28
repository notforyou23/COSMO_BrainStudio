from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

PROVENANCE_FIELDS: Tuple[str, ...] = (
    "landing_url",
    "accessed_at",
    "parsing_method",
    "failure_reason_code",
)

BASE_FIELD_ORDER: Tuple[str, ...] = (
    "doi",
    "doi_normalized",
    "source",
    "title",
    "subtitle",
    "container_title",
    "publisher",
    "published_year",
    "published_date",
    "type",
    "language",
    "volume",
    "issue",
    "page",
    "article_number",
    "issn",
    "isbn",
    "url",
    "author",
    "editor",
    "abstract",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_provenance(record: Dict[str, Any], accessed_at: Optional[str] = None) -> Dict[str, Any]:
    if accessed_at is None:
        accessed_at = utc_now_iso()
    for k in PROVENANCE_FIELDS:
        record.setdefault(k, None)
    record.setdefault("accessed_at", accessed_at)
    return record


def _stable_columns(records: Sequence[Mapping[str, Any]]) -> List[str]:
    seen = set()
    cols: List[str] = []
    for k in BASE_FIELD_ORDER + PROVENANCE_FIELDS:
        if k not in seen:
            cols.append(k)
            seen.add(k)
    extra_keys = sorted({k for r in records for k in r.keys()} - seen)
    cols.extend(extra_keys)
    return cols


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):  # pydantic v2
        return obj.model_dump()
    if hasattr(obj, "dict"):  # pydantic v1
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, default=_json_default, sort_keys=True) + "\n")


def write_json(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, default=_json_default, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = _stable_columns(records)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in records:
            row: Dict[str, Any] = {}
            for k in cols:
                v = r.get(k, None)
                if isinstance(v, (dict, list, tuple)):
                    row[k] = json.dumps(v, ensure_ascii=False, default=_json_default, sort_keys=True)
                else:
                    row[k] = v
            w.writerow(row)


def write_run_logs(path: Path, log_records: Iterable[Mapping[str, Any]]) -> None:
    # Writes structured logs as JSONL (one object per line).
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in log_records:
            f.write(json.dumps(r, ensure_ascii=False, default=_json_default, sort_keys=True) + "\n")


@dataclass(frozen=True)
class ExportPaths:
    artifacts_dir: Path
    records_jsonl: Path
    records_json: Path
    records_csv: Path
    logs_jsonl: Path


def default_export_paths(artifacts_dir: Path, run_id: str) -> ExportPaths:
    ad = Path(artifacts_dir) / run_id
    return ExportPaths(
        artifacts_dir=ad,
        records_jsonl=ad / "records.jsonl",
        records_json=ad / "records.json",
        records_csv=ad / "records.csv",
        logs_jsonl=ad / "logs.jsonl",
    )


def export_run(
    records: Sequence[Mapping[str, Any]],
    run_id: str,
    artifacts_dir: Path,
    log_records: Optional[Iterable[Mapping[str, Any]]] = None,
    accessed_at: Optional[str] = None,
) -> ExportPaths:
    paths = default_export_paths(artifacts_dir, run_id)
    normalized: List[Dict[str, Any]] = [ensure_provenance(dict(r), accessed_at=accessed_at) for r in records]
    write_jsonl(paths.records_jsonl, normalized)
    write_json(paths.records_json, normalized)
    write_csv(paths.records_csv, normalized)
    if log_records is not None:
        write_run_logs(paths.logs_jsonl, log_records)
    return paths
