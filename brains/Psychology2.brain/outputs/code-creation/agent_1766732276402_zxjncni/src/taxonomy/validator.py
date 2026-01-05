from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import csv, json

@dataclass
class ValidationError:
    row: int
    field: str
    code: str
    message: str

def _is_missing(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")

def _as_str(v: Any) -> Optional[str]:
    if _is_missing(v):
        return None
    return v if isinstance(v, str) else str(v)

def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def _iter_jsonl(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            yield i, json.loads(s)

def _iter_csv(path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # header is row 1
            yield i, dict(row)

class Validator:
    """Row validator for taxonomy annotations against a schema dict.

    Expected schema keys:
      - required_fields: [str,...]
      - fields: {name: {type?, allowed?, required?, nullable?, min?, max?}}
      - conditional_required: [{if:{field:value|[values]}, require:[fields]}]
    """
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema or {}
        self.fields = self.schema.get("fields", {}) or {}
        self.required = list(self.schema.get("required_fields", []) or [])
        self.cond = list(self.schema.get("conditional_required", []) or [])
        self._init_default_rules()

    @classmethod
    def from_schema_path(cls, schema_path: Path) -> "Validator":
        return cls(_read_json(schema_path))

    def _init_default_rules(self) -> None:
        # Ensure the mission-critical rule exists even if absent in schema.
        if not any(r.get("if", {}).get("outcome_type") == "tangible" for r in self.cond):
            self.cond.append({"if": {"outcome_type": "tangible"}, "require": ["stake_magnitude"]})

    def validate_row(self, row: Dict[str, Any], row_index: int = 1) -> List[ValidationError]:
        errs: List[ValidationError] = []
        # Required fields
        for k in self.required:
            if _is_missing(row.get(k)):
                errs.append(ValidationError(row_index, k, "missing_required", f"Missing required field '{k}'"))
        # Field-level checks
        for name, spec in self.fields.items():
            v = row.get(name)
            if _is_missing(v):
                if spec.get("required") and not spec.get("nullable", False):
                    errs.append(ValidationError(row_index, name, "missing_required", f"Missing required field '{name}'"))
                continue
            # Type checks
            t = spec.get("type")
            if t:
                if t == "string" and not isinstance(v, str):
                    row[name] = str(v)
                    v = row[name]
                elif t == "integer":
                    try:
                        row[name] = int(v)
                        v = row[name]
                    except Exception:
                        errs.append(ValidationError(row_index, name, "type", f"Expected integer for '{name}'"))
                        continue
                elif t == "number":
                    try:
                        row[name] = float(v)
                        v = row[name]
                    except Exception:
                        errs.append(ValidationError(row_index, name, "type", f"Expected number for '{name}'"))
                        continue
                elif t == "boolean":
                    if isinstance(v, str):
                        s = v.strip().lower()
                        if s in ("true", "1", "yes", "y"): row[name] = True
                        elif s in ("false", "0", "no", "n"): row[name] = False
                        else:
                            errs.append(ValidationError(row_index, name, "type", f"Expected boolean for '{name}'"))
                            continue
                        v = row[name]
                    elif not isinstance(v, bool):
                        errs.append(ValidationError(row_index, name, "type", f"Expected boolean for '{name}'"))
                        continue
            # Allowed values (enums)
            allowed = spec.get("allowed")
            if allowed is not None:
                sv = v if not isinstance(v, str) else v.strip()
                if sv not in allowed:
                    errs.append(ValidationError(row_index, name, "allowed", f"Value '{sv}' not in allowed set for '{name}'"))
            # Numeric bounds
            if isinstance(v, (int, float)):
                if spec.get("min") is not None and v < spec["min"]:
                    errs.append(ValidationError(row_index, name, "min", f"Value {v} < min {spec['min']} for '{name}'"))
                if spec.get("max") is not None and v > spec["max"]:
                    errs.append(ValidationError(row_index, name, "max", f"Value {v} > max {spec['max']} for '{name}'"))
        # Conditional required rules
        for rule in self.cond:
            cond = rule.get("if", {}) or {}
            req = list(rule.get("require", []) or [])
            if self._cond_matches(row, cond):
                for k in req:
                    if _is_missing(row.get(k)):
                        errs.append(ValidationError(row_index, k, "missing_conditional", f"Field '{k}' required when {cond}"))
        return errs

    def _cond_matches(self, row: Dict[str, Any], cond: Dict[str, Any]) -> bool:
        for k, expected in cond.items():
            actual = row.get(k)
            if isinstance(expected, list):
                if _as_str(actual) not in [str(x) for x in expected]:
                    return False
            else:
                if _as_str(actual) != str(expected):
                    return False
        return True

    def validate_rows(self, rows: Iterable[Tuple[int, Dict[str, Any]]]) -> List[ValidationError]:
        all_errs: List[ValidationError] = []
        for i, row in rows:
            if not isinstance(row, dict):
                all_errs.append(ValidationError(i, "", "type", "Row is not an object/dict"))
                continue
            all_errs.extend(self.validate_row(row, i))
        return all_errs

    def validate_file(self, path: Path) -> Dict[str, Any]:
        suf = path.suffix.lower()
        if suf == ".jsonl":
            rows = _iter_jsonl(path)
        elif suf == ".csv":
            rows = _iter_csv(path)
        elif suf == ".json":
            data = _read_json(path)
            if isinstance(data, list):
                rows = ((i, r) for i, r in enumerate(data, start=1))
            else:
                rows = ((1, data),)
        else:
            raise ValueError(f"Unsupported file type: {suf}")
        errors = self.validate_rows(rows)
        return {
            "path": str(path),
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "errors": [e.__dict__ for e in errors],
        }
