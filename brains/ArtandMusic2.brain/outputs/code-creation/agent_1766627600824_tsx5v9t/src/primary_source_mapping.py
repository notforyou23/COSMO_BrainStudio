from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _norm_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        x = str(x)
    if not isinstance(x, str):
        return None
    s = x.strip()
    return s or None


def _norm_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, str):
        items = [x]
    elif isinstance(x, (list, tuple, set)):
        items = list(x)
    else:
        items = [x]
    out: List[str] = []
    for it in items:
        s = _norm_str(it)
        if s and s not in out:
            out.append(s)
    return out


def _pick_first(*vals: Any) -> Optional[str]:
    for v in vals:
        s = _norm_str(v)
        if s:
            return s
    return None


def _boolish(x: Any) -> Optional[bool]:
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    s = _norm_str(x)
    if not s:
        return None
    s2 = s.lower()
    if s2 in {"true", "yes", "y", "1"}:
        return True
    if s2 in {"false", "no", "n", "0"}:
        return False
    return None


@dataclass(frozen=True)
class PrimarySourceInputs:
    dataset_name: Optional[str]
    doi: Optional[str]
    link: Optional[str]
    research_area: Optional[str]
    candidate_authors: List[str]
    candidate_keywords: List[str]
    years: Tuple[int, int] = (2019, 2025)


def _extract_inputs(primary_source_verification: Dict[str, Any]) -> PrimarySourceInputs:
    psv = primary_source_verification or {}
    dataset_name = _pick_first(psv.get("dataset_name"), psv.get("dataset"), psv.get("name"))
    doi = _pick_first(psv.get("doi"), psv.get("dataset_doi"))
    link = _pick_first(psv.get("link"), psv.get("url"), psv.get("dataset_link"), psv.get("dataset_url"))
    research_area = _pick_first(psv.get("research_area"), psv.get("area"), psv.get("domain"))
    candidate_authors = _norm_list(psv.get("candidate_authors") or psv.get("authors") or psv.get("candidate_author_names"))
    candidate_keywords = _norm_list(psv.get("candidate_keywords") or psv.get("keywords") or psv.get("candidate_terms"))

    # Optional explicit known/unknown hint; otherwise infer.
    is_known = _boolish(psv.get("is_known_primary_source") or psv.get("known_primary_source"))
    if is_known is True:
        pass
    elif is_known is False:
        dataset_name = None if not dataset_name else dataset_name
        doi = None if not doi else doi
        link = None if not link else link
    # inference when hint absent
    if is_known is None:
        is_known = any([dataset_name, doi, link])

    if is_known:
        if not any([dataset_name, doi, link]):
            raise ValueError("primary_source_verification: expected dataset_name/doi/link for known primary source.")
    else:
        if not research_area and not candidate_authors and not candidate_keywords:
            raise ValueError(
                "primary_source_verification: for unknown primary source, require research_area and/or candidate_authors/keywords."
            )
    return PrimarySourceInputs(
        dataset_name=dataset_name,
        doi=doi,
        link=link,
        research_area=research_area,
        candidate_authors=candidate_authors,
        candidate_keywords=candidate_keywords,
    )


def _build_queries(inp: PrimarySourceInputs) -> List[Dict[str, Any]]:
    start_year, end_year = inp.years
    queries: List[Dict[str, Any]] = []
    def add(q: str, purpose: str) -> None:
        qn = _norm_str(q)
        if not qn:
            return
        if any(d.get("query") == qn for d in queries):
            return
        queries.append({"query": qn, "purpose": purpose, "years": {"start": start_year, "end": end_year}})

    if inp.doi:
        add(f'"{inp.doi}"', "locate primary source by DOI")
        add(f'"{inp.doi}" dataset', "confirm DOI corresponds to dataset/repository landing page")
    if inp.link:
        add(f'"{inp.link}"', "locate primary source by canonical link")
    if inp.dataset_name:
        add(f'"{inp.dataset_name}" dataset', "locate dataset landing page")
        add(f'"{inp.dataset_name}" (DOI OR zenodo OR figshare OR dataverse OR osf)', "find dataset DOI/repository record")

    # discovery mode / enrichment
    if inp.research_area:
        if inp.candidate_keywords:
            add(f'{inp.research_area} ' + " ".join(f'"{k}"' for k in inp.candidate_keywords[:6]) + " dataset", "discover candidate datasets")
        else:
            add(f'{inp.research_area} dataset (DOI OR repository)', "discover candidate datasets")
    if inp.candidate_authors:
        for a in inp.candidate_authors[:5]:
            add(f'"{a}" dataset (DOI OR repository OR supplementary)', "discover datasets associated with candidate authors")
            if inp.research_area:
                add(f'"{a}" {inp.research_area} dataset', "narrow discovery to research area + author")
    if inp.candidate_keywords:
        add(" ".join(f'"{k}"' for k in inp.candidate_keywords[:8]) + " dataset", "discover datasets by keywords")
    return queries


def map_primary_source_verification_to_search_plan(primary_source_verification: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically map intake primary_source_verification inputs into the 2019–2025 search-plan template fields.

    Output keys are designed to align with a schema-driven search-plan template:
      - template_version: '2019_2025'
      - timeframe: start_year/end_year
      - primary_source_verification: known/discovery blocks + generated_queries
    """
    inp = _extract_inputs(primary_source_verification)
    known = any([inp.dataset_name, inp.doi, inp.link])
    out: Dict[str, Any] = {
        "template_version": "2019_2025",
        "timeframe": {"start_year": inp.years[0], "end_year": inp.years[1]},
        "primary_source_verification": {
            "mode": "known_primary_source" if known else "unknown_primary_source",
            "known_primary_source": {
                "dataset_name": inp.dataset_name,
                "doi": inp.doi,
                "link": inp.link,
            } if known else None,
            "unknown_primary_source": None if known else {
                "research_area": inp.research_area,
                "candidate_authors": inp.candidate_authors,
                "candidate_keywords": inp.candidate_keywords,
            },
            "generated_queries": _build_queries(inp),
        },
    }
    # prune Nones for schema-friendliness while remaining deterministic
    psv = out["primary_source_verification"]
    for k in ["known_primary_source", "unknown_primary_source"]:
        if psv.get(k) is None:
            psv.pop(k, None)
    # remove None fields within blocks
    for block_key in ["known_primary_source", "unknown_primary_source"]:
        if block_key in psv:
            psv[block_key] = {k: v for k, v in psv[block_key].items() if v not in (None, [], {})}
    return out
