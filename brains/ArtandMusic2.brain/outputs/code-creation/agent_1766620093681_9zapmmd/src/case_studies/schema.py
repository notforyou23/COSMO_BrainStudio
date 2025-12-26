from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None


@dataclass
class ValidationIssue:
    path: str
    message: str
    validator: str = ""


class MetadataValidationError(ValueError):
    def __init__(self, issues: List[ValidationIssue], *, source: Optional[str] = None):
        self.issues = issues
        self.source = source
        super().__init__(self.__str__())

    def __str__(self) -> str:
        head = f"Metadata validation failed{f' for {self.source}' if self.source else ''}:"
        lines = [head]
        for i, it in enumerate(self.issues, 1):
            loc = it.path or "$"
            val = f" ({it.validator})" if it.validator else ""
            lines.append(f"  {i}. {loc}: {it.message}{val}")
        return "\n".join(lines)
def _find_schema_path(start: Optional[Path] = None) -> Path:
    start = (start or Path.cwd()).resolve()
    candidates: List[Path] = []
    for base in [start, *start.parents]:
        candidates.append(base / "metadata" / "METADATA_SCHEMA.json")
    # also try relative to this module
    here = Path(__file__).resolve()
    for base in [here.parent, *here.parents]:
        candidates.append(base / "metadata" / "METADATA_SCHEMA.json")
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError("Could not locate metadata/METADATA_SCHEMA.json from current directory or module path.")


def load_metadata_schema(schema_path: Optional[Path] = None) -> Dict[str, Any]:
    p = (schema_path or _find_schema_path()).resolve()
    return json.loads(p.read_text(encoding="utf-8"))


def load_metadata_file(path: Path) -> Dict[str, Any]:
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(str(p))
    suf = p.suffix.lower()
    txt = p.read_text(encoding="utf-8")
    if suf == ".json":
        data = json.loads(txt)
    elif suf in (".yml", ".yaml"):
        if yaml is None:
            raise RuntimeError("PyYAML is not available; cannot load YAML metadata.")
        data = yaml.safe_load(txt) or {}
    else:
        raise ValueError(f"Unsupported metadata file type: {p.name} (expected .json/.yml/.yaml)")
    if not isinstance(data, dict):
        raise ValueError(f"Metadata must be a JSON/YAML object at top-level: {p.name}")
    return data
def _json_path(parts: Iterable[Any]) -> str:
    out: List[str] = []
    for part in parts:
        if isinstance(part, int):
            out.append(f"[{part}]")
        else:
            s = str(part)
            if not out:
                out.append(s)
            else:
                out.append("." + s)
    return "".join(out)


def _select_case_study_subschema(schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for key in ("$defs", "definitions"):
        defs = schema.get(key)
        if isinstance(defs, dict):
            sub = defs.get("case_study") or defs.get("caseStudy") or defs.get("CaseStudy")
            if isinstance(sub, dict):
                return sub
    return None


def validate_metadata(
    metadata: Dict[str, Any],
    *,
    schema: Optional[Dict[str, Any]] = None,
    schema_path: Optional[Path] = None,
    artifact_kind: Optional[str] = None,
    source: Optional[str] = None,
) -> None:
    schema = schema or load_metadata_schema(schema_path)
    subschema = schema
    if artifact_kind == "case_study":
        sub = _select_case_study_subschema(schema)
        if sub:
            subschema = sub

    issues: List[ValidationIssue] = []
    if jsonschema is not None:
        try:
            Validator = jsonschema.Draft202012Validator  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            Validator = getattr(jsonschema, "Draft7Validator", None)
        if Validator is None:  # pragma: no cover
            raise RuntimeError("jsonschema is present but no usable validator class was found.")
        v = Validator(subschema)
        errs = sorted(v.iter_errors(metadata), key=lambda e: list(e.path))
        for e in errs:
            issues.append(ValidationIssue(_json_path(e.path), e.message, getattr(e, "validator", "") or "schema"))
    else:
        # Minimal fallback: enforce top-level required keys, if schema provides them
        req = subschema.get("required")
        if isinstance(req, list):
            for k in req:
                if k not in metadata:
                    issues.append(ValidationIssue(str(k), "is required", "required"))

    if issues:
        raise MetadataValidationError(issues, source=source)


def load_and_validate_case_study_metadata(
    path: Path,
    *,
    schema_path: Optional[Path] = None,
    schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data = load_metadata_file(path)
    validate_metadata(data, schema=schema, schema_path=schema_path, artifact_kind="case_study", source=str(path))
    return data
