"""CSV template/schema handling + robust loading/validation for study-level effects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import csv
import math


DEFAULT_SCHEMA: Dict[str, Dict[str, str]] = {
    "study_id": {"type": "str", "required": "true", "desc": "Study identifier"},
    "yi": {"type": "float", "required": "true", "desc": "Effect estimate (e.g., log RR, SMD)"},
    "vi": {"type": "float", "required": "false", "desc": "Sampling variance of yi (>=0)"},
    "sei": {"type": "float", "required": "false", "desc": "Standard error of yi (>=0); alternative to vi"},
    "label": {"type": "str", "required": "false", "desc": "Optional descriptive label"},
}


@dataclass(frozen=True)
class ValidationResult:
    rows: List[Dict[str, object]]
    errors: List[str]
    warnings: List[str]


def schema() -> Dict[str, Dict[str, str]]:
    return {k: dict(v) for k, v in DEFAULT_SCHEMA.items()}
def template_rows(n: int = 3) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for i in range(1, n + 1):
        rows.append(
            {
                "study_id": f"study_{i}",
                "yi": "",
                "vi": "",
                "sei": "",
                "label": "",
            }
        )
    return rows


def write_template_csv(path: str | Path, n: int = 3, overwrite: bool = False) -> Path:
    p = Path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(f"Template already exists: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(DEFAULT_SCHEMA.keys())
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in template_rows(n=n):
            w.writerow(r)
    return p


def write_schema_json(path: str | Path, overwrite: bool = False) -> Path:
    p = Path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(f"Schema already exists: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p
def _as_float(x: object) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        v = float(x)
        return None if math.isnan(v) else v
    s = str(x).strip()
    if s == "" or s.lower() in {"na", "nan", "null", "none"}:
        return None
    try:
        v = float(s)
        return None if math.isnan(v) else v
    except ValueError:
        return None


def _norm_key(s: str) -> str:
    return s.strip().lstrip("﻿")


def _read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            return [], []
        fields = [_norm_key(c) for c in r.fieldnames]
        out: List[Dict[str, str]] = []
        for row in r:
            out.append({k: (row.get(orig) if (orig := k) else "") for k in fields})
        return fields, out
def load_effects_csv(
    path: str | Path,
    required: Sequence[str] = ("study_id", "yi"),
    allow_extra_cols: bool = True,
    drop_invalid: bool = True,
) -> ValidationResult:
    p = Path(path)
    fields, raw_rows = _read_csv_rows(p)
    errors: List[str] = []
    warnings: List[str] = []

    if not fields:
        errors.append(f"{p}: empty or unreadable CSV (missing header).")
        return ValidationResult(rows=[], errors=errors, warnings=warnings)

    missing = [c for c in required if c not in fields]
    if missing:
        errors.append(f"{p}: missing required columns: {missing}")
        return ValidationResult(rows=[], errors=errors, warnings=warnings)

    known = set(DEFAULT_SCHEMA.keys())
    extra = [c for c in fields if c not in known]
    if extra and not allow_extra_cols:
        errors.append(f"{p}: unexpected columns present: {extra}")
        return ValidationResult(rows=[], errors=errors, warnings=warnings)
    if extra:
        warnings.append(f"{p}: ignoring extra columns: {extra}")

    out: List[Dict[str, object]] = []
    for i, row in enumerate(raw_rows, start=2):
        sid = (row.get("study_id") or "").strip()
        yi = _as_float(row.get("yi"))
        vi = _as_float(row.get("vi"))
        sei = _as_float(row.get("sei"))
        label = (row.get("label") or "").strip() or None

        row_errs: List[str] = []
        if not sid:
            row_errs.append("study_id is blank")
        if yi is None:
            row_errs.append("yi is missing/non-numeric")

        if vi is None and sei is None:
            row_errs.append("provide vi or sei")
        if vi is not None and vi < 0:
            row_errs.append("vi must be >= 0")
        if sei is not None and sei < 0:
            row_errs.append("sei must be >= 0")

        if vi is None and sei is not None:
            vi = sei * sei
        if sei is None and vi is not None:
            sei = math.sqrt(vi) if vi >= 0 else None

        if row_errs:
            msg = f"{p}:{i}: " + "; ".join(row_errs)
            if drop_invalid:
                warnings.append("dropped invalid row: " + msg)
                continue
            errors.append(msg)
            continue

        out.append({"study_id": sid, "yi": float(yi), "vi": float(vi), "sei": float(sei), "label": label})

    if not out and not errors:
        warnings.append(f"{p}: no valid rows found.")
    return ValidationResult(rows=out, errors=errors, warnings=warnings)


__all__ = [
    "DEFAULT_SCHEMA",
    "ValidationResult",
    "schema",
    "template_rows",
    "write_template_csv",
    "write_schema_json",
    "load_effects_csv",
]
