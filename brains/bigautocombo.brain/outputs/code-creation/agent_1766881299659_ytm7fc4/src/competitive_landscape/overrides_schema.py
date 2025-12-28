from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

Json = Union[None, bool, int, float, str, List["Json"], Dict[str, "Json"]]
class ValidationError(ValueError):
    """Raised when overrides fail schema validation."""
def _path_join(path: Tuple[Union[str, int], ...]) -> str:
    if not path:
        return "$"
    out = "$"
    for p in path:
        out += f"[{p!r}]" if isinstance(p, int) else f".{p}"
    return out


def require_mapping(x: Any, *, path: Tuple[Union[str, int], ...] = ()) -> Mapping[str, Any]:
    if not isinstance(x, Mapping):
        raise ValidationError(f"{_path_join(path)} must be a mapping/object")
    return x


def require_sequence(x: Any, *, path: Tuple[Union[str, int], ...] = ()) -> Sequence[Any]:
    if isinstance(x, (str, bytes)) or not isinstance(x, Sequence):
        raise ValidationError(f"{_path_join(path)} must be a list/sequence")
    return x


def opt_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if not isinstance(x, str):
        raise ValidationError("expected string or null")
    s = x.strip()
    return s if s else None


def req_str(x: Any, *, path: Tuple[Union[str, int], ...] = ()) -> str:
    if not isinstance(x, str) or not x.strip():
        raise ValidationError(f"{_path_join(path)} must be a non-empty string")
    return x.strip()


def opt_bool(x: Any) -> Optional[bool]:
    if x is None:
        return None
    if not isinstance(x, bool):
        raise ValidationError("expected boolean or null")
    return x


def opt_str_list(x: Any, *, path: Tuple[Union[str, int], ...] = ()) -> List[str]:
    if x is None:
        return []
    seq = require_sequence(x, path=path)
    out: List[str] = []
    for i, v in enumerate(seq):
        if not isinstance(v, str) or not v.strip():
            raise ValidationError(f"{_path_join(path + (i,))} must be a non-empty string")
        out.append(v.strip())
    return out
@dataclass(frozen=True)
class CompanyOverride:
    """Normalized override for a single company/vendor entry."""

    key: str
    name: Optional[str] = None
    website: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    active: Optional[bool] = None
    notes: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: Mapping[str, Any], *, path: Tuple[Union[str, int], ...]) -> "CompanyOverride":
        d = require_mapping(d, path=path)
        key = req_str(d.get("key"), path=path + ("key",))
        name = opt_str(d.get("name"))
        website = opt_str(d.get("website") or d.get("url"))
        tags = opt_str_list(d.get("tags"), path=path + ("tags",))
        active = opt_bool(d.get("active"))
        notes = opt_str(d.get("notes"))
        known = {"key", "name", "website", "url", "tags", "active", "notes"}
        extra = {k: v for k, v in d.items() if k not in known}
        return CompanyOverride(key=key, name=name, website=website, tags=tags, active=active, notes=notes, extra=extra)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"key": self.key}
        if self.name is not None:
            out["name"] = self.name
        if self.website is not None:
            out["website"] = self.website
        if self.tags:
            out["tags"] = list(self.tags)
        if self.active is not None:
            out["active"] = self.active
        if self.notes is not None:
            out["notes"] = self.notes
        out.update(self.extra)
        return out
@dataclass(frozen=True)
class OverridesDoc:
    """Top-level overrides document with light structure and strong validation."""

    version: Optional[str] = None
    companies: List[CompanyOverride] = field(default_factory=list)
    aliases: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: Mapping[str, Any], *, path: Tuple[Union[str, int], ...] = ()) -> "OverridesDoc":
        d = require_mapping(d, path=path)
        version = opt_str(d.get("version"))
        companies_raw = d.get("companies") or d.get("vendors") or []
        companies_seq = require_sequence(companies_raw, path=path + ("companies",))
        companies: List[CompanyOverride] = []
        seen: set[str] = set()
        for i, item in enumerate(companies_seq):
            co = CompanyOverride.from_dict(item, path=path + ("companies", i))
            if co.key in seen:
                raise ValidationError(f"{_path_join(path + ('companies', i, 'key'))} duplicates key {co.key!r}")
            seen.add(co.key)
            companies.append(co)
        aliases_raw = d.get("aliases") or {}
        aliases_map = require_mapping(aliases_raw, path=path + ("aliases",))
        aliases: Dict[str, str] = {}
        for k, v in aliases_map.items():
            kk = req_str(k, path=path + ("aliases",))
            if not isinstance(v, str) or not v.strip():
                raise ValidationError(f"{_path_join(path + ('aliases', kk))} must be a non-empty string")
            aliases[kk] = v.strip()
        known = {"version", "companies", "vendors", "aliases"}
        extra = {k: v for k, v in d.items() if k not in known}
        return OverridesDoc(version=version, companies=companies, aliases=aliases, extra=extra)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if self.version is not None:
            out["version"] = self.version
        if self.companies:
            out["companies"] = [c.to_dict() for c in self.companies]
        if self.aliases:
            out["aliases"] = dict(self.aliases)
        out.update(self.extra)
        return out
def validate_overrides_doc(d: Any) -> OverridesDoc:
    """Validate and normalize a loaded YAML/JSON object into an OverridesDoc."""
    try:
        return OverridesDoc.from_dict(require_mapping(d, path=()), path=())
    except ValidationError:
        raise
    except Exception as e:  # noqa: BLE001
        raise ValidationError(str(e)) from e


__all__ = [
    "Json",
    "ValidationError",
    "CompanyOverride",
    "OverridesDoc",
    "validate_overrides_doc",
]
