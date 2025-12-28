from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import math
@dataclass(frozen=True)
class ThresholdFit:
    threshold: float
    objective: str
    min_precision: Optional[float] = None
    min_recall: Optional[float] = None
    n: int = 0
    positives: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold": self.threshold,
            "objective": self.objective,
            "min_precision": self.min_precision,
            "min_recall": self.min_recall,
            "n": self.n,
            "positives": self.positives,
        }
def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def _confusion(y_true: Sequence[int], y_pred: Sequence[int]) -> Tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for yt, yp in zip(y_true, y_pred):
        if yt == 1 and yp == 1:
            tp += 1
        elif yt == 0 and yp == 1:
            fp += 1
        elif yt == 0 and yp == 0:
            tn += 1
        elif yt == 1 and yp == 0:
            fn += 1
    return tp, fp, tn, fn


def metrics_from_preds(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict[str, float]:
    tp, fp, tn, fn = _confusion(y_true, y_pred)
    prec = _safe_div(tp, tp + fp)
    rec = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * prec * rec, prec + rec)
    acc = _safe_div(tp + tn, tp + tn + fp + fn)
    fpr = _safe_div(fp, fp + tn)
    fnr = _safe_div(fn, fn + tp)
    return {
        "n": float(tp + fp + tn + fn),
        "tp": float(tp),
        "fp": float(fp),
        "tn": float(tn),
        "fn": float(fn),
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "accuracy": acc,
        "fpr": fpr,
        "fnr": fnr,
    }
def apply_threshold(scores: Sequence[float], threshold: float) -> List[int]:
    t = float(threshold)
    return [1 if (s is not None and float(s) >= t) else 0 for s in scores]


def sweep_thresholds(y_true: Sequence[int], scores: Sequence[float]) -> List[Dict[str, float]]:
    if len(y_true) != len(scores):
        raise ValueError("y_true and scores must be same length")
    pairs = [(1 if int(y) else 0, float(s)) for y, s in zip(y_true, scores)]
    uniq = sorted({s for _, s in pairs})
    if not uniq:
        return []
    candidates = sorted(set([1.0] + uniq + [max(0.0, min(1.0, uniq[0] - 1e-12))]))
    out: List[Dict[str, float]] = []
    for t in candidates:
        y_pred = [1 if s >= t else 0 for _, s in pairs]
        m = metrics_from_preds([y for y, _ in pairs], y_pred)
        m["threshold"] = float(t)
        out.append(m)
    return out


def fit_threshold(
    y_true: Sequence[int],
    scores: Sequence[float],
    objective: str = "f1",
    min_precision: Optional[float] = None,
    min_recall: Optional[float] = None,
) -> ThresholdFit:
    sweeps = sweep_thresholds(y_true, scores)
    if not sweeps:
        return ThresholdFit(threshold=1.0, objective=objective, min_precision=min_precision, min_recall=min_recall, n=0, positives=0)
    obj = objective.lower().strip()
    if obj not in {"f1", "accuracy", "precision", "recall"}:
        raise ValueError(f"Unsupported objective: {objective}")
    def ok(m: Dict[str, float]) -> bool:
        if min_precision is not None and m["precision"] + 1e-12 < float(min_precision):
            return False
        if min_recall is not None and m["recall"] + 1e-12 < float(min_recall):
            return False
        return True
    feasible = [m for m in sweeps if ok(m)]
    pool = feasible if feasible else sweeps
    # Deterministic tie-break: higher objective, then higher precision, then higher recall, then higher threshold.
    pool.sort(key=lambda m: (m[obj], m["precision"], m["recall"], m["threshold"]), reverse=True)
    best = pool[0]
    positives = sum(1 for y in y_true if int(y) == 1)
    return ThresholdFit(
        threshold=float(best["threshold"]),
        objective=obj,
        min_precision=min_precision,
        min_recall=min_recall,
        n=len(y_true),
        positives=positives,
    )
def _grouped(items: Iterable[Dict[str, Any]], group_key: Optional[str]) -> Dict[str, List[Dict[str, Any]]]:
    if not group_key:
        return {"__all__": list(items)}
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        g = it.get(group_key, "__missing__")
        gs = str(g)
        groups.setdefault(gs, []).append(it)
    return groups


def calibrate_thresholds(
    heldout: Sequence[Dict[str, Any]],
    *,
    score_key: str = "score",
    label_key: str = "label",
    group_key: Optional[str] = None,
    objective: str = "f1",
    min_precision: Optional[float] = None,
    min_recall: Optional[float] = None,
) -> Dict[str, Any]:
    groups = _grouped(heldout, group_key)
    fits: Dict[str, ThresholdFit] = {}
    for g, items in groups.items():
        y = [1 if int(it.get(label_key, 0)) else 0 for it in items]
        s = [float(it.get(score_key, 0.0)) for it in items]
        fits[g] = fit_threshold(y, s, objective=objective, min_precision=min_precision, min_recall=min_recall)
    return {
        "group_key": group_key,
        "score_key": score_key,
        "label_key": label_key,
        "objective": objective,
        "min_precision": min_precision,
        "min_recall": min_recall,
        "thresholds": {g: f.to_dict() for g, f in fits.items()},
    }


def evaluate_with_calibration(
    heldout: Sequence[Dict[str, Any]],
    calibration: Dict[str, Any],
    *,
    claim_id_key: str = "claim_id",
    evidence_failures_key: str = "evidence_failures",
) -> Dict[str, Any]:
    group_key = calibration.get("group_key")
    score_key = calibration.get("score_key", "score")
    label_key = calibration.get("label_key", "label")
    thr_map = {g: float(v["threshold"]) for g, v in (calibration.get("thresholds") or {}).items()}
    groups = _grouped(heldout, group_key)

    per_group: Dict[str, Any] = {}
    audit_events: List[Dict[str, Any]] = []
    for g, items in groups.items():
        t = thr_map.get(g, thr_map.get("__all__", 1.0))
        y = [1 if int(it.get(label_key, 0)) else 0 for it in items]
        s = [float(it.get(score_key, 0.0)) for it in items]
        yp = apply_threshold(s, t)
        m = metrics_from_preds(y, yp)
        m["threshold"] = float(t)
        per_group[g] = m
        for it, pred in zip(items, yp):
            label = 1 if int(it.get(label_key, 0)) else 0
            if pred != label:
                audit_events.append(
                    {
                        "claim_id": it.get(claim_id_key),
                        "group": g,
                        "label": label,
                        "pred": int(pred),
                        "score": float(it.get(score_key, 0.0)),
                        "threshold": float(t),
                        "evidence_failures": it.get(evidence_failures_key, []),
                    }
                )

    # Aggregate across all
    y_all = [1 if int(it.get(label_key, 0)) else 0 for it in heldout]
    s_all = [float(it.get(score_key, 0.0)) for it in heldout]
    t_all = thr_map.get("__all__", thr_map.get(next(iter(thr_map), "__all__"), 1.0))
    yp_all = apply_threshold(s_all, t_all)
    agg = metrics_from_preds(y_all, yp_all)
    agg["threshold_used_for_aggregate"] = float(t_all)

    return {
        "aggregate": agg,
        "per_group": per_group,
        "audit_mismatches": audit_events,
        "audit_mismatches_n": len(audit_events),
    }
def load_jsonl(path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
