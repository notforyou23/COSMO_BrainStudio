from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple
def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _asdict(obj: Any) -> Any:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, (list, tuple)):
        return [_asdict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _asdict(v) for k, v in obj.items()}
    return obj
@dataclass(frozen=True)
class Provenance:
    source_id: str
    uri: Optional[str] = None
    title: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: str = field(default_factory=utc_now_iso)
    doc_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Passage:
    passage_id: str
    text: str
    provenance: Provenance
    score: float = 0.0
    char_span: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["provenance"] = self.provenance.to_dict()
        return d
@dataclass(frozen=True)
class Quote:
    passage_id: str
    quote_text: str
    char_span: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    kind: Optional[str] = None
    parent_claim_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimEvidence:
    claim_id: str
    quotes: List[Quote] = field(default_factory=list)
    passage_ids: List[str] = field(default_factory=list)
    alignment_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["quotes"] = [_asdict(q) for q in self.quotes]
        return d
@dataclass(frozen=True)
class ConstraintCheck:
    name: str
    passed: bool
    details: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DecisionStatus(str, Enum):
    SUPPORTED = "supported"
    REFUTED = "refuted"
    NOT_ENOUGH_EVIDENCE = "not_enough_evidence"
    INVALID = "invalid"


@dataclass(frozen=True)
class ClaimDecision:
    claim_id: str
    status: DecisionStatus
    confidence: float = 0.0
    evidence: ClaimEvidence = field(default_factory=lambda: ClaimEvidence(claim_id=""))
    checks: List[ConstraintCheck] = field(default_factory=list)
    rationale: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["evidence"] = _asdict(self.evidence)
        d["checks"] = [_asdict(c) for c in self.checks]
        return d
@dataclass(frozen=True)
class Thresholds:
    min_alignment_score: float = 0.6
    min_confidence_supported: float = 0.6
    min_confidence_refuted: float = 0.6
    require_quotes: bool = True
    require_passages: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationInput:
    input_id: str
    claims: List[Claim]
    query: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["claims"] = [_asdict(c) for c in self.claims]
        return d


@dataclass(frozen=True)
class VerificationResult:
    input_id: str
    decisions: List[ClaimDecision]
    overall_status: DecisionStatus
    thresholds: Thresholds = field(default_factory=Thresholds)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["overall_status"] = self.overall_status.value
        d["decisions"] = [_asdict(x) for x in self.decisions]
        d["thresholds"] = _asdict(self.thresholds)
        return d
class AuditEventType(str, Enum):
    EVIDENCE_MISSING = "evidence_missing"
    QUOTE_MISMATCH = "quote_mismatch"
    CONSTRAINT_FAILED = "constraint_failed"
    THRESHOLD_NOT_MET = "threshold_not_met"


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    event_type: AuditEventType
    claim_id: Optional[str]
    message: str
    timestamp: str = field(default_factory=utc_now_iso)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d


__all__ = [
    "Provenance",
    "Passage",
    "Quote",
    "Claim",
    "ClaimEvidence",
    "ConstraintCheck",
    "DecisionStatus",
    "ClaimDecision",
    "Thresholds",
    "VerificationInput",
    "VerificationResult",
    "AuditEventType",
    "AuditEvent",
]
