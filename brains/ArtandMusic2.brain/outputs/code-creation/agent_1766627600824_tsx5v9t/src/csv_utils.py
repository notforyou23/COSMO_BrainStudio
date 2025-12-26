from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

PathLike = Union[str, Path]


REQUIRED_COLUMNS: Tuple[str, ...] = (
    "case_id",
    "title",
    "one_line_summary",
    "organization",
    "sector",
    "country_or_region",
    "year",
    "problem",
    "approach",
    "results",
    "metrics",
    "tags",
    "data_sources",
    "evidence_links",
    "artifact_paths",
    "status",
    "owner",
    "notes",
    "created_at",
    "updated_at",
)


DEFAULT_STARTER_ROW: Dict[str, str] = {
    "case_id": "",
    "title": "",
    "one_line_summary": "",
    "organization": "",
    "sector": "",
    "country_or_region": "",
    "year": "",
    "problem": "",
    "approach": "",
    "results": "",
    "metrics": "",
    "tags": "",
    "data_sources": "",
    "evidence_links": "",
    "artifact_paths": "",
    "status": "",
    "owner": "",
    "notes": "",
    "created_at": "",
    "updated_at": "",
}


@dataclass(frozen=True)
class CSVValidationResult:
    ok: bool
    errors: Tuple[str, ...]


class CSVUtilsError(Exception):
    pass


def _to_path(p: PathLike) -> Path:
    return p if isinstance(p, Path) else Path(p)


def _dialect_kwargs() -> dict:
    # Force consistent output across platforms and preserve commas/newlines in fields.
    return {
        "delimiter": ",",
        "quotechar": '"',
        "quoting": csv.QUOTE_ALL,
        "lineterminator": "\n",
        "doublequote": True,
        "escapechar": None,
        "skipinitialspace": False,
    }
def validate_columns(
    columns: Sequence[str],
    required: Sequence[str] = REQUIRED_COLUMNS,
    allow_extra: bool = True,
) -> CSVValidationResult:
    colset = list(columns)
    errors: List[str] = []
    missing = [c for c in required if c not in colset]
    if missing:
        errors.append("Missing required columns: " + ", ".join(missing))
    if not allow_extra:
        extra = [c for c in colset if c not in required]
        if extra:
            errors.append("Unexpected extra columns: " + ", ".join(extra))
    # Ensure uniqueness and no empty names
    seen = set()
    dups = []
    for c in colset:
        if not c or not str(c).strip():
            errors.append("Empty column name encountered.")
            continue
        if c in seen:
            dups.append(c)
        seen.add(c)
    if dups:
        errors.append("Duplicate columns: " + ", ".join(sorted(set(dups))))
    return CSVValidationResult(ok=(len(errors) == 0), errors=tuple(errors))


def read_csv(
    path: PathLike,
    required: Sequence[str] = REQUIRED_COLUMNS,
    allow_extra: bool = True,
    encoding: str = "utf-8",
) -> List[Dict[str, str]]:
    p = _to_path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    with p.open("r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise CSVUtilsError(f"CSV has no header row: {p}")
        vr = validate_columns(reader.fieldnames, required=required, allow_extra=allow_extra)
        if not vr.ok:
            raise CSVUtilsError("; ".join(vr.errors))
        rows: List[Dict[str, str]] = []
        for r in reader:
            # Normalize None to "" and ensure required keys exist.
            out: Dict[str, str] = {}
            for k in reader.fieldnames:
                v = r.get(k, "")
                out[k] = "" if v is None else str(v)
            for k in required:
                out.setdefault(k, "")
            rows.append(out)
        return rows


def write_csv(
    path: PathLike,
    rows: Iterable[Mapping[str, object]],
    fieldnames: Sequence[str] = REQUIRED_COLUMNS,
    encoding: str = "utf-8",
    create_parents: bool = True,
) -> None:
    p = _to_path(path)
    if create_parents:
        p.parent.mkdir(parents=True, exist_ok=True)
    vr = validate_columns(list(fieldnames), required=REQUIRED_COLUMNS, allow_extra=True)
    if not vr.ok:
        raise CSVUtilsError("; ".join(vr.errors))
    with p.open("w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore", **_dialect_kwargs())
        writer.writeheader()
        for r in rows:
            d = {k: ("" if r.get(k) is None else str(r.get(k))) for k in fieldnames}
            writer.writerow(d)
def ensure_starter_index_csv(
    path: PathLike,
    required: Sequence[str] = REQUIRED_COLUMNS,
    write_if_missing: bool = True,
    allow_existing_extra_columns: bool = True,
    encoding: str = "utf-8",
) -> CSVValidationResult:
    p = _to_path(path)
    if not p.exists():
        if not write_if_missing:
            return CSVValidationResult(ok=False, errors=(f"Missing CSV: {p}",))
        write_csv(p, rows=[], fieldnames=list(required), encoding=encoding, create_parents=True)
        return CSVValidationResult(ok=True, errors=())
    # Validate existing file header without rewriting.
    try:
        with p.open("r", encoding=encoding, newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
    except Exception as e:
        return CSVValidationResult(ok=False, errors=(f"Failed to read CSV: {e}",))
    if header is None:
        return CSVValidationResult(ok=False, errors=(f"CSV has no header row: {p}",))
    return validate_columns(header, required=required, allow_extra=allow_existing_extra_columns)


def coerce_rows_to_required(
    rows: Iterable[Mapping[str, object]],
    required: Sequence[str] = REQUIRED_COLUMNS,
    keep_extra: bool = True,
) -> List[Dict[str, str]]:
    out_rows: List[Dict[str, str]] = []
    req = list(required)
    for r in rows:
        out: Dict[str, str] = {}
        keys = list(r.keys())
        if keep_extra:
            for k in keys:
                v = r.get(k)
                out[str(k)] = "" if v is None else str(v)
        for k in req:
            v = r.get(k)
            out[k] = "" if v is None else str(v)
        out_rows.append(out)
    return out_rows


def default_starter_row(required: Sequence[str] = REQUIRED_COLUMNS) -> Dict[str, str]:
    # Returns a blank row with all required columns, useful for UI/testing.
    return {k: DEFAULT_STARTER_ROW.get(k, "") for k in required}
