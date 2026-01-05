"""threshold_sweep.py

Runs threshold sweeps across risk tiers and aggregates metrics to estimate
human-review cost versus error under different routing thresholds.

Input is typically JSONL where each line represents a claim with at least:
- risk_tier: str
- uncertainty: float in [0, 1] (or provide a custom getter)
- correct: bool (model's auto-answer correctness if auto-answered)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import argparse
import json
from pathlib import Path


@dataclass(frozen=True)
class TierCosts:
    tier: str
    review_cost: float = 1.0
    abstain_cost: float = 0.25
    auto_cost: float = 0.0


def _as_dict(rec: Any) -> Dict[str, Any]:
    if isinstance(rec, dict):
        return rec
    if hasattr(rec, "__dict__"):
        return dict(rec.__dict__)
    raise TypeError(f"Unsupported record type: {type(rec)!r}")


def default_get_uncertainty(rec: Any) -> float:
    d = _as_dict(rec)
    for k in ("uncertainty", "risk", "risk_score", "u"):
        if k in d:
            return float(d[k])
    raise KeyError("Missing uncertainty field (expected one of: uncertainty, risk, risk_score, u)")


def default_get_tier(rec: Any) -> str:
    d = _as_dict(rec)
    for k in ("risk_tier", "tier", "riskTier"):
        if k in d:
            return str(d[k])
    return "default"


def default_get_correct(rec: Any) -> Optional[bool]:
    d = _as_dict(rec)
    for k in ("correct", "is_correct", "label_correct", "y_true"):
        if k in d:
            v = d[k]
            if v is None:
                return None
            return bool(v)
    return None


def route(uncertainty: float, t_auto: float, t_abstain: Optional[float] = None) -> str:
    """Return one of: 'auto', 'escalate', 'abstain'."""
    if t_abstain is not None and uncertainty >= t_abstain:
        return "abstain"
    if uncertainty <= t_auto:
        return "auto"
    return "escalate"


def evaluate(
    records: Sequence[Any],
    t_auto: float,
    t_abstain: Optional[float],
    costs_by_tier: Mapping[str, TierCosts],
    get_uncertainty: Callable[[Any], float] = default_get_uncertainty,
    get_tier: Callable[[Any], str] = default_get_tier,
    get_correct: Callable[[Any], Optional[bool]] = default_get_correct,
) -> Dict[str, Any]:
    n = len(records)
    auto = esc = abst = 0
    incorrect_auto = 0
    unknown_correct = 0
    cost = 0.0
    for r in records:
        u = float(get_uncertainty(r))
        tier = get_tier(r)
        c = costs_by_tier.get(tier) or costs_by_tier.get("default") or TierCosts(tier=tier)
        decision = route(u, t_auto=t_auto, t_abstain=t_abstain)
        if decision == "auto":
            auto += 1
            cost += c.auto_cost
            corr = get_correct(r)
            if corr is None:
                unknown_correct += 1
            elif not corr:
                incorrect_auto += 1
        elif decision == "escalate":
            esc += 1
            cost += c.review_cost
        else:
            abst += 1
            cost += c.abstain_cost
    denom = max(n, 1)
    return {
        "n": n,
        "t_auto": float(t_auto),
        "t_abstain": None if t_abstain is None else float(t_abstain),
        "coverage_auto": auto / denom,
        "escalation_rate": esc / denom,
        "abstention_rate": abst / denom,
        "error_rate": incorrect_auto / denom,
        "incorrect_auto": int(incorrect_auto),
        "unknown_correct": int(unknown_correct),
        "expected_cost": float(cost),
    }


def sweep(
    records: Sequence[Any],
    thresholds_auto: Sequence[float],
    thresholds_abstain: Optional[Sequence[Optional[float]]] = None,
    costs_by_tier: Optional[Mapping[str, TierCosts]] = None,
    get_uncertainty: Callable[[Any], float] = default_get_uncertainty,
    get_tier: Callable[[Any], str] = default_get_tier,
    get_correct: Callable[[Any], Optional[bool]] = default_get_correct,
) -> List[Dict[str, Any]]:
    costs_by_tier = dict(costs_by_tier or {})
    if "default" not in costs_by_tier:
        costs_by_tier["default"] = TierCosts(tier="default")

    tiers: Dict[str, List[Any]] = {}
    for r in records:
        tiers.setdefault(get_tier(r), []).append(r)

    if thresholds_abstain is None:
        thresholds_abstain = [None]

    out: List[Dict[str, Any]] = []
    for tier, recs in sorted(tiers.items()):
        for t_auto in thresholds_auto:
            for t_abstain in thresholds_abstain:
                if t_abstain is not None and float(t_abstain) < float(t_auto):
                    continue
                row = evaluate(
                    recs, float(t_auto), None if t_abstain is None else float(t_abstain),
                    costs_by_tier=costs_by_tier,
                    get_uncertainty=get_uncertainty, get_tier=get_tier, get_correct=get_correct,
                )
                row["risk_tier"] = tier
                out.append(row)

    # overall aggregate
    for t_auto in thresholds_auto:
        for t_abstain in thresholds_abstain:
            if t_abstain is not None and float(t_abstain) < float(t_auto):
                continue
            row = evaluate(
                records, float(t_auto), None if t_abstain is None else float(t_abstain),
                costs_by_tier=costs_by_tier,
                get_uncertainty=get_uncertainty, get_tier=get_tier, get_correct=get_correct,
            )
            row["risk_tier"] = "__overall__"
            out.append(row)

    return out


def _parse_floats(spec: str) -> List[float]:
    spec = (spec or "").strip()
    if not spec:
        return []
    if ":" in spec:
        a, b, c = spec.split(":")
        start, stop, step = float(a), float(b), float(c)
        if step <= 0:
            raise ValueError("step must be > 0")
        xs = []
        x = start
        while x <= stop + 1e-12:
            xs.append(round(x, 10))
            x += step
        return xs
    return [float(x.strip()) for x in spec.split(",") if x.strip()]


def _parse_costs(spec: str) -> Dict[str, TierCosts]:
    # Format: tier=review_cost[,abstain_cost][;tier2=...]
    out: Dict[str, TierCosts] = {}
    spec = (spec or "").strip()
    if not spec:
        return out
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        tier, rhs = part.split("=", 1)
        vals = [v.strip() for v in rhs.split(",") if v.strip()]
        review = float(vals[0]) if vals else 1.0
        abstain = float(vals[1]) if len(vals) > 1 else 0.25
        auto = float(vals[2]) if len(vals) > 2 else 0.0
        out[tier.strip()] = TierCosts(tier=tier.strip(), review_cost=review, abstain_cost=abstain, auto_cost=auto)
    return out


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Run threshold sweeps for routing policy across risk tiers.")
    ap.add_argument("--input", type=str, required=True, help="Path to JSONL with per-claim fields.")
    ap.add_argument("--out", type=str, required=True, help="Path to write JSON results.")
    ap.add_argument("--thresholds-auto", type=str, default="0:1:0.05", help="Comma list or start:stop:step")
    ap.add_argument("--thresholds-abstain", type=str, default="", help="Optional comma list or start:stop:step; empty disables abstain tier")
    ap.add_argument("--costs", type=str, default="", help="Costs spec: tier=review,abstain,auto;tier2=...")
    args = ap.parse_args(argv)

    inp = Path(args.input)
    outp = Path(args.out)
    records = load_jsonl(inp)

    t_auto = _parse_floats(args.thresholds_auto)
    if not t_auto:
        raise SystemExit("No thresholds-auto provided.")
    t_abst = _parse_floats(args.thresholds_abstain) if args.thresholds_abstain.strip() else None
    if t_abst is not None and not t_abst:
        t_abst = None

    costs = _parse_costs(args.costs)
    results = sweep(records, thresholds_auto=t_auto, thresholds_abstain=t_abst, costs_by_tier=costs)

    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
