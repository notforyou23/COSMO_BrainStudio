#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


MISSING = object()


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    return False


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_rows(path: Path, fmt: str) -> Iterable[Tuple[int, Dict[str, Any]]]:
    if fmt == "auto":
        suffix = path.suffix.lower()
        fmt = "jsonl" if suffix in {".jsonl", ".jl"} else ("csv" if suffix == ".csv" else "")
    if fmt not in {"jsonl", "csv"}:
        raise SystemExit(f"Unsupported format for {path.name!r}. Use --format jsonl|csv.")
    if fmt == "jsonl":
        with path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception as e:
                    yield i, {"__parse_error__": f"Invalid JSON: {e}"}
                    continue
                if not isinstance(obj, dict):
                    yield i, {"__parse_error__": "JSONL row must be an object/dict"}
                    continue
                yield i, obj
    else:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return
            for i, row in enumerate(reader, start=2):  # header is line 1
                yield i, dict(row)


def _coerce_type(val: Any, t: str) -> Tuple[Any, Optional[str]]:
    if _is_missing(val):
        return val, None
    if t == "string":
        return str(val), None
    if t == "integer":
        if isinstance(val, int) and not isinstance(val, bool):
            return val, None
        if isinstance(val, float) and val.is_integer():
            return int(val), None
        if isinstance(val, str):
            s = val.strip()
            try:
                return int(s), None
            except Exception:
                return val, "expected integer"
        return val, "expected integer"
    if t == "number":
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val), None
        if isinstance(val, str):
            s = val.strip()
            try:
                return float(s), None
            except Exception:
                return val, "expected number"
        return val, "expected number"
    if t == "boolean":
        if isinstance(val, bool):
            return val, None
        if isinstance(val, str):
            s = val.strip().lower()
            if s in {"true", "t", "1", "yes", "y"}:
                return True, None
            if s in {"false", "f", "0", "no", "n"}:
                return False, None
        return val, "expected boolean"
    if t == "array":
        if isinstance(val, list):
            return val, None
        if isinstance(val, str):
            s = val.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    v = json.loads(s)
                    return (v, None) if isinstance(v, list) else (val, "expected array")
                except Exception:
                    return val, "expected array"
            if s == "":
                return [], None
            return [p.strip() for p in s.split("|") if p.strip()], None
        return val, "expected array"
    if t == "object":
        if isinstance(val, dict):
            return val, None
        if isinstance(val, str):
            s = val.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    v = json.loads(s)
                    return (v, None) if isinstance(v, dict) else (val, "expected object")
                except Exception:
                    return val, "expected object"
        return val, "expected object"
    return val, None


@dataclass
class FieldSpec:
    name: str
    type: str = "string"
    required: bool = False
    allowed: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


def _parse_schema(schema: Dict[str, Any]) -> Tuple[Dict[str, FieldSpec], List[Dict[str, Any]]]:
    fields: Dict[str, FieldSpec] = {}
    required = set(schema.get("required_fields") or [])
    for k, v in (schema.get("fields") or {}).items():
        if not isinstance(v, dict):
            v = {}
        fields[k] = FieldSpec(
            name=k,
            type=str(v.get("type") or "string"),
            required=bool(v.get("required")) or (k in required),
            allowed=list(v.get("allowed")) if isinstance(v.get("allowed"), list) else None,
            min_value=v.get("min"),
            max_value=v.get("max"),
        )
    for k in required:
        fields.setdefault(k, FieldSpec(name=k, required=True))
    cond = schema.get("conditional_required") or schema.get("conditional_requirements") or []
    if not isinstance(cond, list):
        cond = []
    return fields, cond


def _check_condition(row: Dict[str, Any], cond: Dict[str, Any]) -> bool:
    f = cond.get("field")
    if not f:
        return False
    v = row.get(f, MISSING)
    if v is MISSING:
        return False
    if "equals" in cond:
        return v == cond.get("equals")
    if "in" in cond and isinstance(cond.get("in"), list):
        return v in cond.get("in")
    if "not_equals" in cond:
        return v != cond.get("not_equals")
    return False


