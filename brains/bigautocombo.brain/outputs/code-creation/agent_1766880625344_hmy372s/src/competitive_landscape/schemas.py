from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re


SUPPLIER_TYPES = {"kit_supplier", "integrator", "oem_program", "software", "service", "other", "unknown"}
PRICING_BANDS = {"low", "mid", "premium", "enterprise", "unknown"}
COMPLIANCE_POSTURES = {"strong", "partial", "weak", "unknown"}


def _s(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, str):
        return val.strip()
    return str(val).strip()


def _slug_choice(val: Any, allowed: set, default: str = "unknown") -> str:
    s = _s(val).lower()
    s = re.sub(r"[^a-z0-9_\-\s]+", "", s).replace("-", "_")
    s = re.sub(r"\s+", "_", s).strip("_")
    return s if s in allowed else default


def _list(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [x for x in (_s(v) for v in val) if x]
    if isinstance(val, (tuple, set)):
        return [x for x in (_s(v) for v in val) if x]
    s = _s(val)
    if not s:
        return []
    parts = re.split(r"[,;\n\t]+", s)
    return [p.strip() for p in parts if p.strip()]


def _int(val: Any) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    s = _s(val)
    if not s:
        return None
    m = re.search(r"-?\d+", s)
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None


def normalize_supplier_type(val: Any) -> str:
    s = _s(val).lower()
    if s in {"kit", "kit supplier", "kitsupplier"}:
        return "kit_supplier"
    if s in {"integrator", "installer", "partner"}:
        return "integrator"
    if s in {"oem", "oem program", "oem_program"}:
        return "oem_program"
    if s in {"software", "platform", "saas"}:
        return "software"
    if s in {"service", "services", "consulting"}:
        return "service"
    return _slug_choice(s, SUPPLIER_TYPES, "unknown")


def normalize_pricing_band(val: Any) -> str:
    s = _s(val).lower()
    if s in {"budget", "value", "entry", "low"}:
        return "low"
    if s in {"mid", "mid-market", "midmarket", "standard"}:
        return "mid"
    if s in {"premium", "high", "pro"}:
        return "premium"
    if s in {"enterprise", "ent"}:
        return "enterprise"
    return _slug_choice(s, PRICING_BANDS, "unknown")


def normalize_compliance_posture(val: Any) -> str:
    s = _s(val).lower()
    if s in {"strong", "high", "mature"}:
        return "strong"
    if s in {"partial", "mixed", "some"}:
        return "partial"
    if s in {"weak", "low", "immature"}:
        return "weak"
    return _slug_choice(s, COMPLIANCE_POSTURES, "unknown")


@dataclass
class CompetitiveRecord:
    name: str = ""
    supplier_type: str = "unknown"  # kit_supplier | integrator | oem_program | software | service | other | unknown
    website: str = ""
    regions: List[str] = field(default_factory=list)

    pricing_band: str = "unknown"  # low | mid | premium | enterprise | unknown
    pricing_notes: str = ""

    warranty_months: Optional[int] = None
    warranty_terms: str = ""

    compliance_posture: str = "unknown"  # strong | partial | weak | unknown
    compliance_standards: List[str] = field(default_factory=list)  # e.g., UL, CE, FCC, ISO27001, SOC2, GDPR
    compliance_notes: str = ""

    differentiation: List[str] = field(default_factory=list)
    differentiation_gaps: List[str] = field(default_factory=list)

    notes: str = ""
    source: str = ""
    last_verified: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Dict[str, Any]) -> "CompetitiveRecord":
        d = data or {}
        return cls(
            name=_s(d.get("name")),
            supplier_type=normalize_supplier_type(d.get("supplier_type")),
            website=_s(d.get("website")),
            regions=_list(d.get("regions")),
            pricing_band=normalize_pricing_band(d.get("pricing_band")),
            pricing_notes=_s(d.get("pricing_notes")),
            warranty_months=_int(d.get("warranty_months")),
            warranty_terms=_s(d.get("warranty_terms")),
            compliance_posture=normalize_compliance_posture(d.get("compliance_posture")),
            compliance_standards=_list(d.get("compliance_standards")),
            compliance_notes=_s(d.get("compliance_notes")),
            differentiation=_list(d.get("differentiation")),
            differentiation_gaps=_list(d.get("differentiation_gaps")),
            notes=_s(d.get("notes")),
            source=_s(d.get("source")),
            last_verified=_s(d.get("last_verified")),
        )


def validate_record(rec: CompetitiveRecord) -> Tuple[CompetitiveRecord, List[str]]:
    errors: List[str] = []
    rec.name = _s(rec.name)
    if not rec.name:
        errors.append("name: required")

    rec.supplier_type = normalize_supplier_type(rec.supplier_type)
    if rec.supplier_type not in SUPPLIER_TYPES:
        errors.append("supplier_type: invalid")

    rec.pricing_band = normalize_pricing_band(rec.pricing_band)
    rec.compliance_posture = normalize_compliance_posture(rec.compliance_posture)

    rec.website = _s(rec.website)
    rec.pricing_notes = _s(rec.pricing_notes)
    rec.warranty_terms = _s(rec.warranty_terms)
    rec.compliance_notes = _s(rec.compliance_notes)
    rec.notes = _s(rec.notes)
    rec.source = _s(rec.source)
    rec.last_verified = _s(rec.last_verified)

    rec.regions = _list(rec.regions)
    rec.compliance_standards = _list(rec.compliance_standards)
    rec.differentiation = _list(rec.differentiation)
    rec.differentiation_gaps = _list(rec.differentiation_gaps)

    if rec.warranty_months is not None and rec.warranty_months < 0:
        errors.append("warranty_months: must be >= 0 or null")
        rec.warranty_months = None

    return rec, errors


def coerce_records(rows: Iterable[Dict[str, Any]]) -> Tuple[List[CompetitiveRecord], List[str]]:
    out: List[CompetitiveRecord] = []
    errs: List[str] = []
    for i, row in enumerate(rows or []):
        rec = CompetitiveRecord.from_mapping(row)
        rec, e = validate_record(rec)
        out.append(rec)
        for msg in e:
            errs.append(f"row[{i}]: {msg}")
    return out, errs
