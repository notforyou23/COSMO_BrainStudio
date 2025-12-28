"""claims_audit.metrics

Compute tiered claim-audit metrics (coverage/abstain/false-accept + confusion matrices)
grouped by confidence tiers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

DEFAULT_LABELS: Tuple[str, ...] = ("supported", "unsupported", "insufficient")
ABSTAIN_LABELS: Tuple[str, ...] = ("abstain", "unknown", "none", "")


def _norm_label(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip().lower()
    if s in ABSTAIN_LABELS:
        return None
    return s


def _coerce_float(x: Any) -> float:
    try:
        v = float(x)
    except Exception:
        return float("nan")
    return v


def _format_tier(lo: float, hi: float) -> str:
    hi_s = "1.00" if hi >= 1.0 else f"{hi:.2f}"
    return f"{lo:.2f}-{hi_s}"


def build_tiers(thresholds: Sequence[float]) -> List[Tuple[float, float, str]]:
    ts = sorted(float(t) for t in thresholds)
    if not ts:
        ts = [0.0, 1.0]
    if ts[0] > 0.0:
        ts = [0.0] + ts
    if ts[-1] < 1.0:
        ts = ts + [1.0]
    tiers: List[Tuple[float, float, str]] = []
    for lo, hi in zip(ts[:-1], ts[1:]):
        tiers.append((lo, hi, _format_tier(lo, hi)))
    return tiers


def tier_for_confidence(conf: Any, tiers: Sequence[Tuple[float, float, str]]) -> str:
    c = _coerce_float(conf)
    if c != c:
        return "nan"
    if c < 0:
        c = 0.0
    if c > 1:
        c = 1.0
    for lo, hi, name in tiers:
        if (c >= lo and c < hi) or (hi >= 1.0 and c >= lo and c <= hi):
            return name
    return tiers[-1][2] if tiers else "all"


def _init_confusion(labels: Sequence[str]) -> Dict[str, Dict[str, int]]:
    lab = list(labels) + ["abstain"]
    return {t: {p: 0 for p in lab} for t in lab}


def _safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else 0.0


@dataclass(frozen=True)
class MetricConfig:
    thresholds: Tuple[float, ...] = (0.0, 0.5, 0.8, 0.9, 1.0)
    labels: Tuple[str, ...] = DEFAULT_LABELS
    accept_label: str = "supported"


def compute_tiered_metrics(
    rows: Iterable[Mapping[str, Any]],
    *,
    config: MetricConfig = MetricConfig(),
    true_key: str = "true_label",
    pred_key: str = "pred_label",
    conf_key: str = "confidence",
) -> Dict[str, Any]:
    tiers = build_tiers(config.thresholds)
    labels = tuple(str(x).strip().lower() for x in config.labels)
    accept = str(config.accept_label).strip().lower()

    per_tier: Dict[str, MutableMapping[str, Any]] = {}

    def get_bucket(tier_name: str) -> MutableMapping[str, Any]:
        b = per_tier.get(tier_name)
        if b is None:
            b = per_tier[tier_name] = {
                "n": 0,
                "n_abstain": 0,
                "n_covered": 0,
                "n_accept": 0,
                "n_false_accept": 0,
                "confusion": _init_confusion(labels),
            }
        return b

    overall = get_bucket("overall")

    for r in rows:
        t = _norm_label(r.get(true_key))
        p = _norm_label(r.get(pred_key))
        conf = r.get(conf_key)
        tier = tier_for_confidence(conf, tiers)

        for name in (tier, "overall"):
            b = get_bucket(name)
            b["n"] += 1
            true_l = t if t in labels else "abstain"
            pred_l = p if p in labels else "abstain"
            b["confusion"][true_l][pred_l] += 1

            if p is None:
                b["n_abstain"] += 1
            else:
                b["n_covered"] += 1
                if p == accept:
                    b["n_accept"] += 1
                    if t != accept:
                        b["n_false_accept"] += 1

    def finalize(b: Mapping[str, Any]) -> Dict[str, Any]:
        n = int(b["n"])
        n_abs = int(b["n_abstain"])
        n_cov = int(b["n_covered"])
        n_acc = int(b["n_accept"])
        n_fa = int(b["n_false_accept"])
        out = dict(b)
        out["coverage"] = _safe_div(n_cov, n)
        out["abstain_rate"] = _safe_div(n_abs, n)
        out["false_accept_rate"] = _safe_div(n_fa, n_acc)
        out["false_accept_overall_rate"] = _safe_div(n_fa, n)
        return out

    tiered = {k: finalize(v) for k, v in per_tier.items()}

    summary = {
        "n": tiered["overall"]["n"],
        "coverage": tiered["overall"]["coverage"],
        "abstain_rate": tiered["overall"]["abstain_rate"],
        "false_accept_rate": tiered["overall"]["false_accept_rate"],
        "false_accept_overall_rate": tiered["overall"]["false_accept_overall_rate"],
    }

    return {"config": config.__dict__, "tiers": [t[2] for t in tiers], "by_tier": tiered, "summary": summary}
