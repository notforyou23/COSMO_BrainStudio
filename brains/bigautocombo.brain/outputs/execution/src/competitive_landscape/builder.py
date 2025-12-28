from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import csv, json, re
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

def _s(x: Any) -> str:
    return "" if x is None else str(x).strip()

def _norm_key(x: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _s(x).lower()).strip("_")

def _coalesce(*vals: Any) -> str:
    for v in vals:
        t = _s(v)
        if t:
            return t
    return ""

def _parse_int(x: Any) -> Optional[int]:
    t = _s(x)
    if not t:
        return None
    m = re.search(r"(-?\d+)", t)
    return int(m.group(1)) if m else None

def _parse_money(x: Any) -> Optional[float]:
    t = _s(x).replace(",", "")
    if not t:
        return None
    m = re.search(r"(-?\d+(?:\.\d+)?)", t)
    return float(m.group(1)) if m else None

def _pricing_band(price_usd: Optional[float], raw: str = "") -> str:
    r = _s(raw).lower()
    for k in ("low", "mid", "medium", "high", "enterprise", "premium", "budget"):
        if k in r:
            return {"medium":"mid","premium":"enterprise","budget":"low"}.get(k, k)
    if price_usd is None:
        return "unknown"
    if price_usd < 500:
        return "low"
    if price_usd < 2000:
        return "mid"
    if price_usd < 8000:
        return "high"
    return "enterprise"

def _norm_supplier_type(x: str) -> str:
    t = _s(x).lower()
    if any(k in t for k in ("kit", "supplier", "hardware", "bundl")):
        return "kit_supplier"
    if any(k in t for k in ("integrator", "installer", "service", "deployment", "si")):
        return "integrator"
    if any(k in t for k in ("oem", "program", "manufacturer", "brand")):
        return "oem"
    return "unknown"

def _norm_compliance(x: str) -> str:
    t = _s(x).lower()
    if not t:
        return "unknown"
    if any(k in t for k in ("cert", "compliant", "soc", "iso", "ul", "ce", "fcc", "rohs", "reach", "gdpr", "hipaa")):
        return "compliant"
    if any(k in t for k in ("partial", "in progress", "roadmap", "planned", "self attest")):
        return "partial"
    if any(k in t for k in ("no", "none", "unknown", "n/a")):
        return "unknown"
    if any(k in t for k in ("noncompliant", "not compliant", "violat")):
        return "noncompliant"
    return "partial" if len(t) > 0 else "unknown"

@dataclass
class CompetitiveRecord:
    name: str
    supplier_type: str = "unknown"
    region: str = ""
    pricing_text: str = ""
    pricing_usd: Optional[float] = None
    pricing_band: str = "unknown"
    warranty_months: Optional[int] = None
    warranty_terms: str = ""
    compliance_posture: str = "unknown"
    compliance_notes: str = ""
    differentiation_notes: str = ""
    sources: str = ""

def load_competitors(path: Path) -> List[Dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    if path.suffix.lower() in (".json",):
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix.lower() in (".yaml", ".yml"):
        if yaml is None:
            raise RuntimeError("PyYAML not available for YAML input")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else (data.get("competitors") or [])
    # csv
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]

def apply_overrides(records: List[Dict[str, Any]], overrides_path: Optional[Path]) -> List[Dict[str, Any]]:
    if not overrides_path:
        return records
    p = Path(overrides_path)
    if not p.exists():
        return records
    if p.suffix.lower() in (".json",):
        ov = json.loads(p.read_text(encoding="utf-8"))
    else:
        if yaml is None:
            return records
        ov = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not ov:
        return records
    edits = ov.get("edit", {}) if isinstance(ov, dict) else {}
    adds = ov.get("add", []) if isinstance(ov, dict) else []
    out: List[Dict[str, Any]] = []
    for r in records:
        name = _coalesce(r.get("name"), r.get("competitor"), r.get("vendor"))
        key = _norm_key(name)
        if key in edits and isinstance(edits[key], dict):
            rr = dict(r); rr.update(edits[key]); out.append(rr)
        else:
            out.append(r)
    if isinstance(adds, list):
        out.extend([a for a in adds if isinstance(a, dict)])
    return out

def normalize_record(raw: Dict[str, Any]) -> CompetitiveRecord:
    name = _coalesce(raw.get("name"), raw.get("competitor"), raw.get("vendor"), raw.get("company"))
    st = _coalesce(raw.get("supplier_type"), raw.get("type"), raw.get("category"))
    price_text = _coalesce(raw.get("pricing"), raw.get("price"), raw.get("msrp"), raw.get("pricing_text"))
    price_usd = _parse_money(_coalesce(raw.get("pricing_usd"), raw.get("price_usd"))) or _parse_money(price_text)
    band = _pricing_band(price_usd, price_text or _s(raw.get("pricing_band")))
    w_terms = _coalesce(raw.get("warranty_terms"), raw.get("warranty"), raw.get("warranty_text"))
    w_m = _parse_int(_coalesce(raw.get("warranty_months"), raw.get("warranty_mo"))) or _parse_int(w_terms)
    comp = _coalesce(raw.get("compliance_posture"), raw.get("compliance"), raw.get("security"), raw.get("certifications"))
    return CompetitiveRecord(
        name=name or "Unknown",
        supplier_type=_norm_supplier_type(st),
        region=_coalesce(raw.get("region"), raw.get("geo"), raw.get("market")),
        pricing_text=price_text,
        pricing_usd=price_usd,
        pricing_band=_coalesce(_s(raw.get("pricing_band")), band) or band,
        warranty_months=w_m,
        warranty_terms=w_terms,
        compliance_posture=_norm_compliance(comp),
        compliance_notes=_coalesce(raw.get("compliance_notes"), raw.get("cert_notes"), raw.get("security_notes")),
        differentiation_notes=_coalesce(raw.get("differentiation"), raw.get("notes"), raw.get("differentiation_notes")),
        sources=_coalesce(raw.get("source"), raw.get("sources"), raw.get("url")),
    )

