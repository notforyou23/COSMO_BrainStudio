from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union


class OverridesError(ValueError):
    pass


JsonDict = Dict[str, Any]
def _load_yaml(path: Union[str, Path]) -> Any:
    p = Path(path)
    if not p.exists():
        raise OverridesError(f"Overrides file not found: {p}")
    try:
        import yaml  # type: ignore
    except Exception as e:  # pragma: no cover
        raise OverridesError("PyYAML is required to load override YAML files") from e
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise OverridesError(f"Failed to parse YAML: {p}") from e
    return {} if data is None else data
def _is_scalar_list(v: Any) -> bool:
    if not isinstance(v, list):
        return False
    for x in v:
        if isinstance(x, (dict, list)):
            return False
    return True


def _merge_scalar_lists(a: List[Any], b: List[Any]) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for x in a + b:
        key = x
        try:
            h = hash(key)
        except Exception:
            out.append(x)
            continue
        if h in seen:
            continue
        seen.add(h)
        out.append(x)
    return out


def deep_merge(base: Any, overlay: Any) -> Any:
    if overlay is None:
        return base
    if base is None:
        return overlay
    if isinstance(base, dict) and isinstance(overlay, dict):
        out = dict(base)
        for k, v in overlay.items():
            out[k] = deep_merge(out.get(k), v)
        return out
    if _is_scalar_list(base) and _is_scalar_list(overlay):
        return _merge_scalar_lists(list(base), list(overlay))
    return overlay
def _ensure_dict(x: Any, where: str) -> JsonDict:
    if x is None:
        return {}
    if not isinstance(x, dict):
        raise OverridesError(f"Expected mapping at {where}, got {type(x).__name__}")
    return x  # type: ignore[return-value]


def _ensure_str(x: Any, where: str) -> str:
    if not isinstance(x, str) or not x.strip():
        raise OverridesError(f"Expected non-empty string at {where}")
    return x.strip()


def _ensure_list(x: Any, where: str) -> List[Any]:
    if x is None:
        return []
    if not isinstance(x, list):
        raise OverridesError(f"Expected list at {where}, got {type(x).__name__}")
    return x
def _normalize_company(company_id: str, raw: Mapping[str, Any], defaults: Mapping[str, Any]) -> JsonDict:
    c = deep_merge(dict(defaults), dict(raw))
    out: JsonDict = {"id": company_id}

    if "name" in c and c["name"] is not None:
        out["name"] = _ensure_str(c["name"], f"companies.{company_id}.name")

    for k in ("website", "status", "notes"):
        if k in c and c[k] is not None:
            out[k] = _ensure_str(c[k], f"companies.{company_id}.{k}")

    tags = c.get("tags")
    if tags is not None:
        lst = _ensure_list(tags, f"companies.{company_id}.tags")
        if not _is_scalar_list(lst):
            raise OverridesError(f"Expected scalar list at companies.{company_id}.tags")
        out["tags"] = _merge_scalar_lists([], [str(x) for x in lst if str(x).strip()])

    categories = c.get("categories")
    if categories is not None:
        lst = _ensure_list(categories, f"companies.{company_id}.categories")
        if not _is_scalar_list(lst):
            raise OverridesError(f"Expected scalar list at companies.{company_id}.categories")
        out["categories"] = _merge_scalar_lists([], [str(x) for x in lst if str(x).strip()])

    metrics = c.get("metrics")
    if metrics is not None:
        md = _ensure_dict(metrics, f"companies.{company_id}.metrics")
        out["metrics"] = md

    sources = c.get("sources")
    if sources is not None:
        lst = _ensure_list(sources, f"companies.{company_id}.sources")
        out["sources"] = lst

    for k in ("enabled", "hidden"):
        if k in c and c[k] is not None:
            if not isinstance(c[k], bool):
                raise OverridesError(f"Expected boolean at companies.{company_id}.{k}")
            out[k] = c[k]

    return out
def normalize_overrides(doc: Any) -> JsonDict:
    d = _ensure_dict(doc, "root")
    defaults = _ensure_dict(d.get("defaults"), "defaults")
    companies_raw = d.get("companies") or d.get("overrides") or {}
    companies = _ensure_dict(companies_raw, "companies")

    normalized: JsonDict = {"defaults": defaults, "companies": {}}
    for cid, raw in companies.items():
        cid_str = _ensure_str(cid, "companies key")
        raw_map = _ensure_dict(raw, f"companies.{cid_str}")
        normalized["companies"][cid_str] = _normalize_company(cid_str, raw_map, defaults)
    return normalized
def merge_overrides(*docs: Mapping[str, Any]) -> JsonDict:
    merged: JsonDict = {"defaults": {}, "companies": {}}
    for doc in docs:
        n = normalize_overrides(doc)
        merged["defaults"] = deep_merge(merged.get("defaults", {}), n.get("defaults", {}))
        for cid, c in n.get("companies", {}).items():
            prev = merged["companies"].get(cid, {})
            merged["companies"][cid] = deep_merge(prev, c)
    # Re-normalize companies against merged defaults to ensure defaults applied consistently
    defaults = merged.get("defaults", {})
    companies = {}
    for cid, c in merged.get("companies", {}).items():
        raw = dict(c)
        raw.pop("id", None)
        companies[cid] = _normalize_company(cid, raw, defaults)
    merged["companies"] = companies
    return merged
def load_overrides(paths: Union[str, Path, Sequence[Union[str, Path]]]) -> JsonDict:
    if isinstance(paths, (str, Path)):
        paths_list: List[Union[str, Path]] = [paths]
    else:
        paths_list = list(paths)
    if not paths_list:
        return {"defaults": {}, "companies": {}}
    docs: List[Mapping[str, Any]] = []
    for p in paths_list:
        docs.append(_ensure_dict(_load_yaml(p), f"file:{p}"))
    return merge_overrides(*docs)


__all__ = ["OverridesError", "deep_merge", "normalize_overrides", "merge_overrides", "load_overrides"]
