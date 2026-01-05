from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProviderName(str, Enum):
    unpaywall = "unpaywall"
    openalex = "openalex"
    crossref = "crossref"
    pubmed = "pubmed"
    pmc = "pmc"
    direct = "direct"


class FullTextType(str, Enum):
    pdf = "pdf"
    html = "html"
    landing_page = "landing_page"


class AccessStatus(str, Enum):
    found = "found"
    not_found = "not_found"
    error = "error"
    skipped = "skipped"
class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: ProviderName
    url: Optional[HttpUrl] = None
    retrieved_at: datetime = Field(default_factory=utcnow)
    status_code: Optional[int] = None
    elapsed_ms: Optional[int] = None
    note: Optional[str] = None


class FullTextLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: HttpUrl
    type: FullTextType = FullTextType.landing_page
    license: Optional[str] = None
    host_type: Optional[str] = None
    version: Optional[str] = None
class ProviderOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: ProviderName
    status: AccessStatus
    location: Optional[FullTextLocation] = None
    provenance: Optional[Provenance] = None
    error: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class DOIOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doi: str
    ok: bool = False
    status: AccessStatus = AccessStatus.not_found
    best: Optional[FullTextLocation] = None
    providers: List[ProviderOutcome] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @property
    def duration_ms(self) -> Optional[int]:
        if not self.started_at or not self.finished_at:
            return None
        return int((self.finished_at - self.started_at).total_seconds() * 1000)
class DiscoverRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dois: List[str] = Field(..., min_length=1)
    email: Optional[str] = None
    providers: Optional[List[ProviderName]] = None
    max_per_provider: int = Field(default=1, ge=1, le=10)
    timeout_s: float = Field(default=20.0, gt=0, le=120)
    retries: int = Field(default=2, ge=0, le=10)
    backoff_s: float = Field(default=0.5, ge=0, le=10)


class RunMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    created_at: datetime = Field(default_factory=utcnow)
    app: str = "generated_api_server_1766724060001"
    stage: str = "stage_1"
    user_agent: Optional[str] = None
    notes: Optional[str] = None
class RunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meta: RunMeta
    request: DiscoverRequest
    outcomes: List[DOIOutcome]
    counts: Dict[str, int] = Field(default_factory=dict)

    def compute_counts(self) -> Dict[str, int]:
        total = len(self.outcomes)
        found = sum(1 for o in self.outcomes if o.status == AccessStatus.found)
        errored = sum(1 for o in self.outcomes if o.status == AccessStatus.error)
        skipped = sum(1 for o in self.outcomes if o.status == AccessStatus.skipped)
        not_found = total - found - errored - skipped
        self.counts = {
            "total": total,
            "found": found,
            "not_found": not_found,
            "error": errored,
            "skipped": skipped,
        }
        return self.counts


class DiscoverResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run: RunSummary
    logs: List[str] = Field(default_factory=list)