def validate_rows(rows: Iterable[Tuple[int, Dict[str, Any]]], schema: Dict[str, Any]) -> Dict[str, Any]:
    fields, cond = _parse_schema(schema)
    out: Dict[str, Any] = {
        "summary": {
            "total_rows": 0,
            "valid_rows": 0,
            "invalid_rows": 0,
            "error_count": 0,
            "errors_by_field": {},
            "errors_by_code": {},
        },
        "row_errors": [],
    }

    def add_err(row_no: int, field: str, code: str, msg: str, row_id: Any = None):
        out["summary"]["error_count"] += 1
        out["summary"]["errors_by_field"][field] = out["summary"]["errors_by_field"].get(field, 0) + 1
        out["summary"]["errors_by_code"][code] = out["summary"]["errors_by_code"].get(code, 0) + 1
        out["row_errors"].append({"row": row_no, "id": row_id, "field": field, "code": code, "message": msg})

    for row_no, row in rows:
        out["summary"]["total_rows"] += 1
        row_id = row.get("annotation_id") if isinstance(row, dict) else None
        row_ok = True

        if "__parse_error__" in row:
            add_err(row_no, "__row__", "parse_error", row["__parse_error__"], row_id=row_id)
            row_ok = False
        else:
            # Required fields
            for fs in fields.values():
                if fs.required and _is_missing(row.get(fs.name, None)):
                    add_err(row_no, fs.name, "missing_required", "missing required field", row_id=row_id)
                    row_ok = False

            # Type + allowed + min/max
            for name, fs in fields.items():
                if name not in row:
                    continue
                v0 = row.get(name)
                v, type_err = _coerce_type(v0, fs.type)
                row[name] = v
                if type_err:
                    add_err(row_no, name, "type_mismatch", type_err, row_id=row_id)
                    row_ok = False
                    continue
                if fs.allowed is not None and not _is_missing(v) and v not in fs.allowed:
                    add_err(row_no, name, "invalid_value", f"value {v!r} not in allowed set", row_id=row_id)
                    row_ok = False
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if fs.min_value is not None and v < fs.min_value:
                        add_err(row_no, name, "below_min", f"value {v} < min {fs.min_value}", row_id=row_id)
                        row_ok = False
                    if fs.max_value is not None and v > fs.max_value:
                        add_err(row_no, name, "above_max", f"value {v} > max {fs.max_value}", row_id=row_id)
                        row_ok = False

            # Conditional requirements
            for rule in cond:
                if not isinstance(rule, dict):
                    continue
                ifc = rule.get("if") or rule.get("when") or rule.get("condition") or {}
                th = rule.get("then_require") or rule.get("require") or rule.get("then") or []
                if isinstance(th, str):
                    th = [th]
                if not (isinstance(ifc, dict) and isinstance(th, list) and th):
                    continue
                if _check_condition(row, ifc):
                    for req in th:
                        if _is_missing(row.get(req, None)):
                            add_err(row_no, req, "missing_conditional", f"required when {ifc.get('field')} condition holds", row_id=row_id)
                            row_ok = False

        if row_ok:
            out["summary"]["valid_rows"] += 1
        else:
            out["summary"]["invalid_rows"] += 1

    return out


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="taxonomy-validate", description="Validate taxonomy annotation files (JSONL/CSV).")
    p.add_argument("annotations", type=str, help="Path to annotation file (.jsonl/.csv)")
    p.add_argument("--schema", type=str, default="outputs/taxonomy/annotation_schema_v0.1.json", help="Path to schema JSON")
    p.add_argument("--format", type=str, default="auto", choices=["auto", "jsonl", "csv"], help="Input format")
    p.add_argument("--report", type=str, default="", help="Write full JSON report to this path")
    p.add_argument("--max-errors", type=int, default=50, help="Max row-level errors to print")
    args = p.parse_args(argv)

    ann_path = Path(args.annotations)
    schema_path = Path(args.schema)
    if not ann_path.exists():
        print(f"ERROR: annotation file not found: {ann_path}", file=sys.stderr)
        return 2
    if not schema_path.exists():
        print(f"ERROR: schema file not found: {schema_path}", file=sys.stderr)
        return 2

    schema = _load_json(schema_path)
    report = validate_rows(_iter_rows(ann_path, args.format), schema)

    s = report["summary"]
    print(f"ROWS total={s['total_rows']} valid={s['valid_rows']} invalid={s['invalid_rows']} errors={s['error_count']}")
    if s["error_count"]:
        for e in report["row_errors"][: max(0, args.max_errors)]:
            rid = f" id={e['id']!r}" if e.get("id") not in (None, "") else ""
            print(f"ERR row={e['row']}{rid} field={e['field']} code={e['code']}: {e['message']}")
        if len(report["row_errors"]) > args.max_errors:
            print(f"... ({len(report['row_errors']) - args.max_errors} more errors not shown)")

    if args.report:
        outp = Path(args.report)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return 0 if s["invalid_rows"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
