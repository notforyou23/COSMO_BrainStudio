from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _norm_decision(d: Any) -> str:
    if d is None:
        return "abstain"
    d = str(d).strip().lower()
    if d in {"auto", "answer", "respond", "responded", "auto_answer", "auto-answer"}:
        return "auto"
    if d in {"escalate", "review", "human", "human_review", "human-review"}:
        return "escalate"
    if d in {"abstain", "reject", "defer"}:
        return "abstain"
    return d


@dataclass(frozen=True)
class CostConfig:
    cost_auto: float = 0.0
    cost_escalate: float = 1.0
    cost_abstain: float = 0.0
    cost_error: float = 0.0


def evaluate_records(
    records: Iterable[Any],
    *,
    costs: CostConfig = CostConfig(),
    decision_key: str = "decision",
    y_true_key: str = "y_true",
    y_pred_key: str = "y_pred",
) -> Dict[str, Any]:
    """Compute metrics for a set of routing outcomes.

    Assumptions:
      - Errors are counted only for auto-answered items where both y_true and y_pred exist.
      - Escalated/abstained items are treated as having zero model error (human resolves).
      - expected_cost = sum(per-decision costs) + cost_error * (#auto_errors).
    """
    total = 0
    n_auto = n_escalate = n_abstain = 0
    n_auto_with_label = 0
    n_auto_errors = 0

    for r in records:
        total += 1
        d = _norm_decision(_get(r, decision_key, None))
        if d == "auto":
            n_auto += 1
            yt = _get(r, y_true_key, None)
            yp = _get(r, y_pred_key, None)
            if yt is not None and yp is not None:
                n_auto_with_label += 1
                if yp != yt:
                    n_auto_errors += 1
        elif d == "escalate":
            n_escalate += 1
        else:
            n_abstain += 1

    def safe_div(a: float, b: float) -> float:
        return float(a) / float(b) if b else 0.0

    coverage = safe_div(n_auto, total)
    escalation_rate = safe_div(n_escalate, total)
    abstention_rate = safe_div(n_abstain, total)

    auto_error_rate = safe_div(n_auto_errors, n_auto_with_label)
    overall_error_rate = safe_div(n_auto_errors, total)

    expected_cost = (
        costs.cost_auto * n_auto
        + costs.cost_escalate * n_escalate
        + costs.cost_abstain * n_abstain
        + costs.cost_error * n_auto_errors
    )
    expected_cost_per_item = safe_div(expected_cost, total)

    return {
        "n": total,
        "n_auto": n_auto,
        "n_escalate": n_escalate,
        "n_abstain": n_abstain,
        "coverage": coverage,
        "escalation_rate": escalation_rate,
        "abstention_rate": abstention_rate,
        "n_auto_with_label": n_auto_with_label,
        "n_auto_errors": n_auto_errors,
        "auto_error_rate": auto_error_rate,
        "overall_error_rate": overall_error_rate,
        "expected_cost": float(expected_cost),
        "expected_cost_per_item": expected_cost_per_item,
    }


def evaluate_grouped(
    records: Iterable[Any],
    *,
    group_key: str = "risk_tier",
    costs: CostConfig = CostConfig(),
    decision_key: str = "decision",
    y_true_key: str = "y_true",
    y_pred_key: str = "y_pred",
) -> Dict[str, Any]:
    """Evaluate overall metrics plus per-group metrics (e.g., by risk tier)."""
    recs = list(records)
    overall = evaluate_records(
        recs, costs=costs, decision_key=decision_key, y_true_key=y_true_key, y_pred_key=y_pred_key
    )

    groups: Dict[str, List[Any]] = {}
    for r in recs:
        g = _get(r, group_key, "unknown")
        g = "unknown" if g is None else str(g)
        groups.setdefault(g, []).append(r)

    by_group = {
        g: evaluate_records(
            rs, costs=costs, decision_key=decision_key, y_true_key=y_true_key, y_pred_key=y_pred_key
        )
        for g, rs in sorted(groups.items(), key=lambda kv: kv[0])
    }
    return {"overall": overall, "by_group": by_group}
