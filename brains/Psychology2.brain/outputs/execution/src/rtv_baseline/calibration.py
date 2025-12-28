"""Calibration utilities: temperature scaling / isotonic calibration + risk-tier thresholds.

This module is dependency-light (numpy only). Isotonic calibration uses sklearn if available.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import math
import numpy as np
EPS = 1e-12


def _sigmoid(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, -50, 50)
    return 1.0 / (1.0 + np.exp(-x))


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def log_loss_from_proba(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1.0 - EPS)
    y = np.asarray(y, dtype=float)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def expected_calibration_error(probs: Sequence[float], y: Sequence[int], n_bins: int = 15) -> float:
    p = np.asarray(probs, dtype=float)
    yv = np.asarray(y, dtype=float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = max(len(p), 1)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (p >= lo) & (p < hi) if i < n_bins - 1 else (p >= lo) & (p <= hi)
        if not np.any(mask):
            continue
        acc = float(np.mean(yv[mask]))
        conf = float(np.mean(p[mask]))
        w = float(np.sum(mask)) / n
        ece += w * abs(acc - conf)
    return float(ece)
class Calibrator:
    def fit(self, scores: Sequence[float], y: Sequence[int]) -> "Calibrator":
        raise NotImplementedError

    def predict_proba(self, scores: Sequence[float]) -> np.ndarray:
        raise NotImplementedError
@dataclass
class TemperatureCalibrator(Calibrator):
    temperature: float = 1.0
    input_is_prob: bool = True

    def fit(self, scores: Sequence[float], y: Sequence[int]) -> "TemperatureCalibrator":
        s = np.asarray(scores, dtype=float)
        yv = np.asarray(y, dtype=float)
        logits = _logit(s) if self.input_is_prob else s

        def obj(logT: float) -> float:
            T = float(np.exp(logT))
            p = _sigmoid(logits / max(T, EPS))
            return log_loss_from_proba(p, yv)

        # Golden section search on log(T)
        a, b = math.log(0.05), math.log(20.0)
        gr = (math.sqrt(5.0) + 1.0) / 2.0
        c = b - (b - a) / gr
        d = a + (b - a) / gr
        fc, fd = obj(c), obj(d)
        for _ in range(80):
            if abs(b - a) < 1e-6:
                break
            if fc < fd:
                b, d, fd = d, c, fc
                c = b - (b - a) / gr
                fc = obj(c)
            else:
                a, c, fc = c, d, fd
                d = a + (b - a) / gr
                fd = obj(d)
        logT = (a + b) / 2.0
        self.temperature = float(np.exp(logT))
        return self

    def predict_proba(self, scores: Sequence[float]) -> np.ndarray:
        s = np.asarray(scores, dtype=float)
        logits = _logit(s) if self.input_is_prob else s
        T = max(float(self.temperature), EPS)
        return _sigmoid(logits / T)
@dataclass
class IsotonicCalibrator(Calibrator):
    _iso: object = None  # sklearn.isotonic.IsotonicRegression

    def fit(self, scores: Sequence[float], y: Sequence[int]) -> "IsotonicCalibrator":
        try:
            from sklearn.isotonic import IsotonicRegression  # type: ignore
        except Exception as e:  # pragma: no cover
            raise ImportError("Isotonic calibration requires scikit-learn") from e
        s = np.asarray(scores, dtype=float)
        yv = np.asarray(y, dtype=float)
        self._iso = IsotonicRegression(out_of_bounds="clip")
        self._iso.fit(s, yv)
        return self

    def predict_proba(self, scores: Sequence[float]) -> np.ndarray:
        if self._iso is None:
            raise RuntimeError("IsotonicCalibrator not fitted")
        s = np.asarray(scores, dtype=float)
        return np.asarray(self._iso.predict(s), dtype=float)
def fit_calibrator(
    method: str, scores: Sequence[float], y: Sequence[int], *, input_is_prob: bool = True
) -> Calibrator:
    m = (method or "none").lower()
    if m in ("none", "identity", "raw"):
        return _IdentityCalibrator().fit(scores, y)
    if m in ("temp", "temperature", "temperature_scaling"):
        return TemperatureCalibrator(input_is_prob=input_is_prob).fit(scores, y)
    if m in ("iso", "isotonic"):
        return IsotonicCalibrator().fit(scores, y)
    raise ValueError(f"Unknown calibration method: {method}")


@dataclass
class _IdentityCalibrator(Calibrator):
    def fit(self, scores: Sequence[float], y: Sequence[int]) -> "_IdentityCalibrator":
        return self

    def predict_proba(self, scores: Sequence[float]) -> np.ndarray:
        return np.clip(np.asarray(scores, dtype=float), 0.0, 1.0)
def threshold_for_false_accept_budget(
    probs: Sequence[float], y: Sequence[int], budget: float, *, eps: float = 1e-9
) -> float:
    """Return threshold t such that FA rate among negatives (y==0) for accept(p>=t) is <= budget.

    If no negatives, return 0.0. If budget<=0, return just above max negative prob.
    """
    p = np.asarray(probs, dtype=float)
    yv = np.asarray(y, dtype=int)
    neg = p[yv == 0]
    if neg.size == 0:
        return 0.0
    b = float(np.clip(budget, 0.0, 1.0))
    if b <= 0.0:
        return float(min(1.0, float(np.max(neg)) + eps))
    if b >= 1.0:
        return 0.0
    # Need P(neg >= t) <= b  -> choose t at (1-b) quantile of negatives
    q = float(np.quantile(neg, 1.0 - b, method="higher" if hasattr(np, "quantile") else "linear"))
    return float(np.clip(q, 0.0, 1.0))


def apply_threshold(probs: Sequence[float], threshold: float, *, abstain_label: str = "abstain") -> List[str]:
    p = np.asarray(probs, dtype=float)
    return ["accept" if float(x) >= float(threshold) else abstain_label for x in p]
def risk_tier_thresholds(
    rows: Sequence[Mapping],
    *,
    tier_key: str = "risk_tier",
    prob_key: str = "p_support",
    label_key: str = "is_supported",
    budgets: Mapping[str, float],
) -> Dict[str, float]:
    """Compute per-tier accept thresholds controlling false-accept under each tier budget."""
    out: Dict[str, float] = {}
    for tier, budget in budgets.items():
        ps, ys = [], []
        for r in rows:
            if r.get(tier_key) != tier:
                continue
            if prob_key not in r or label_key not in r:
                continue
            ps.append(float(r[prob_key]))
            ys.append(int(r[label_key]))
        out[str(tier)] = threshold_for_false_accept_budget(ps, ys, float(budget))
    return out


def summarize_thresholding(
    probs: Sequence[float], y: Sequence[int], threshold: float
) -> Dict[str, float]:
    p = np.asarray(probs, dtype=float)
    yv = np.asarray(y, dtype=int)
    accept = p >= float(threshold)
    n = max(len(p), 1)
    coverage = float(np.mean(accept)) if len(p) else 0.0
    fa = float(np.mean(accept[yv == 0])) if np.any(yv == 0) else 0.0
    ta = float(np.mean(accept[yv == 1])) if np.any(yv == 1) else 0.0
    return {"threshold": float(threshold), "coverage": coverage, "false_accept_rate": fa, "true_accept_rate": ta, "n": float(n)}
