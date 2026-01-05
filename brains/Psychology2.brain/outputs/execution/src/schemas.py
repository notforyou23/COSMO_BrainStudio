from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import BaseModel, Field, validator


class ParsingMethod(str, Enum):
    crossref = "crossref"
    datacite = "datacite"
    schema_org = "schema_org"
    meta_tags = "meta_tags"
    html_fallback = "html_fallback"
    unknown = "unknown"


class FailureReasonCode(str, Enum):
    none = "none"
    invalid_doi = "invalid_doi"
    doi_not_found = "doi_not_found"
    resolve_failed = "resolve_failed"
    fetch_failed = "fetch_failed"
    http_error = "http_error"
    paywall_or_blocked = "paywall_or_blocked"
    parse_failed = "parse_failed"
    metadata_missing = "metadata_missing"
    rate_limited = "rate_limited"
    timeout = "timeout"
    unexpected = "unexpected"


class Person(BaseModel):
    name: Optional[str] = None
    given: Optional[str] = None
    family: Optional[str] = None
    orcid: Optional[str] = None
    affiliations: List[str] = Field(default_factory=list)

    @validator("affiliations", pre=True)
    def _coerce_affiliations(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)


class Provenance(BaseModel):
    doi_input: str
    doi_normalized: Optional[str] = None

    landing_url: Optional[str] = None
    resolved_url: Optional[str] = None
    redirect_chain: List[str] = Field(default_factory=list)

    accessed_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    parsing_method: ParsingMethod = ParsingMethod.unknown

    failure_reason_code: FailureReasonCode = FailureReasonCode.none
    failure_message: Optional[str] = None

    http_status: Optional[int] = None
    source: Optional[str] = None
    raw_provider: Optional[str] = None

    @validator("redirect_chain", pre=True)
    def _coerce_redirect_chain(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)


class CitationRecord(BaseModel):
    record_id: Optional[str] = None

    doi: Optional[str] = None
    url: Optional[str] = None

    title: Optional[str] = None
    container_title: Optional[str] = None
    publisher: Optional[str] = None

    issued: Optional[Union[date, str]] = None
    type: Optional[str] = None
    language: Optional[str] = None

    authors: List[Person] = Field(default_factory=list)
    editors: List[Person] = Field(default_factory=list)

    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    article_number: Optional[str] = None

    issn: List[str] = Field(default_factory=list)
    isbn: List[str] = Field(default_factory=list)

    abstract: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    license: Optional[str] = None

    provenance: Provenance

    @validator("authors", "editors", pre=True)
    def _coerce_people(cls, v: Any) -> List[Person]:
        if v is None:
            return []
        if isinstance(v, dict):
            return [Person(**v)]
        return [p if isinstance(p, Person) else Person(**p) for p in list(v)]

    @validator("issn", "isbn", "keywords", pre=True)
    def _coerce_str_list(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return [str(x) for x in list(v)]

    def to_flat_dict(self) -> Dict[str, Any]:
        """CSV-friendly flattened representation with stable keys."""
        d = self.dict()
        prov = d.pop("provenance", {}) or {}
        d["authors"] = "; ".join([p.get("name") or " ".join(filter(None, [p.get("given"), p.get("family")])).strip() for p in d.get("authors") or [] if p])
        d["editors"] = "; ".join([p.get("name") or " ".join(filter(None, [p.get("given"), p.get("family")])).strip() for p in d.get("editors") or [] if p])
        d["issn"] = "; ".join(d.get("issn") or [])
        d["isbn"] = "; ".join(d.get("isbn") or [])
        d["keywords"] = "; ".join(d.get("keywords") or [])
        for k, v in prov.items():
            d[f"provenance_{k}"] = v
        return d
