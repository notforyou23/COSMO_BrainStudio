"""Metadata checklist templates + risk-weighted validation rules for primary-source scholarship."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Issue:
    code: str
    field: str
    severity: str  # info|warn|error
    risk: int
    message: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "field": self.field,
            "severity": self.severity,
            "risk": self.risk,
            "message": self.message,
        }


@dataclass(frozen=True)
class FieldSpec:
    key: str
    required: bool = False
    risk_missing: int = 0
    description: str = ""
    allowed: Optional[Sequence[str]] = None


def _norm_key(k: str) -> str:
    return k.strip()


def _get(d: Mapping[str, Any], k: str) -> Any:
    return d.get(k)


def _present(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str) and not v.strip():
        return False
    if isinstance(v, (list, tuple, set, dict)) and len(v) == 0:
        return False
    return True


def _is_url(s: str) -> bool:
    s = (s or "").strip().lower()
    return s.startswith("http://") or s.startswith("https://")
TEMPLATES: Dict[str, Dict[str, Any]] = {
    "primary_source_psychology": {
        "title": "Primary source (psychology) – edition/translation provenance",
        "version": 1,
        "fields": [
            FieldSpec("work_title", required=True, risk_missing=15, description="Canonical work title."),
            FieldSpec("work_author", required=True, risk_missing=15, description="Author(s) of the original work."),
            FieldSpec("original_publication_year", required=True, risk_missing=10),
            FieldSpec("edition_title", required=True, risk_missing=10, description="The specific edition used."),
            FieldSpec("edition_year", required=True, risk_missing=12),
            FieldSpec("publisher", required=True, risk_missing=10),
            FieldSpec("place_of_publication", required=False, risk_missing=0),
            FieldSpec("language_of_source", required=True, risk_missing=8),
            FieldSpec("is_translation", required=True, risk_missing=8, allowed=["yes", "no"]),
            FieldSpec("translator", required=False, risk_missing=10),
            FieldSpec("translation_year", required=False, risk_missing=8),
            FieldSpec("translation_notes", required=False),
            FieldSpec("editor", required=False),
            FieldSpec("isbn", required=False),
            FieldSpec("oclc", required=False),
            FieldSpec("doi", required=False),
            FieldSpec("source_type", required=True, risk_missing=6, allowed=["print", "scan", "born_digital"]),
            FieldSpec("access_url", required=False),
            FieldSpec("archive", required=False, description="Repository/collection name for scans/archives."),
            FieldSpec("accessed_date", required=False),
            FieldSpec("public_domain_status", required=True, risk_missing=10, allowed=["pd", "in_copyright", "unknown"]),
            FieldSpec("public_domain_rationale", required=False, risk_missing=6),
            FieldSpec("citation_style", required=False, allowed=["apa", "chicago", "mla", "other"]),
            FieldSpec("citation_text", required=True, risk_missing=12, description="Full citation for the edition/translation used."),
            FieldSpec("page_system", required=True, risk_missing=12, allowed=["original", "edition", "both", "n_a"]),
            FieldSpec("variant_pagination_mapping", required=False, risk_missing=10, description="How original pages map to edition pages."),
            FieldSpec("quoted_passages", required=False, description="List of quoted passages with page refs."),
            FieldSpec("provenance_notes", required=False),
        ],
    }
}


def list_templates() -> List[str]:
    return sorted(TEMPLATES.keys())


def get_template(name: str) -> Dict[str, Any]:
    if name not in TEMPLATES:
        raise KeyError(f"Unknown checklist template: {name}")
    return TEMPLATES[name]
def _allowed_issue(field: str, allowed: Sequence[str], value: Any) -> Optional[Issue]:
    if not _present(value):
        return None
    if not isinstance(value, str):
        return Issue("type", field, "warn", 2, f"Expected a string from {list(allowed)}.")
    v = value.strip()
    if v not in allowed:
        return Issue("allowed", field, "error", 6, f"Value '{v}' not in allowed set {list(allowed)}.")
    return None


def validate_metadata(metadata: Mapping[str, Any], template: str = "primary_source_psychology") -> Dict[str, Any]:
    t = get_template(template)
    fields: List[FieldSpec] = list(t["fields"])
    issues: List[Issue] = []

    # Normalize keys (non-destructive): handle accidental whitespace keys
    md: Dict[str, Any] = { _norm_key(k): v for k, v in dict(metadata).items() }

    for fs in fields:
        v = _get(md, fs.key)
        if fs.required and not _present(v):
            issues.append(Issue("missing", fs.key, "error", fs.risk_missing, f"Required field '{fs.key}' is missing/empty."))
        if fs.allowed:
            iss = _allowed_issue(fs.key, fs.allowed, v)
            if iss:
                issues.append(iss)

    # Cross-field, risk-weighted rules (workflow safety)
    is_translation = str(_get(md, "is_translation") or "").strip()
    if is_translation == "yes":
        if not _present(_get(md, "translator")):
            issues.append(Issue("missing_translation", "translator", "error", 12, "Translation indicated but translator is missing."))
        if not _present(_get(md, "translation_year")):
            issues.append(Issue("missing_translation_year", "translation_year", "warn", 6, "Translation indicated but translation_year is missing."))
    if is_translation == "no" and _present(_get(md, "translator")):
        issues.append(Issue("unexpected_translator", "translator", "warn", 3, "Translator provided but is_translation='no'."))

    source_type = str(_get(md, "source_type") or "").strip()
    if source_type in ("scan", "born_digital"):
        if not (_present(_get(md, "access_url")) or _present(_get(md, "archive"))):
            issues.append(Issue("missing_access", "access_url", "warn", 6, "Digital/scan sources should include access_url or archive."))
        if _present(_get(md, "access_url")) and not _is_url(str(_get(md, "access_url"))):
            issues.append(Issue("bad_url", "access_url", "warn", 3, "access_url does not look like an http(s) URL."))

    pd = str(_get(md, "public_domain_status") or "").strip()
    if pd in ("pd", "unknown") and not _present(_get(md, "public_domain_rationale")):
        issues.append(Issue("missing_pd_rationale", "public_domain_rationale", "warn", 5, "Provide public_domain_rationale for pd/unknown status."))

    page_system = str(_get(md, "page_system") or "").strip()
    if page_system == "both" and not _present(_get(md, "variant_pagination_mapping")):
        issues.append(Issue("missing_pagination_map", "variant_pagination_mapping", "warn", 7, "page_system='both' requires variant_pagination_mapping."))

    # Heuristic: citation should mention edition_year or edition_title to reduce provenance ambiguity
    citation = str(_get(md, "citation_text") or "")
    if _present(citation) and _present(_get(md, "edition_year")):
        ey = str(_get(md, "edition_year"))
        if ey.isdigit() and ey not in citation:
            issues.append(Issue("citation_ambiguous", "citation_text", "warn", 4, "citation_text does not appear to include edition_year."))

    risk_total = sum(i.risk for i in issues)
    severity_max = "info"
    if any(i.severity == "error" for i in issues):
        severity_max = "error"
    elif any(i.severity == "warn" for i in issues):
        severity_max = "warn"

    return {
        "template": template,
        "issues": [i.as_dict() for i in issues],
        "risk_total": int(risk_total),
        "severity": severity_max,
        "valid": severity_max != "error",
    }


def checklist_schema(template: str = "primary_source_psychology") -> Dict[str, Any]:
    t = get_template(template)
    out_fields = []
    for fs in t["fields"]:
        out_fields.append(
            {
                "key": fs.key,
                "required": fs.required,
                "risk_missing": fs.risk_missing,
                "description": fs.description,
                "allowed": list(fs.allowed) if fs.allowed else None,
            }
        )
    return {"template": template, "title": t.get("title"), "version": t.get("version"), "fields": out_fields}
