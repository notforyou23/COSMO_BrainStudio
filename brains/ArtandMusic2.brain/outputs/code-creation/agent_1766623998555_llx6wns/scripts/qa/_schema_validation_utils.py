from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None


MISSING_REQUIRED = "missing_required_fields"
INVALID_ENUM = "invalid_enums"
CITATION_FORMATTING = "citation_formatting"
SCHEMA_VALIDATION = "schema_validation"


@dataclass
class ValidationIssue:
    category: str
    path: str
    message: str
    validator: Optional[str] = None
    schema_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"category": self.category, "path": self.path, "message": self.message}
        if self.validator:
            d["validator"] = self.validator
        if self.schema_path:
            d["schema_path"] = self.schema_path
        return d


def _join_path(base: str, token: str) -> str:
    if base in ("", "/"):
        base = "/"
    if token.startswith("["):
        return (base if base != "/" else "") + token
    if base == "/":
        return "/" + token
    return base.rstrip("/") + "/" + token


def _schema_ptr_to_path(ptr: Iterable[Any]) -> str:
    out = ""
    for p in ptr:
        if isinstance(p, int):
            out = _join_path(out or "/", f"[{p}]")
        else:
            out = _join_path(out or "/", str(p))
    return out or "/"


def _category_for_jsonschema_error(err: Any) -> str:
    v = getattr(err, "validator", None)
    if v == "required":
        return MISSING_REQUIRED
    if v == "enum":
        return INVALID_ENUM
    return SCHEMA_VALIDATION


def validate_with_jsonschema(schema: Dict[str, Any], instance: Any) -> List[ValidationIssue]:
    if jsonschema is None:
        raise RuntimeError("jsonschema is not installed; use validate_lightweight or install jsonschema.")
    validator_cls = jsonschema.validators.validator_for(schema)  # type: ignore[attr-defined]
    validator_cls.check_schema(schema)
    v = validator_cls(schema)
    issues: List[ValidationIssue] = []
    for err in sorted(v.iter_errors(instance), key=lambda e: list(getattr(e, "path", []))):
        path = _schema_ptr_to_path(getattr(err, "path", []))
        spath = _schema_ptr_to_path(getattr(err, "schema_path", []))
        issues.append(
            ValidationIssue(
                category=_category_for_jsonschema_error(err),
                path=path,
                message=str(getattr(err, "message", str(err))),
                validator=getattr(err, "validator", None),
                schema_path=spath,
            )
        )
    return issues
def _type_ok(schema_type: Any, value: Any) -> bool:
    if schema_type is None:
        return True
    if isinstance(schema_type, list):
        return any(_type_ok(t, value) for t in schema_type)
    t = schema_type
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    return True


def _walk_schema_for_required_and_enums(schema: Any, inst: Any, path: str, out: List[ValidationIssue]) -> None:
    if not isinstance(schema, dict):
        return

    st = schema.get("type")
    if st is not None and inst is not None and not _type_ok(st, inst):
        out.append(ValidationIssue(SCHEMA_VALIDATION, path, f"type mismatch: expected {st}"))
        return

    if "enum" in schema and inst is not None:
        enum_vals = schema.get("enum", [])
        if inst not in enum_vals:
            out.append(ValidationIssue(INVALID_ENUM, path, f"value {inst!r} not in enum {enum_vals!r}", validator="enum"))

    if schema.get("type") == "object" and isinstance(inst, dict):
        req = schema.get("required") or []
        if isinstance(req, list):
            for k in req:
                if k not in inst or inst.get(k) is None:
                    out.append(ValidationIssue(MISSING_REQUIRED, _join_path(path or "/", str(k)), "missing required field", validator="required"))
        props = schema.get("properties") or {}
        if isinstance(props, dict):
            for k, subs in props.items():
                if k in inst:
                    _walk_schema_for_required_and_enums(subs, inst.get(k), _join_path(path or "/", str(k)), out)
        addl = schema.get("additionalProperties")
        if isinstance(addl, dict):
            for k, v in inst.items():
                if k not in props:
                    _walk_schema_for_required_and_enums(addl, v, _join_path(path or "/", str(k)), out)

    if schema.get("type") == "array" and isinstance(inst, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, v in enumerate(inst):
                _walk_schema_for_required_and_enums(items, v, _join_path(path or "/", f"[{i}]"), out)
        elif isinstance(items, list):
            for i, subs in enumerate(items):
                if i < len(inst):
                    _walk_schema_for_required_and_enums(subs, inst[i], _join_path(path or "/", f"[{i}]"), out)


def validate_lightweight(schema: Dict[str, Any], instance: Any) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    _walk_schema_for_required_and_enums(schema, instance, "/", issues)
    return issues
_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
_DOI_RE = re.compile(r"^(doi:)?10\.\d{4,9}/\S+$", re.IGNORECASE)
_SIMPLE_CIT_RE = re.compile(r"^[^\n]{2,200}\(\d{4}[a-z]?\)\.?\s+.+$")


def _is_citation_key(k: str) -> bool:
    lk = k.lower()
    return "citation" in lk or lk in {"references", "bibliography"}


def _lint_citation_value(val: Any, path: str, out: List[ValidationIssue]) -> None:
    def bad(msg: str) -> None:
        out.append(ValidationIssue(CITATION_FORMATTING, path, msg))

    if val is None:
        return
    if isinstance(val, str):
        s = val.strip()
        if not s:
            bad("empty citation string")
            return
        if _URL_RE.match(s) or _DOI_RE.match(s) or _SIMPLE_CIT_RE.match(s):
            return
        bad("citation string not recognized as URL, DOI, or 'Author (Year) Title' format")
        return
    if isinstance(val, dict):
        if not any(k in val for k in ("url", "doi", "text", "title")):
            bad("citation object should include one of: url, doi, text, title")
        if "url" in val and isinstance(val["url"], str) and val["url"].strip() and not _URL_RE.match(val["url"].strip()):
            out.append(ValidationIssue(CITATION_FORMATTING, _join_path(path, "url"), "invalid URL format"))
        if "doi" in val and isinstance(val["doi"], str) and val["doi"].strip() and not _DOI_RE.match(val["doi"].strip()):
            out.append(ValidationIssue(CITATION_FORMATTING, _join_path(path, "doi"), "invalid DOI format"))
        return
    if isinstance(val, list):
        for i, item in enumerate(val):
            _lint_citation_value(item, _join_path(path, f"[{i}]"), out)
        return
    bad("citations must be a string, object, or list of these")


def lint_citations(instance: Any) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    def walk(obj: Any, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                p = _join_path(path or "/", str(k))
                if isinstance(k, str) and _is_citation_key(k):
                    _lint_citation_value(v, p, issues)
                walk(v, p)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, _join_path(path or "/", f"[{i}]"))

    walk(instance, "/")
    return issues


def validate_metadata(schema: Dict[str, Any], instance: Any, use_jsonschema: bool = True) -> List[Dict[str, Any]]:
    issues: List[ValidationIssue] = []
    if use_jsonschema and jsonschema is not None:
        issues.extend(validate_with_jsonschema(schema, instance))
    else:
        issues.extend(validate_lightweight(schema, instance))
    issues.extend(lint_citations(instance))
    return [i.to_dict() for i in issues]


def summarize_issues(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for it in issues:
        c = it.get("category", SCHEMA_VALIDATION)
        counts[c] = counts.get(c, 0) + 1
    return {"total": len(issues), "by_category": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))}
