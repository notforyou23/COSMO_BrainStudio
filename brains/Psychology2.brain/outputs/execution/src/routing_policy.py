from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

Decision = str  # "auto" | "escalate" | "abstain"


@dataclass(frozen=True)
class Thresholds:
    escalate_at: float = 0.35
    abstain_at: float = 0.75

    def __post_init__(self) -> None:
        if not (0.0 <= self.escalate_at <= 1.0 and 0.0 <= self.abstain_at <= 1.0):
            raise ValueError("Thresholds must be in [0, 1].")
        if self.escalate_at > self.abstain_at:
            raise ValueError("escalate_at must be <= abstain_at.")


@dataclass(frozen=True)
class RoutingPolicy:
    tier_thresholds: Mapping[str, Thresholds] = field(
        default_factory=lambda: {
            "low": Thresholds(escalate_at=0.45, abstain_at=0.85),
            "medium": Thresholds(escalate_at=0.30, abstain_at=0.75),
            "high": Thresholds(escalate_at=0.15, abstain_at=0.55),
            "default": Thresholds(escalate_at=0.30, abstain_at=0.75),
        }
    )
    abstain_if: Tuple[str, ...] = ("policy_violation", "unsafe_content")
    escalate_if: Tuple[str, ...] = ("needs_citation", "missing_context")
    uncertainty_key: str = "uncertainty"

    def thresholds_for(self, tier: Optional[str]) -> Thresholds:
        t = tier or "default"
        return self.tier_thresholds.get(t, self.tier_thresholds.get("default", Thresholds()))


@dataclass(frozen=True)
class RoutingResult:
    claim_id: Optional[str]
    risk_tier: str
    decision: Decision
    uncertainty: float
    reasons: Tuple[str, ...] = ()
    thresholds: Thresholds = field(default_factory=Thresholds)


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def compute_uncertainty(signals: Mapping[str, Any], uncertainty_key: str = "uncertainty") -> float:
    if uncertainty_key in signals and signals[uncertainty_key] is not None:
        return min(1.0, max(0.0, _to_float(signals[uncertainty_key], 0.0)))

    if "self_consistency" in signals and signals["self_consistency"] is not None:
        sc = min(1.0, max(0.0, _to_float(signals["self_consistency"], 0.0)))
        return 1.0 - sc

    for k in ("confidence", "p_true", "prob_correct"):
        if k in signals and signals[k] is not None:
            c = min(1.0, max(0.0, _to_float(signals[k], 0.0)))
            return 1.0 - c

    if "entropy" in signals and signals["entropy"] is not None:
        return min(1.0, max(0.0, _to_float(signals["entropy"], 0.0)))

    keys = [k for k in ("uncertainty_logprob", "uncertainty_heuristic", "uncertainty_consistency") if k in signals]
    if keys:
        vals = [min(1.0, max(0.0, _to_float(signals.get(k), 0.0))) for k in keys]
        return sum(vals) / max(1, len(vals))
    return 0.0


def route_one(
    *,
    claim: Optional[Mapping[str, Any]] = None,
    signals: Optional[Mapping[str, Any]] = None,
    policy: Optional[RoutingPolicy] = None,
) -> RoutingResult:
    claim = claim or {}
    signals = signals or {}
    policy = policy or RoutingPolicy()

    claim_id = claim.get("id") if isinstance(claim, Mapping) else None
    tier = (claim.get("risk_tier") or claim.get("tier") or "default") if isinstance(claim, Mapping) else "default"
    thresholds = policy.thresholds_for(str(tier))

    reasons: List[str] = []
    for k in policy.abstain_if:
        if bool(signals.get(k)):
            reasons.append(f"hard_abstain:{k}")
    if reasons:
        u = compute_uncertainty(signals, policy.uncertainty_key)
        return RoutingResult(claim_id=claim_id, risk_tier=str(tier), decision="abstain", uncertainty=u, reasons=tuple(reasons), thresholds=thresholds)

    for k in policy.escalate_if:
        if bool(signals.get(k)):
            reasons.append(f"hard_escalate:{k}")

    u = compute_uncertainty(signals, policy.uncertainty_key)

    if u >= thresholds.abstain_at:
        reasons.append("uncertainty>=abstain_at")
        decision: Decision = "abstain"
    elif u >= thresholds.escalate_at or any(r.startswith("hard_escalate:") for r in reasons):
        if u >= thresholds.escalate_at:
            reasons.append("uncertainty>=escalate_at")
        decision = "escalate"
    else:
        reasons.append("uncertainty<escalate_at")
        decision = "auto"

    return RoutingResult(
        claim_id=claim_id,
        risk_tier=str(tier),
        decision=decision,
        uncertainty=u,
        reasons=tuple(reasons),
        thresholds=thresholds,
    )


def route_many(
    claims: Sequence[Mapping[str, Any]],
    signals_by_id: Mapping[Union[str, int], Mapping[str, Any]],
    policy: Optional[RoutingPolicy] = None,
    id_key: str = "id",
) -> List[RoutingResult]:
    policy = policy or RoutingPolicy()
    out: List[RoutingResult] = []
    for c in claims:
        cid = c.get(id_key)
        sig = signals_by_id.get(cid, {})
        out.append(route_one(claim=c, signals=sig, policy=policy))
    return out


def decisions_to_dict(results: Iterable[RoutingResult]) -> List[Dict[str, Any]]:
    return [
        {
            "claim_id": r.claim_id,
            "risk_tier": r.risk_tier,
            "decision": r.decision,
            "uncertainty": r.uncertainty,
            "reasons": list(r.reasons),
            "thresholds": {"escalate_at": r.thresholds.escalate_at, "abstain_at": r.thresholds.abstain_at},
        }
        for r in results
    ]
