from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class IntakeValidationError(Exception):
    errors: List[str]
    def __str__(self) -> str:
        return "\n".join(self.errors)

def _is_blank(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (list, tuple, set, dict)):
        return len(v) == 0
    return False

def _get(d: Any, path: str, default: Any = None) -> Any:
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

def _as_str(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ("" if v is None else str(v).strip())

def _find_dataset_verification_selected(data: Dict[str, Any]) -> bool:
    def has_token(x: str) -> bool:
        s = x.lower().replace("_", "-").strip()
        return ("dataset" in s and ("verification" in s or "verify" in s)) or s in {
            "dataset-verification", "dataset_verification", "datasetverification"
        }
    # Common boolean flags
    for k in ("dataset_verification", "datasetVerification", "pilot_dataset_verification"):
        if bool(data.get(k)) is True:
            return True
    # Common list containers
    for k in ("pilots", "pilot_claims", "verification_pilots", "selected_pilots", "pilotClaims"):
        v = data.get(k)
        if isinstance(v, list) and any(isinstance(it, str) and has_token(it) for it in v):
            return True
        if isinstance(v, dict):
            # e.g. {"dataset_verification": true}
            for kk, vv in v.items():
                if bool(vv) is True and isinstance(kk, str) and has_token(kk):
                    return True
    # Search nested known locations
    for p in ("intake.pilots", "intake.pilot_claims", "request.pilots", "request.pilot_claims"):
        v = _get(data, p)
        if isinstance(v, list) and any(isinstance(it, str) and has_token(it) for it in v):
            return True
    return False

def _extract_dataset_identifier(data: Dict[str, Any]) -> Tuple[str, str]:
    ds = data.get("dataset")
    name = doi_or_link = ""
    if isinstance(ds, dict):
        name = _as_str(ds.get("name") or ds.get("dataset_name") or ds.get("title"))
        doi_or_link = _as_str(ds.get("doi") or ds.get("link") or ds.get("url") or ds.get("identifier"))
    # top-level fallbacks
    if not name:
        name = _as_str(data.get("dataset_name") or data.get("datasetName") or data.get("dataset_title"))
    if not doi_or_link:
        doi_or_link = _as_str(data.get("dataset_doi") or data.get("dataset_link") or data.get("dataset_url") or data.get("dataset_identifier"))
    # nested fallbacks
    if not name:
        name = _as_str(_get(data, "intake.dataset.name") or _get(data, "request.dataset.name"))
    if not doi_or_link:
        doi_or_link = _as_str(_get(data, "intake.dataset.doi") or _get(data, "intake.dataset.link") or _get(data, "request.dataset.doi") or _get(data, "request.dataset.link"))
    return name, doi_or_link

def _only_research_area_provided(data: Dict[str, Any]) -> bool:
    research_area = _as_str(data.get("research_area") or data.get("researchArea") or _get(data, "intake.research_area") or _get(data, "request.research_area"))
    if not research_area:
        return False
    # Any additional substantive detail should unblock.
    specific_fields = [
        "claim","question","research_question","problem_statement","objective","objectives","hypothesis",
        "summary","task","analysis_request","deliverables","success_criteria","inputs","data","sources",
        "citations","context","constraints","methods","methodology","evaluation","acceptance_criteria"
    ]
    for k in specific_fields:
        v = data.get(k)
        if not _is_blank(v):
            return False
        v = _get(data, f"intake.{k}")
        if not _is_blank(v):
            return False
        v = _get(data, f"request.{k}")
        if not _is_blank(v):
            return False
    # If there is any non-research-area free text under common description keys, also unblock.
    for k in ("description", "details", "notes"):
        for p in (k, f"intake.{k}", f"request.{k}"):
            v = _as_str(_get(data, p))
            if v and v.strip().lower() != research_area.strip().lower():
                return False
    return True

def _validate_against_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    try:
        import jsonschema  # type: ignore
    except Exception:
        return []
    try:
        jsonschema.Draft202012Validator(schema).validate(data)
        return []
    except Exception as e:
        msg = getattr(e, "message", None) or str(e)
        path = ".".join(str(x) for x in getattr(e, "path", []))
        return [f"Schema validation error{(' at ' + path) if path else ''}: {msg}"]

def validate_intake(data: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> List[str]:
    errors: List[str] = []
    if schema:
        errors.extend(_validate_against_schema(data, schema))

    if _only_research_area_provided(data):
        errors.append("Blocked: intake provides only a vague research area; add a concrete claim/question/objective and relevant details.")

    if _find_dataset_verification_selected(data):
        name, doi_or_link = _extract_dataset_identifier(data)
        if not name or not doi_or_link:
            errors.append("Blocked: dataset-verification pilot selected but missing required dataset identifier (dataset name AND DOI/link).")

    return errors

def validate_intake_path(intake_path: Path, schema_path: Optional[Path] = None) -> None:
    data = json.loads(intake_path.read_text(encoding="utf-8"))
    schema = None
    if schema_path and schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errs = validate_intake(data, schema=schema)
    if errs:
        raise IntakeValidationError(errs)
