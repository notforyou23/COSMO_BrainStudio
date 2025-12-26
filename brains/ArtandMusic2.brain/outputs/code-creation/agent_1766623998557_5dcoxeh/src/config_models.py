from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar

T = TypeVar("T")

class ValidationError(ValueError):
    def __init__(self, message: str, path: str = ""):
        super().__init__(f"{path}: {message}" if path else message)
        self.path = path
        self.message = message

def _is_nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != ""

def _is_str_list(v: Any) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() != "" for x in v) and len(v) > 0

def _dict(v: Any, path: str) -> Dict[str, Any]:
    if not isinstance(v, dict):
        raise ValidationError("must be a mapping/object", path)
    return v

def _unknown_keys(d: Dict[str, Any], allowed: set, path: str) -> None:
    extra = sorted(set(d.keys()) - allowed)
    if extra:
        raise ValidationError(f"unknown keys: {extra}", path)

def _opt_str(v: Any, path: str) -> Optional[str]:
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValidationError("must be a string", path)
    s = v.strip()
    return s or None

def _opt_str_list(v: Any, path: str) -> Optional[List[str]]:
    if v is None:
        return None
    if not isinstance(v, list):
        raise ValidationError("must be a list of strings", path)
    out = []
    for i, x in enumerate(v):
        if not isinstance(x, str) or x.strip() == "":
            raise ValidationError("must be a non-empty string", f"{path}[{i}]")
        out.append(x.strip())
    return out or None

def _require(cond: bool, msg: str, path: str) -> None:
    if not cond:
        raise ValidationError(msg, path)

def _load_dataclass(cls: Type[T], data: Any, path: str) -> T:
    d = _dict(data, path)
    return cls.from_dict(d, path=path)  # type: ignore[attr-defined]
@dataclass(frozen=True)
class PrimarySourceVerification:
    dataset_name: Optional[str] = None
    doi: Optional[str] = None
    link: Optional[str] = None
    research_area: Optional[str] = None
    candidate_authors: Optional[List[str]] = None
    keywords: Optional[List[str]] = None

    @staticmethod
    def from_dict(d: Dict[str, Any], path: str = "primary_source_verification") -> "PrimarySourceVerification":
        allowed = {"dataset_name", "doi", "link", "research_area", "candidate_authors", "keywords"}
        _unknown_keys(d, allowed, path)
        obj = PrimarySourceVerification(
            dataset_name=_opt_str(d.get("dataset_name"), f"{path}.dataset_name"),
            doi=_opt_str(d.get("doi"), f"{path}.doi"),
            link=_opt_str(d.get("link"), f"{path}.link"),
            research_area=_opt_str(d.get("research_area"), f"{path}.research_area"),
            candidate_authors=_opt_str_list(d.get("candidate_authors"), f"{path}.candidate_authors"),
            keywords=_opt_str_list(d.get("keywords"), f"{path}.keywords"),
        )
        obj.validate(path)
        return obj

    def validate(self, path: str = "primary_source_verification") -> None:
        has_id = any(_is_nonempty_str(v) for v in [self.dataset_name, self.doi, self.link])
        has_context = _is_nonempty_str(self.research_area) and (self.candidate_authors is not None or self.keywords is not None)
        _require(has_id or has_context,
                 "provide dataset_name/doi/link OR (research_area AND (candidate_authors or keywords))",
                 path)
        if self.research_area is not None:
            _require(_is_nonempty_str(self.research_area), "must be a non-empty string", f"{path}.research_area")
        if self.candidate_authors is not None:
            _require(_is_str_list(self.candidate_authors), "must be a non-empty list of non-empty strings", f"{path}.candidate_authors")
        if self.keywords is not None:
            _require(_is_str_list(self.keywords), "must be a non-empty list of non-empty strings", f"{path}.keywords")
@dataclass(frozen=True)
class IntakeChecklist:
    primary_source_verification: PrimarySourceVerification
    meta: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: Dict[str, Any], path: str = "intake_checklist") -> "IntakeChecklist":
        allowed = {"primary_source_verification", "meta"}
        _unknown_keys(d, allowed, path)
        _require("primary_source_verification" in d, "missing required section", f"{path}.primary_source_verification")
        psv = _load_dataclass(PrimarySourceVerification, d.get("primary_source_verification"), f"{path}.primary_source_verification")
        meta = d.get("meta") or {}
        if not isinstance(meta, dict):
            raise ValidationError("must be a mapping/object", f"{path}.meta")
        return IntakeChecklist(primary_source_verification=psv, meta=meta)
@dataclass(frozen=True)
class SearchPlanPrimarySourceVerification2019_2025:
    time_window: str = "2019-2025"
    dataset_name: Optional[str] = None
    doi: Optional[str] = None
    link: Optional[str] = None
    research_area: Optional[str] = None
    candidate_authors: Optional[List[str]] = None
    keywords: Optional[List[str]] = None

    @staticmethod
    def from_dict(d: Dict[str, Any], path: str = "search_plan.primary_source_verification") -> "SearchPlanPrimarySourceVerification2019_2025":
        allowed = {"time_window", "dataset_name", "doi", "link", "research_area", "candidate_authors", "keywords"}
        _unknown_keys(d, allowed, path)
        tw = _opt_str(d.get("time_window"), f"{path}.time_window") or "2019-2025"
        obj = SearchPlanPrimarySourceVerification2019_2025(
            time_window=tw,
            dataset_name=_opt_str(d.get("dataset_name"), f"{path}.dataset_name"),
            doi=_opt_str(d.get("doi"), f"{path}.doi"),
            link=_opt_str(d.get("link"), f"{path}.link"),
            research_area=_opt_str(d.get("research_area"), f"{path}.research_area"),
            candidate_authors=_opt_str_list(d.get("candidate_authors"), f"{path}.candidate_authors"),
            keywords=_opt_str_list(d.get("keywords"), f"{path}.keywords"),
        )
        obj.validate(path)
        return obj

    def validate(self, path: str = "search_plan.primary_source_verification") -> None:
        _require(self.time_window == "2019-2025", "time_window must be '2019-2025'", f"{path}.time_window")
        has_any = any(_is_nonempty_str(v) for v in [self.dataset_name, self.doi, self.link, self.research_area]) or                   (self.candidate_authors is not None) or (self.keywords is not None)
        _require(has_any, "must include at least one input for verification", path)
@dataclass(frozen=True)
class SearchPlanTemplate2019_2025:
    primary_source_verification: SearchPlanPrimarySourceVerification2019_2025

    @staticmethod
    def from_dict(d: Dict[str, Any], path: str = "search_plan_template_2019_2025") -> "SearchPlanTemplate2019_2025":
        allowed = {"primary_source_verification"}
        _unknown_keys(d, allowed, path)
        _require("primary_source_verification" in d, "missing required section", f"{path}.primary_source_verification")
        psv = _load_dataclass(SearchPlanPrimarySourceVerification2019_2025, d.get("primary_source_verification"), f"{path}.primary_source_verification")
        return SearchPlanTemplate2019_2025(primary_source_verification=psv)
