from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
class SupportLabel(str, Enum):
    SUPPORTED = "supported"
    REFUTED = "refuted"
    NOT_ENOUGH_INFO = "not_enough_info"


class QuoteAttributionStatus(str, Enum):
    ATTRIBUTED = "attributed"
    UNATTRIBUTED = "unattributed"
    MISMATCH = "mismatch"
    UNKNOWN = "unknown"


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high" 
@dataclass(frozen=True)
class AtomicClaim:
    """Smallest self-contained proposition, with machine-readable fields for rule-based processing."""

    id: str
    text: str
    subject: Optional[str] = None
    predicate: Optional[str] = None
    obj: Optional[str] = None
    scope: Optional[str] = None  # e.g., time/location/conditional
    provenance_req: Optional[str] = None  # e.g., "must be quote", "primary source"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
@dataclass(frozen=True)
class EvidenceChunk:
    """A retrieved text span with enough provenance to attribute quotes."""

    id: str
    text: str
    source: str  # URL/path/corpus name
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    published: Optional[str] = None  # ISO-ish date string
    offset: Optional[Tuple[int, int]] = None  # character span in source doc, if known
    metadata: Dict[str, Any] = field(default_factory=dict)

    def short_source(self) -> str:
        return self.title or self.source

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
@dataclass(frozen=True)
class RetrievalResult:
    """Retrieval output for a query/atomic claim."""

    query: str
    claim_id: Optional[str] = None
    chunks: List[EvidenceChunk] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    retrieval_time_s: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def topk(self, k: int) -> List[EvidenceChunk]:
        return self.chunks[: max(0, k)]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["chunks"] = [c.to_dict() for c in self.chunks]
        return d
@dataclass(frozen=True)
class QuoteAttributionCheck:
    """Result of checking that a quoted span is properly attributed to its source."""

    status: QuoteAttributionStatus
    quote: Optional[str] = None
    attributed_to: Optional[str] = None  # e.g., person/org
    source: Optional[str] = None  # URL/title
    rationale: Optional[str] = None

    def ok(self) -> bool:
        return self.status == QuoteAttributionStatus.ATTRIBUTED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
@dataclass(frozen=True)
class VerificationDecision:
    """Decision for an atomic claim, with abstain support via NOT_ENOUGH_INFO."""

    claim_id: str
    label: SupportLabel
    confidence: float  # calibrated-ish probability of correctness for non-abstain; else may be 0
    abstained: bool
    evidence: List[EvidenceChunk] = field(default_factory=list)
    quote_check: Optional[QuoteAttributionCheck] = None
    rationale: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["evidence"] = [c.to_dict() for c in self.evidence]
        d["quote_check"] = None if self.quote_check is None else self.quote_check.to_dict()
        return d
@dataclass(frozen=True)
class ExampleRecord:
    """A single input example (claim) and its decomposed atomic claims."""

    example_id: str
    claim: str
    atomic_claims: List[AtomicClaim] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["atomic_claims"] = [c.to_dict() for c in self.atomic_claims]
        return d
@dataclass(frozen=True)
class EvalRecord:
    """Evaluation record for one atomic claim."""

    example_id: str
    claim_id: str
    gold: SupportLabel
    pred: SupportLabel
    confidence: float
    abstained: bool
    risk_tier: RiskTier = RiskTier.MEDIUM
    false_accept: Optional[bool] = None  # set when abstain is allowed: incorrect & not abstained
    retrieval: Optional[RetrievalResult] = None
    decision: Optional[VerificationDecision] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_false_accept(self) -> bool:
        if self.abstained:
            return False
        return self.pred != self.gold

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["retrieval"] = None if self.retrieval is None else self.retrieval.to_dict()
        d["decision"] = None if self.decision is None else self.decision.to_dict()
        return d
def clamp01(x: float) -> float:
    try:
        xf = float(x)
    except Exception:
        return 0.0
    return 0.0 if xf < 0.0 else 1.0 if xf > 1.0 else xf
