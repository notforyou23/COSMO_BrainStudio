"""Evaluation utilities for verifier benchmark runs.

Computes:
- Error-detection metrics: precision/recall/F1, AUROC, AUPRC
- Calibration: reliability bins + ECE
- Failure-mode slices: per-key group metrics

Expected record fields (flexible):
- score: one of ['error_score','verifier_score','score','p_error']
- label: one of ['is_error','error','label'] OR 'is_correct' (inverted)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import math
def _get_first(d: Dict[str, Any], keys: Sequence[str], default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _as_float(x, default=None):
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _as_bool(x, default=None):
    if x is None:
        return default
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return bool(int(x))
    if isinstance(x, str):
        s = x.strip().lower()
        if s in ("1", "true", "t", "yes", "y"):
            return True
        if s in ("0", "false", "f", "no", "n"):
            return False
    return default
def _labels_scores_from_records(
    records: Iterable[Dict[str, Any]],
    score_key: Optional[str] = None,
    label_key: Optional[str] = None,
) -> Tuple[List[int], List[float]]:
    ys: List[int] = []
    ss: List[float] = []
    for r in records:
        if score_key:
            s = _as_float(r.get(score_key))
        else:
            s = _as_float(_get_first(r, ["error_score", "verifier_score", "score", "p_error", "prob_error"]))
        if s is None:
            continue
        if label_key:
            lab = r.get(label_key)
            b = _as_bool(lab, default=None)
            if b is None and isinstance(lab, (int, float)):
                b = bool(int(lab))
        else:
            b = _as_bool(_get_first(r, ["is_error", "error", "label"]), default=None)
            if b is None:
                ic = _as_bool(_get_first(r, ["is_correct", "correct", "gold_correct"]), default=None)
                if ic is not None:
                    b = (not ic)
        if b is None:
            continue
        ys.append(1 if b else 0)
        ss.append(float(s))
    return ys, ss
def precision_recall_f1(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict[str, float]:
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) else 0.0
    return {"precision": prec, "recall": rec, "f1": f1, "tp": float(tp), "fp": float(fp), "fn": float(fn)}


def _pairwise_rank_auc(y_true: Sequence[int], y_score: Sequence[float]) -> float:
    pairs = sorted(zip(y_score, y_true), key=lambda x: x[0])
    n_pos = sum(1 for _, y in pairs if y == 1)
    n_neg = len(pairs) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    i = 0
    rank_sum_pos = 0.0
    rank = 1
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        avg_rank = (rank + (rank + (j - i) - 1)) / 2.0
        cnt_pos = sum(1 for k in range(i, j) if pairs[k][1] == 1)
        rank_sum_pos += cnt_pos * avg_rank
        rank += (j - i)
        i = j
    u = rank_sum_pos - (n_pos * (n_pos + 1) / 2.0)
    return u / (n_pos * n_neg)


def auprc(y_true: Sequence[int], y_score: Sequence[float]) -> float:
    items = sorted(zip(y_score, y_true), key=lambda x: x[0], reverse=True)
    n_pos = sum(y_true)
    if n_pos == 0:
        return float("nan")
    tp = fp = 0
    last_score = None
    points: List[Tuple[float, float]] = [(0.0, 1.0)]
    for s, y in items:
        if last_score is not None and s != last_score:
            prec = tp / (tp + fp) if (tp + fp) else 1.0
            rec = tp / n_pos
            points.append((rec, prec))
        if y == 1:
            tp += 1
        else:
            fp += 1
        last_score = s
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / n_pos
    points.append((rec, prec))
    area = 0.0
    for (r1, p1), (r2, p2) in zip(points, points[1:]):
        area += (r2 - r1) * p2
    return area
def best_f1_threshold(y_true: Sequence[int], y_score: Sequence[float]) -> Dict[str, float]:
    if not y_true:
        return {"threshold": float("nan"), "precision": float("nan"), "recall": float("nan"), "f1": float("nan")}
    items = sorted(zip(y_score, y_true), key=lambda x: x[0], reverse=True)
    n_pos = sum(y_true)
    tp = fp = 0
    best = {"threshold": float("inf"), "precision": 0.0, "recall": 0.0, "f1": 0.0}
    for i, (s, y) in enumerate(items):
        if y == 1:
            tp += 1
        else:
            fp += 1
        next_s = items[i + 1][0] if i + 1 < len(items) else None
        if next_s is not None and next_s == s:
            continue
        fn = n_pos - tp
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) else 0.0
        if f1 > best["f1"]:
            best = {"threshold": float(s), "precision": prec, "recall": rec, "f1": f1}
    return best


def reliability_bins(y_true: Sequence[int], y_prob: Sequence[float], n_bins: int = 10) -> Dict[str, Any]:
    n = len(y_true)
    if n == 0:
        return {"n": 0, "n_bins": n_bins, "bins": [], "ece": float("nan")}
    bins = []
    ece = 0.0
    for b in range(n_bins):
        lo = b / n_bins
        hi = (b + 1) / n_bins
        idx = [i for i, p in enumerate(y_prob) if (p >= lo and (p < hi or (b == n_bins - 1 and p <= hi)))]
        if not idx:
            bins.append({"bin": b, "lo": lo, "hi": hi, "count": 0, "avg_p": float("nan"), "emp_rate": float("nan")})
            continue
        avg_p = sum(y_prob[i] for i in idx) / len(idx)
        emp = sum(y_true[i] for i in idx) / len(idx)
        ece += (len(idx) / n) * abs(emp - avg_p)
        bins.append({"bin": b, "lo": lo, "hi": hi, "count": len(idx), "avg_p": avg_p, "emp_rate": emp})
    return {"n": n, "n_bins": n_bins, "bins": bins, "ece": ece}
def evaluate_error_detection(
    records: Iterable[Dict[str, Any]],
    score_key: Optional[str] = None,
    label_key: Optional[str] = None,
    threshold: float = 0.5,
    n_bins: int = 10,
) -> Dict[str, Any]:
    y, s = _labels_scores_from_records(records, score_key=score_key, label_key=label_key)
    if not y:
        return {"n": 0, "threshold": threshold, "point": {}, "best_f1": {}, "auroc": float("nan"), "auprc": float("nan"), "calibration": {}}
    y_pred = [1 if p >= threshold else 0 for p in s]
    point = precision_recall_f1(y, y_pred)
    best = best_f1_threshold(y, s)
    return {
        "n": len(y),
        "pos": float(sum(y)),
        "threshold": float(threshold),
        "point": point,
        "best_f1": best,
        "auroc": _pairwise_rank_auc(y, s),
        "auprc": auprc(y, s),
        "calibration": reliability_bins(y, s, n_bins=n_bins),
    }


def slice_metrics(
    records: Sequence[Dict[str, Any]],
    slice_keys: Sequence[str],
    min_n: int = 20,
    **eval_kwargs,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {"slices": {}, "keys": list(slice_keys), "min_n": int(min_n)}
    for k in slice_keys:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in records:
            v = r.get(k, None)
            if v is None:
                v = "__MISSING__"
            v = str(v)
            groups.setdefault(v, []).append(r)
        out["slices"][k] = {}
        for v, grp in groups.items():
            if len(grp) < min_n:
                continue
            out["slices"][k][v] = evaluate_error_detection(grp, **eval_kwargs)
    return out
