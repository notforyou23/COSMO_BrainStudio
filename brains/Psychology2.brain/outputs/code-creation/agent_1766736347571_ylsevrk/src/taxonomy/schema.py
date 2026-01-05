from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union
import json


SchemaDict = Dict[str, Any]


def default_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "outputs" / "taxonomy" / "annotation_schema_v0.1.json"


@lru_cache(maxsize=8)
def load_schema(path: Optional[Union[str, Path]] = None) -> SchemaDict:
    p = Path(path) if path is not None else default_schema_path()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Schema root must be a JSON object.")
    return data


def fields(schema: Mapping[str, Any]) -> Mapping[str, Any]:
    f = schema.get("fields")
    if not isinstance(f, dict):
        raise ValueError("Schema missing object 'fields'.")
    return f


def field_names(schema: Mapping[str, Any]) -> List[str]:
    return list(fields(schema).keys())


def field_spec(schema: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    spec = fields(schema).get(name)
    if not isinstance(spec, dict):
        raise KeyError(f"Unknown field: {name}")
    return spec


def is_required(schema: Mapping[str, Any], name: str) -> bool:
    return bool(field_spec(schema, name).get("required", False))


def base_required_fields(schema: Mapping[str, Any]) -> Set[str]:
    return {n for n in field_names(schema) if is_required(schema, n)}


def allowed_values(schema: Mapping[str, Any], name: str) -> Optional[Set[Any]]:
    spec = field_spec(schema, name)
    vals = spec.get("allowed_values", spec.get("enum"))
    if vals is None:
        return None
    if not isinstance(vals, list):
        raise ValueError(f"allowed_values/enum for {name} must be a list.")
    return set(vals)


def type_name(schema: Mapping[str, Any], name: str) -> Optional[str]:
    t = field_spec(schema, name).get("type")
    return t if isinstance(t, str) else None


def conditional_rules(schema: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    rules = schema.get("conditional_requirements", [])
    if rules is None:
        return []
    if not isinstance(rules, list):
        raise ValueError("conditional_requirements must be a list.")
    out: List[Mapping[str, Any]] = []
    for r in rules:
        if not isinstance(r, dict):
            raise ValueError("Each conditional rule must be an object.")
        out.append(r)
    return out


def _truthy(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str) and v.strip() == "":
        return False
    return True


def eval_condition(cond: Any, row: Mapping[str, Any]) -> bool:
    if cond is None:
        return True
    if isinstance(cond, dict):
        if "all" in cond:
            seq = cond["all"]
            if not isinstance(seq, list):
                raise ValueError("Condition 'all' must be a list.")
            return all(eval_condition(c, row) for c in seq)
        if "any" in cond:
            seq = cond["any"]
            if not isinstance(seq, list):
                raise ValueError("Condition 'any' must be a list.")
            return any(eval_condition(c, row) for c in seq)
        field = cond.get("field")
        if not isinstance(field, str) or not field:
            raise ValueError("Atomic condition requires non-empty 'field'.")
        val = row.get(field)
        if "equals" in cond:
            return val == cond["equals"]
        if "not_equals" in cond:
            return val != cond["not_equals"]
        if "in" in cond:
            seq = cond["in"]
            if not isinstance(seq, list):
                raise ValueError("Condition 'in' must be a list.")
            return val in seq
        if "not_in" in cond:
            seq = cond["not_in"]
            if not isinstance(seq, list):
                raise ValueError("Condition 'not_in' must be a list.")
            return val not in seq
        if "exists" in cond:
            want = bool(cond["exists"])
            return _truthy(val) if want else (not _truthy(val))
        raise ValueError("Unknown atomic condition operator.")
    raise ValueError("Condition must be an object (or use all/any).")


def required_fields_for_row(schema: Mapping[str, Any], row: Mapping[str, Any]) -> Set[str]:
    req = set(base_required_fields(schema))
    for rule in conditional_rules(schema):
        cond = rule.get("if", rule.get("condition"))
        if eval_condition(cond, row):
            rf = rule.get("require_fields", rule.get("require"))
            if rf is None:
                continue
            if not isinstance(rf, list) or not all(isinstance(x, str) and x for x in rf):
                raise ValueError("Conditional rule require_fields/require must be a list of strings.")
            req.update(rf)
    return req


def forbidden_fields_for_row(schema: Mapping[str, Any], row: Mapping[str, Any]) -> Set[str]:
    forb: Set[str] = set()
    for rule in conditional_rules(schema):
        cond = rule.get("if", rule.get("condition"))
        if eval_condition(cond, row):
            ff = rule.get("forbid_fields", rule.get("forbid"))
            if ff is None:
                continue
            if not isinstance(ff, list) or not all(isinstance(x, str) and x for x in ff):
                raise ValueError("Conditional rule forbid_fields/forbid must be a list of strings.")
            forb.update(ff)
    return forb
