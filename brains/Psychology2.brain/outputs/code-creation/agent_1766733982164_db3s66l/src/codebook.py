import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


class CodebookError(ValueError):
    pass


def _parse_version(v: Any) -> Tuple[int, ...]:
    if v is None:
        return ()
    if isinstance(v, (tuple, list)) and all(isinstance(x, int) for x in v):
        return tuple(v)
    if not isinstance(v, str):
        raise CodebookError(f"Invalid version type: {type(v).__name__}")
    m = re.fullmatch(r"\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\s*", v)
    if not m:
        raise CodebookError(f"Invalid version string: {v!r}")
    return tuple(int(x) for x in m.groups() if x is not None)


def _type_ok(spec_type: str, v: Any) -> bool:
    t = spec_type.lower()
    if t in ("str", "string"):
        return isinstance(v, str)
    if t in ("int", "integer"):
        return isinstance(v, int) and not isinstance(v, bool)
    if t in ("num", "number"):
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t in ("bool", "boolean"):
        return isinstance(v, bool)
    if t in ("arr", "array", "list"):
        return isinstance(v, list)
    if t in ("obj", "object", "dict"):
        return isinstance(v, dict)
    return True


@dataclass(frozen=True)
class Violation:
    path: str
    message: str
    code: str = "constraint_violation"

    def as_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "message": self.message, "code": self.code}


class Codebook:
    def __init__(self, data: Dict[str, Any], *, path: Optional[Path] = None):
        if not isinstance(data, dict):
            raise CodebookError("Codebook must be a JSON object")
        self.data = data
        self.path = path
        self.codebook_version = _parse_version(data.get("codebook_version") or data.get("version"))
        ann = data.get("annotation") or {}
        if not isinstance(ann, dict):
            raise CodebookError("codebook.annotation must be an object")
        self.annotation = ann
        self.compatible_annotation_versions = [
            _parse_version(v) for v in (ann.get("compatible_versions") or ann.get("compatible_annotation_versions") or [])
        ]
        cats = data.get("categories") or {}
        if not isinstance(cats, dict):
            raise CodebookError("codebook.categories must be an object")
        self.categories = cats
        fields = ann.get("fields") or {}
        if not isinstance(fields, dict):
            raise CodebookError("codebook.annotation.fields must be an object")
        self.fields = fields
        req = ann.get("required_fields") or []
        if not isinstance(req, list) or not all(isinstance(x, str) for x in req):
            raise CodebookError("codebook.annotation.required_fields must be a list of strings")
        self.required_fields = req
        self.cross_field_rules = ann.get("cross_field_rules") or []
        if not isinstance(self.cross_field_rules, list):
            raise CodebookError("codebook.annotation.cross_field_rules must be a list")

    @classmethod
    def load(cls, path: Any) -> "Codebook":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(data, path=p)

    def check_compatibility(self, annotation_version: Optional[Any]) -> None:
        if annotation_version is None or not self.compatible_annotation_versions:
            return
        av = _parse_version(annotation_version)
        if av not in self.compatible_annotation_versions:
            want = ", ".join(".".join(map(str, v)) for v in self.compatible_annotation_versions)
            got = ".".join(map(str, av)) if av else str(annotation_version)
            raise CodebookError(f"Annotation version {got} not compatible with codebook; allowed: {want}")

    def _category_values(self, name: str) -> Iterable[Any]:
        cat = self.categories.get(name)
        if not isinstance(cat, dict):
            raise CodebookError(f"Unknown category: {name}")
        vals = cat.get("values")
        if isinstance(vals, list):
            return vals
        if isinstance(vals, dict):
            return vals.keys()
        raise CodebookError(f"Category {name} must define 'values' as list or object")

    def validate_record(self, rec: Any, *, annotation_version: Optional[Any] = None) -> List[Dict[str, Any]]:
        self.check_compatibility(annotation_version)
        viols: List[Violation] = []
        if not isinstance(rec, dict):
            return [Violation(path="", message="Record must be a JSON object", code="type").as_dict()]

        for f in self.required_fields:
            if f not in rec or rec.get(f) in (None, ""):
                viols.append(Violation(path=f, message="Missing required field", code="required"))

        for f, spec in self.fields.items():
            if f not in rec:
                continue
            v = rec.get(f)
            if v is None:
                continue
            if not isinstance(spec, dict):
                raise CodebookError(f"Field spec for {f} must be an object")
            st = spec.get("type")
            if isinstance(st, str) and not _type_ok(st, v):
                viols.append(Violation(path=f, message=f"Expected type {st}", code="type"))
                continue
            allowed = spec.get("allowed_values")
            if isinstance(allowed, list) and v not in allowed:
                viols.append(Violation(path=f, message="Value not in allowed_values", code="enum"))
            cat = spec.get("category")
            if isinstance(cat, str):
                if v not in set(self._category_values(cat)):
                    viols.append(Violation(path=f, message=f"Value not in category {cat}", code="category"))

        viols.extend(self._apply_cross_field_rules(rec))
        return [x.as_dict() for x in viols]

    def _apply_cross_field_rules(self, rec: Dict[str, Any]) -> List[Violation]:
        out: List[Violation] = []
        for i, rule in enumerate(self.cross_field_rules):
            if not isinstance(rule, dict):
                raise CodebookError("Each cross_field_rule must be an object")
            cond = rule.get("if") or {}
            then = rule.get("then") or {}
            if not isinstance(cond, dict) or not isinstance(then, dict):
                raise CodebookError("cross_field_rule.if and .then must be objects")
            field = cond.get("field")
            if not isinstance(field, str):
                raise CodebookError("cross_field_rule.if.field must be a string")
            if field not in rec:
                continue
            v = rec.get(field)
            ok = True
            if "equals" in cond:
                ok = v == cond.get("equals")
            if "in" in cond:
                vals = cond.get("in")
                if not isinstance(vals, list):
                    raise CodebookError("cross_field_rule.if.in must be a list")
                ok = v in vals
            if not ok:
                continue

            for rf in then.get("required", []) or []:
                if rf not in rec or rec.get(rf) in (None, ""):
                    out.append(Violation(path=rf, message=f"Required when {field} condition holds", code="required_if"))
            for ff in then.get("forbid", []) or []:
                if ff in rec and rec.get(ff) not in (None, ""):
                    out.append(Violation(path=ff, message=f"Forbidden when {field} condition holds", code="forbidden_if"))
            fields = then.get("fields") or {}
            if fields and not isinstance(fields, dict):
                raise CodebookError("cross_field_rule.then.fields must be an object")
            for tf, tspec in fields.items():
                if tf not in rec:
                    continue
                if not isinstance(tspec, dict):
                    raise CodebookError("cross_field_rule.then.fields.<field> must be an object")
                if "in" in tspec:
                    vals = tspec.get("in")
                    if not isinstance(vals, list):
                        raise CodebookError("cross_field_rule.then.fields.<field>.in must be a list")
                    if rec.get(tf) not in vals:
                        out.append(Violation(path=tf, message="Value violates conditional allowed set", code="enum_if"))
            _ = i
        return out
