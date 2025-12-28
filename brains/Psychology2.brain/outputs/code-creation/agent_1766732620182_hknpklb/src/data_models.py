from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RouteDecision(str, Enum):
    AUTO_ANSWER = "auto_answer"
    ESCALATE = "escalate"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str
    risk_tier: RiskTier = RiskTier.LOW
    context: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UncertaintySignals:
    """Per-claim uncertainty signals.

    Conventions:
      - All numeric scores should be in [0, 1] where higher means *more uncertain/risky*.
      - `components` can hold raw features used to compute the final score.
    """

    score: float
    components: Dict[str, float] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RoutingOutput:
    claim_id: str
    decision: RouteDecision
    uncertainty_score: float
    threshold: float
    risk_tier: RiskTier
    reason: Optional[str] = None
    signals: Optional[UncertaintySignals] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.signals is None:
            d["signals"] = None
        return d


@dataclass(frozen=True)
class LabeledExample:
    """A claim paired with a gold label for evaluation.

    `label_error` indicates whether the model-produced answer is incorrect for this claim
    (1=error, 0=correct). Routing/abstention decisions operate independently from labels.
    """

    claim: Claim
    label_error: int
    weight: float = 1.0
    gold: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.label_error not in (0, 1):
            raise ValueError("label_error must be 0 or 1")
        if self.weight <= 0:
            raise ValueError("weight must be > 0")


@dataclass(frozen=True)
class EvaluationRecord:
    """One row of evaluation: a labeled example with routing output."""

    claim_id: str
    risk_tier: RiskTier
    label_error: int
    decision: RouteDecision
    uncertainty_score: float
    threshold: float
    weight: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SweepPointResult:
    """Aggregated metrics at a given threshold, optionally per tier."""

    threshold: float
    risk_tier: Optional[RiskTier] = None
    n: int = 0
    coverage: float = 0.0
    escalate_rate: float = 0.0
    abstain_rate: float = 0.0
    error_rate_on_answered: float = 0.0
    expected_human_reviews: float = 0.0
    expected_error: float = 0.0
    expected_cost: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def coerce_risk_tier(v: Any) -> RiskTier:
    if isinstance(v, RiskTier):
        return v
    if v is None:
        return RiskTier.LOW
    s = str(v).strip().lower()
    for t in RiskTier:
        if t.value == s:
            return t
    raise ValueError(f"Unknown risk tier: {v!r}")


def coerce_route_decision(v: Any) -> RouteDecision:
    if isinstance(v, RouteDecision):
        return v
    s = str(v).strip().lower()
    for d in RouteDecision:
        if d.value == s:
            return d
    raise ValueError(f"Unknown route decision: {v!r}")


def records_to_jsonl(records: Sequence[Mapping[str, Any]]) -> str:
    return "".join(json.dumps(dict(r), ensure_ascii=False) + "\n" for r in records)