def score_opportunities(r: CompetitiveRecord) -> Tuple[int, List[str]]:
    score = 0
    opp: List[str] = []
    if r.compliance_posture in ("unknown", "partial"):
        score += 2; opp.append("Lead with stronger compliance/certifications and clearer attestations")
    if r.warranty_months is None or (r.warranty_months is not None and r.warranty_months < 12):
        score += 2; opp.append("Offer longer/clearer warranty and streamlined RMA terms")
    if r.pricing_band in ("unknown",):
        score += 1; opp.append("Provide transparent pricing tiers and configurator")
    if r.supplier_type in ("kit_supplier", "oem") and "install" not in r.differentiation_notes.lower():
        score += 1; opp.append("Bundle services: install, commissioning, training, support SLAs")
    if r.supplier_type in ("integrator",) and ("kit" not in r.differentiation_notes.lower() and "hardware" not in r.differentiation_notes.lower()):
        score += 1; opp.append("Differentiate with pre-certified kits/BOM standardization and faster lead times")
    return score, opp

def build_matrix(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for raw in records:
        r = normalize_record(raw)
        score, opp = score_opportunities(r)
        d = asdict(r)
        d["opportunity_score"] = score
        d["differentiation_opportunities"] = "; ".join(opp)
        out.append(d)
    out.sort(key=lambda x: (-int(x.get("opportunity_score") or 0), _s(x.get("name")).lower()))
    return out

def write_matrix_excel_or_csv(rows: List[Dict[str, Any]], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["name","supplier_type","region","pricing_band","pricing_usd","pricing_text","warranty_months","warranty_terms",
            "compliance_posture","compliance_notes","opportunity_score","differentiation_opportunities","differentiation_notes","sources"]
    if out_path.suffix.lower() == ".xlsx":
        try:
            from openpyxl import Workbook  # type: ignore
            wb, ws = Workbook(), Workbook().active
        except Exception:
            # fallback to csv
            return write_matrix_excel_or_csv(rows, out_path.with_suffix(".csv"))
        ws.title = "competitive_map"
        ws.append(cols)
        for r in rows:
            ws.append([r.get(c, "") for c in cols])
        for i, c in enumerate(cols, 1):
            ws.column_dimensions[chr(64+i)].width = min(45, max(12, len(c)+2))
        wb = ws.parent
        wb.save(out_path)
        return out_path
    # csv
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})
    return out_path

def write_summary_md(rows: List[Dict[str, Any]], out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(rows)
    by_type: Dict[str,int] = {}
    by_band: Dict[str,int] = {}
    by_comp: Dict[str,int] = {}
    for r in rows:
        by_type[r.get("supplier_type","unknown")] = by_type.get(r.get("supplier_type","unknown"), 0) + 1
        by_band[r.get("pricing_band","unknown")] = by_band.get(r.get("pricing_band","unknown"), 0) + 1
        by_comp[r.get("compliance_posture","unknown")] = by_comp.get(r.get("compliance_posture","unknown"), 0) + 1
    top = rows[:8]
    lines = []
    lines.append("# Competitive Landscape Summary")
    lines.append("")
    lines.append(f"- Total competitors: **{total}**")
    lines.append(f"- Supplier types: " + ", ".join(f"**{k}**={v}" for k,v in sorted(by_type.items(), key=lambda x:(-x[1], x[0]))))
    lines.append(f"- Pricing bands: " + ", ".join(f"**{k}**={v}" for k,v in sorted(by_band.items(), key=lambda x:(-x[1], x[0]))))
    lines.append(f"- Compliance posture: " + ", ".join(f"**{k}**={v}" for k,v in sorted(by_comp.items(), key=lambda x:(-x[1], x[0]))))
    lines.append("")
    lines.append("## Highest-leverage differentiation opportunities (top scored)")
    lines.append("")
    for r in top:
        lines.append(f"- **{r.get('name','')}** ({r.get('supplier_type','')}, {r.get('pricing_band','')}): score={r.get('opportunity_score',0)}")
        opp = _s(r.get("differentiation_opportunities"))
        if opp:
            lines.append(f"  - {opp}")
    lines.append("")
    lines.append("## Cross-market opportunity themes")
    lines.append("")
    theme_counts: Dict[str,int] = {}
    for r in rows:
        for t in [x.strip() for x in _s(r.get("differentiation_opportunities")).split(";") if x.strip()]:
            theme_counts[t] = theme_counts.get(t, 0) + 1
    for t, c in sorted(theme_counts.items(), key=lambda x:(-x[1], x[0]))[:8]:
        lines.append(f"- {t} (seen in {c}/{total})")
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path

def build_competitive_outputs(seed_path: Path, out_matrix_path: Path, out_summary_path: Path, overrides_path: Optional[Path] = None) -> Tuple[Path, Path]:
    recs = load_competitors(Path(seed_path))
    recs = apply_overrides(recs, overrides_path)
    rows = build_matrix(recs)
    matrix_written = write_matrix_excel_or_csv(rows, Path(out_matrix_path))
    summary_written = write_summary_md(rows, Path(out_summary_path))
    return matrix_written, summary_written
