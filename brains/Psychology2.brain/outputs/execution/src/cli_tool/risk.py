from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
import json
import math


class RiskConfigError(ValueError):
    """Raised when risk thresholds or inputs are invalid."""


def _is_finite_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _as_float(x: Any, *, name: str) -> float:
    if not _is_finite_number(x):
        raise RiskConfigError(f"{name} must be a finite number")
    return float(x)


def _sorted_items(m: Mapping[str, Any]) -> List[Tuple[str, Any]]:
    return sorted(m.items(), key=lambda kv: kv[0])


@dataclass(frozen=True)
class RiskThresholds:
    """Deterministic risk-threshold configuration.

    max_overall: fail if overall risk score > max_overall.
    per_metric: optional per-metric max score thresholds.
    """
    max_overall: float = 1.0
    per_metric: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        max_overall = _as_float(self.max_overall, name="max_overall")
        if max_overall < 0.0:
            raise RiskConfigError("max_overall must be >= 0")
        object.__setattr__(self, "max_overall", max_overall)

        pm: Dict[str, float] = {}
        for k, v in _sorted_items(dict(self.per_metric or {})):
            if not isinstance(k, str) or not k:
                raise RiskConfigError("per_metric keys must be non-empty strings")
            fv = _as_float(v, name=f"per_metric[{k}]")
            if fv < 0.0:
                raise RiskConfigError(f"per_metric[{k}] must be >= 0")
            pm[k] = fv
        object.__setattr__(self, "per_metric", pm)

    @staticmethod
    def from_cli(
        *,
        max_overall: Optional[float] = None,
        per_metric_json: Optional[str] = None,
        per_metric_kv: Optional[Iterable[str]] = None,
    ) -> "RiskThresholds":
        """Create thresholds from CLI inputs deterministically.

        per_metric_json: JSON object mapping metric->threshold.
        per_metric_kv: iterable of "metric=threshold" strings; merged over JSON.
        """
        pm: Dict[str, float] = {}
        if per_metric_json:
            try:
                obj = json.loads(per_metric_json)
            except Exception as e:
                raise RiskConfigError(f"Invalid per_metric_json: {e}") from e
            if not isinstance(obj, dict):
                raise RiskConfigError("per_metric_json must decode to an object")
            for k, v in obj.items():
                pm[str(k)] = _as_float(v, name=f"per_metric_json[{k}]")
        for kv in per_metric_kv or []:
            if "=" not in kv:
                raise RiskConfigError(f"Invalid per-metric threshold '{kv}', expected metric=threshold")
            k, v = kv.split("=", 1)
            k = k.strip()
            if not k:
                raise RiskConfigError(f"Invalid per-metric threshold '{kv}', empty metric name")
            pm[k] = _as_float(v.strip(), name=f"per_metric[{k}]")
        return RiskThresholds(max_overall=1.0 if max_overall is None else max_overall, per_metric=pm)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_overall": float(self.max_overall),
            "per_metric": {k: float(v) for k, v in _sorted_items(self.per_metric)},
        }


@dataclass(frozen=True)
class RiskDecision:
    passed: bool
    overall: float
    metrics: Mapping[str, float]
    thresholds: RiskThresholds
    violations: Tuple[str, ...] = ()

    def to_trace(self) -> Dict[str, Any]:
        return {
            "type": "risk_evaluation",
            "passed": bool(self.passed),
            "overall": float(self.overall),
            "metrics": {k: float(v) for k, v in _sorted_items(self.metrics)},
            "thresholds": self.thresholds.to_dict(),
            "violations": list(self.violations),
        }

    def to_manifest_fragment(self) -> Dict[str, Any]:
        return {
            "risk": {
                "passed": bool(self.passed),
                "overall": float(self.overall),
                "thresholds": self.thresholds.to_dict(),
                "violations": list(self.violations),
            }
        }


def evaluate_risk(
    metrics: Mapping[str, Any],
    *,
    thresholds: RiskThresholds,
    overall_metric: str = "overall",
) -> RiskDecision:
    """Evaluate metrics against thresholds with deterministic checks."""
    if not isinstance(metrics, Mapping):
        raise RiskConfigError("metrics must be a mapping")
    clean: Dict[str, float] = {}
    for k, v in _sorted_items({str(k): v for k, v in metrics.items()}):
        clean[k] = _as_float(v, name=f"metrics[{k}]")
        if clean[k] < 0.0:
            raise RiskConfigError(f"metrics[{k}] must be >= 0")

    overall = clean.get(overall_metric, None)
    if overall is None:
        overall = max(clean.values()) if clean else 0.0
    if not _is_finite_number(overall):
        raise RiskConfigError("overall risk must be a finite number")
    overall = float(overall)

    violations: List[str] = []
    if overall > thresholds.max_overall:
        violations.append(f"overall>{thresholds.max_overall}")

    for metric, max_allowed in _sorted_items(thresholds.per_metric):
        if metric in clean and clean[metric] > float(max_allowed):
            violations.append(f"{metric}>{float(max_allowed)}")

    return RiskDecision(
        passed=(len(violations) == 0),
        overall=overall,
        metrics=clean,
        thresholds=thresholds,
        violations=tuple(violations),
    )
