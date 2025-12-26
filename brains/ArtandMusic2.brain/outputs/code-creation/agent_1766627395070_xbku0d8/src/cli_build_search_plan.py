from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except Exception as e:  # pragma: no cover
    raise SystemExit("PyYAML is required to run this tool (pip install pyyaml).") from e


def _load_yaml(path: Path) -> Dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def _dump_yaml(data: Dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _get_psv(intake: Dict[str, Any]) -> Dict[str, Any]:
    psv = intake.get("primary_source_verification")
    if psv is None or not isinstance(psv, dict):
        raise ValueError("Missing required section: primary_source_verification (mapping).")
    return psv


def _norm_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return str(x).strip() or None


def validate_primary_source_fields(psv: Dict[str, Any]) -> Dict[str, Any]:
    dataset_name = _norm_str(psv.get("dataset_name"))
    doi = _norm_str(psv.get("doi"))
    link = _norm_str(psv.get("link"))
    research_area = _norm_str(psv.get("research_area"))
    cak = psv.get("candidate_authors_or_keywords")
    if isinstance(cak, str):
        cak_list = [s.strip() for s in cak.split(",") if s.strip()]
    elif isinstance(cak, list):
        cak_list = [str(s).strip() for s in cak if str(s).strip()]
    elif cak is None:
        cak_list = []
    else:
        cak_list = [str(cak).strip()] if str(cak).strip() else []

    has_direct = any([dataset_name, doi, link])
    has_unknown_bundle = bool(research_area) and len(cak_list) > 0
    if not (has_direct or has_unknown_bundle):
        raise ValueError(
            "primary_source_verification must include at least one of "
            "dataset_name/doi/link; if unknown, provide research_area AND candidate_authors_or_keywords."
        )

    out = {
        "dataset_name": dataset_name,
        "doi": doi,
        "link": link,
        "research_area": research_area,
        "candidate_authors_or_keywords": cak_list,
    }
    if "notes" in psv:
        out["notes"] = _norm_str(psv.get("notes"))
    return out


def build_queries(psv: Dict[str, Any]) -> List[str]:
    q: List[str] = []
    if psv.get("doi"):
        q.append(f'"{psv["doi"]}"')
    if psv.get("dataset_name"):
        q.append(f'"{psv["dataset_name"]}" dataset')
        q.append(f'"{psv["dataset_name"]}" DOI')
    if psv.get("link"):
        q.append(f'site:{psv["link"].split("/")[2]}' if "://" in psv["link"] else psv["link"])
        q.append(f'"{psv["link"]}"')
    if not q:
        ra = psv.get("research_area") or ""
        cak = psv.get("candidate_authors_or_keywords") or []
        joined = " ".join([f'"{t}"' if " " in t else t for t in cak[:8]])
        base = f'{ra} {joined}'.strip()
        if base:
            q.append(base + " dataset DOI")
            q.append(base + " codebook")
            q.append(base + " repository")
    # de-dup while preserving order
    seen = set()
    out: List[str] = []
    for s in q:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def map_into_template(template: Dict[str, Any], validated: Dict[str, Any]) -> Dict[str, Any]:
    sp = dict(template)  # shallow copy
    psv_t = sp.get("primary_source_verification")
    if psv_t is None or not isinstance(psv_t, dict):
        sp["primary_source_verification"] = {}
        psv_t = sp["primary_source_verification"]

    psv_t["timeframe"] = "2019-2025"
    psv_t["required"] = True
    psv_t["inputs"] = {
        "dataset_name": validated.get("dataset_name"),
        "doi": validated.get("doi"),
        "link": validated.get("link"),
        "research_area": validated.get("research_area"),
        "candidate_authors_or_keywords": validated.get("candidate_authors_or_keywords") or [],
        "notes": validated.get("notes"),
    }
    psv_t["queries"] = build_queries(validated)
    psv_t["sources"] = psv_t.get("sources") or ["Crossref", "DataCite", "Google Scholar", "Publisher site", "Institutional repository"]
    psv_t["acceptance_criteria"] = psv_t.get("acceptance_criteria") or [
        "Primary source is located (paper/registry/repository) that defines the dataset.",
        "Dataset identity is confirmed via DOI/landing page/registry entry.",
        "Provenance and license/access conditions are recorded.",
    ]
    return sp


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build a 2019–2025 search plan from an intake checklist.")
    ap.add_argument("--intake", required=True, type=Path, help="Path to intake checklist YAML.")
    ap.add_argument("--template", type=Path, default=Path("config/search_plan_template_2019_2025.yaml"), help="Template YAML.")
    ap.add_argument("--out", required=True, type=Path, help="Output path for filled search-plan YAML.")
    args = ap.parse_args(argv)

    if not args.intake.exists():
        raise SystemExit(f"Intake file not found: {args.intake}")
    if not args.template.exists():
        raise SystemExit(f"Template file not found: {args.template}")

    intake = _load_yaml(args.intake)
    psv = _get_psv(intake)
    validated = validate_primary_source_fields(psv)
    template = _load_yaml(args.template)
    out = map_into_template(template, validated)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_dump_yaml(out), encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
