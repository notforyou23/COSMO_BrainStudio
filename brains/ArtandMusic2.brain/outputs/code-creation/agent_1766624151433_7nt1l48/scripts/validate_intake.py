#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
def _iter_items(obj: Any) -> Iterable[Tuple[Optional[str], Any]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k), v
            yield from _iter_items(v)
    elif isinstance(obj, list):
        for v in obj:
            yield None, v
            yield from _iter_items(v)
def _truthy(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return x != 0
    if isinstance(x, str):
        return x.strip().lower() in {"true", "yes", "y", "1", "enabled", "on", "selected"}
    return bool(x)
def _is_dataset_verification_selected(data: Any) -> bool:
    if isinstance(data, dict):
        pc = data.get("pilot_claims") or data.get("pilotClaims")
        if isinstance(pc, list):
            for item in pc:
                if isinstance(item, str) and ("dataset" in item.lower() and "verif" in item.lower()):
                    return True

        claims = data.get("claims")
        if isinstance(claims, dict):
            for k, v in claims.items():
                lk = str(k).lower()
                if "dataset" in lk and "verif" in lk and _truthy(v):
                    return True

        dv = data.get("dataset_verification") or data.get("datasetVerification")
        if isinstance(dv, dict):
            for k in ("selected", "enabled", "active", "on"):
                if k in dv and _truthy(dv.get(k)):
                    return True
            if _truthy(dv.get("value")):
                return True
        if _truthy(data.get("dataset_verification_pilot")) or _truthy(data.get("datasetVerificationPilot")):
            return True

    for k, v in _iter_items(data):
        if k is None:
            continue
        lk = k.lower()
        if "dataset" in lk and "verif" in lk and _truthy(v):
            return True
    return False
def _extract_dataset_entries(data: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    def add_candidate(x: Any) -> None:
        if isinstance(x, dict):
            out.append(x)

    if isinstance(data, dict):
        for key in ("dataset", "dataset_identifier", "datasetIdentifier", "dataset_info", "datasetInfo"):
            add_candidate(data.get(key))
        ds = data.get("datasets")
        if isinstance(ds, list):
            for item in ds:
                add_candidate(item)

    for k, v in _iter_items(data):
        if k is None:
            continue
        lk = k.lower()
        if lk in {"dataset", "dataset_identifier", "datasetidentifier", "dataset_info", "datasetinfo"}:
            add_candidate(v)
        elif lk == "datasets" and isinstance(v, list):
            for item in v:
                add_candidate(item)

    return [d for d in out if isinstance(d, dict)]
def _get_str(d: Dict[str, Any], keys: Iterable[str]) -> str:
    for k in keys:
        if k in d and isinstance(d.get(k), str) and d.get(k).strip():
            return d.get(k).strip()
    return 
def _has_dataset_identifier(data: Any) -> bool:
    entries = _extract_dataset_entries(data)

    for d in entries:
        name = _get_str(d, ("name", "dataset_name", "datasetName", "title"))
        link = _get_str(d, ("doi", "DOI", "link", "url", "uri", "homepage", "landing_page", "landingPage"))
        if name and link:
            return True

    # Also accept flattened fields at root / anywhere
    flat_name = ""
    flat_link = ""
    for k, v in _iter_items(data):
        if k is None or not isinstance(v, str) or not v.strip():
            continue
        lk = k.lower()
        if lk in {"dataset_name", "datasetname", "dataset", "name_of_dataset"} and not flat_name:
            flat_name = v.strip()
        if lk in {"dataset_doi", "datasetdoi", "doi", "dataset_url", "dataseturl", "dataset_link", "datasetlink", "url", "link"} and not flat_link:
            flat_link = v.strip()
    return bool(flat_name and flat_link)
def _get_research_area(data: Any) -> str:
    if isinstance(data, dict):
        for k in ("research_area", "researchArea", "domain", "area"):
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    for k, v in _iter_items(data):
        if k is None or not isinstance(v, str) or not v.strip():
            continue
        lk = k.lower()
        if lk in {"research_area", "researcharea", "domain", "area"}:
            return v.strip()
    return 
def _has_specific_target(data: Any) -> bool:
    # Looks for any concrete identifier beyond a vague research area.
    specific_keys = {
        "dataset", "datasets", "dataset_name", "datasetdoi", "dataset_doi", "dataset_url", "dataset_link",
        "doi", "url", "link", "arxiv", "arxiv_id", "paper_title", "title", "publication_doi",
        "repository", "repo", "github", "git", "osf", "zenodo", "figshare", "kaggle"
    }
    for k, v in _iter_items(data):
        if k is None:
            continue
        lk = k.lower()
        if lk in {"research_area", "researcharea", "domain", "area"}:
            continue
        if lk in specific_keys:
            if isinstance(v, str) and v.strip():
                return True
            if isinstance(v, (dict, list)) and v:
                return True
    return False
def validate_intake(data: Any) -> List[str]:
    errors: List[str] = []

    research_area = _get_research_area(data)
    if research_area and not _has_specific_target(data):
        errors.append(
            "Blocked: intake provides only a vague research area ('{ra}'). Add a concrete target identifier "
            "(e.g., dataset name + DOI/link, paper DOI/arXiv, or a specific URL/repository).".format(ra=research_area)
        )

    if _is_dataset_verification_selected(data) and not _has_dataset_identifier(data):
        errors.append(
            "Blocked: dataset-verification pilot claim selected, but dataset identifier is missing. "
            "Provide BOTH dataset name and a DOI/link (URL) to the dataset landing page."
        )

    return errors
def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as e:
        loc = f"line {e.lineno}, col {e.colno}"
        raise SystemExit(f"ERROR: invalid JSON ({loc}): {e.msg}")
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="validate_intake", description="Validate an intake checklist JSON file.")
    p.add_argument("intake_path", help="Path to intake checklist JSON file")
    args = p.parse_args(argv)

    path = Path(args.intake_path).expanduser().resolve()
    data = _load_json(path)
    errors = validate_intake(data)

    if errors:
        for msg in errors:
            print(msg, file=sys.stderr)
        print("Validation failed: fix the blocked items above and re-run.", file=sys.stderr)
        return 2

    print("OK: intake checklist validated.")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
