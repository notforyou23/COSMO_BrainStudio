from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import json
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _as_np(x: Any) -> np.ndarray:
    if x is None:
        return np.array([], dtype=float)
    if isinstance(x, np.ndarray):
        return x.astype(float)
    return np.asarray(list(x), dtype=float)


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _savefig(fig: plt.Figure, out_path: Path, formats: Tuple[str, ...] = ("png", "svg"), dpi: int = 200) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stem = out_path.with_suffix("")
    for ext in formats:
        fig.savefig(stem.with_suffix(f".{ext}"), bbox_inches="tight", dpi=dpi)
    plt.close(fig)


def _bin_stats(y_true: np.ndarray, y_score: np.ndarray, n_bins: int = 10) -> Dict[str, np.ndarray]:
    y_true = _as_np(y_true)
    y_score = _as_np(y_score)
    if y_true.size == 0 or y_score.size == 0:
        return {"bin_centers": np.array([]), "acc": np.array([]), "conf": np.array([]), "counts": np.array([]), "ece": np.array([np.nan])}
    y_score = np.clip(y_score, 0.0, 1.0)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_ids = np.digitize(y_score, edges[1:-1], right=True)
    acc, conf, counts = [], [], []
    ece = 0.0
    for b in range(n_bins):
        m = bin_ids == b
        c = int(m.sum())
        counts.append(c)
        if c == 0:
            acc.append(np.nan)
            conf.append(np.nan)
            continue
        a = float(np.mean(y_true[m] > 0.5))
        q = float(np.mean(y_score[m]))
        acc.append(a)
        conf.append(q)
        ece += (c / y_true.size) * abs(a - q)
    centers = (edges[:-1] + edges[1:]) / 2
    return {"bin_centers": centers, "acc": np.array(acc), "conf": np.array(conf), "counts": np.array(counts), "ece": np.array([ece])}


def plot_reliability_curve(
    y_true: Iterable[float],
    y_score: Iterable[float],
    out_path: Path,
    n_bins: int = 10,
    title: str = "Reliability (Calibration) Curve",
    formats: Tuple[str, ...] = ("png", "svg"),
) -> Dict[str, float]:
    s = _bin_stats(_as_np(y_true), _as_np(y_score), n_bins=n_bins)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1, label="Perfect")
    x = s["conf"]
    y = s["acc"]
    m = ~np.isnan(x) & ~np.isnan(y)
    ax.plot(x[m], y[m], marker="o", linewidth=2, label="Model")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ece = float(s["ece"][0]) if s["ece"].size else float("nan")
    ax.set_title(f"{title}\nECE={ece:.4f}" if np.isfinite(ece) else title)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Empirical accuracy")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", frameon=False)
    _savefig(fig, out_path, formats=formats)
    return {"ece": ece}


def _try_sklearn_curves(y_true: np.ndarray, y_score: np.ndarray):
    try:
        from sklearn.metrics import roc_curve, precision_recall_curve, auc
        fpr, tpr, _ = roc_curve(y_true, y_score)
        p, r, _ = precision_recall_curve(y_true, y_score)
        roc_auc = float(auc(fpr, tpr))
        pr_auc = float(auc(r, p))
        return (fpr, tpr, roc_auc), (r, p, pr_auc)
    except Exception:
        return None, None


def _manual_pr_roc(y_true: np.ndarray, y_score: np.ndarray):
    order = np.argsort(-y_score)
    y = (y_true[order] > 0.5).astype(int)
    s = y_score[order]
    tp = np.cumsum(y)
    fp = np.cumsum(1 - y)
    fn = tp[-1] - tp
    tn = fp[-1] - fp
    tpr = tp / np.maximum(tp + fn, 1)
    fpr = fp / np.maximum(fp + tn, 1)
    prec = tp / np.maximum(tp + fp, 1)
    rec = tpr
    def _auc(x, y):
        idx = np.argsort(x)
        return float(np.trapz(y[idx], x[idx]))
    return (fpr, tpr, _auc(fpr, tpr)), (rec, prec, _auc(rec, prec))


def plot_pr_roc(
    y_true: Iterable[float],
    y_score: Iterable[float],
    out_path_prefix: Path,
    title_prefix: str = "Error Detection",
    formats: Tuple[str, ...] = ("png", "svg"),
) -> Dict[str, float]:
    y_true = _as_np(y_true)
    y_score = _as_np(y_score)
    if y_true.size == 0 or y_score.size == 0:
        return {"roc_auc": float("nan"), "pr_auc": float("nan")}
    y_bin = (y_true > 0.5).astype(int)
    sk_roc, sk_pr = _try_sklearn_curves(y_bin, y_score)
    if sk_roc is None or sk_pr is None:
        sk_roc, sk_pr = _manual_pr_roc(y_bin, y_score)
    fpr, tpr, roc_auc = sk_roc
    rec, prec, pr_auc = sk_pr

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(fpr, tpr, linewidth=2, label=f"AUC={roc_auc:.4f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
    ax.set_title(f"{title_prefix}: ROC")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", frameon=False)
    _savefig(fig, out_path_prefix.with_suffix("").with_name(out_path_prefix.name + "_roc"), formats=formats)

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(rec, prec, linewidth=2, label=f"AUC={pr_auc:.4f}")
    ax.set_title(f"{title_prefix}: Precision-Recall")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower left", frameon=False)
    _savefig(fig, out_path_prefix.with_suffix("").with_name(out_path_prefix.name + "_pr"), formats=formats)

    return {"roc_auc": float(roc_auc), "pr_auc": float(pr_auc)}


def plot_failure_modes_bar(
    failure_modes: Dict[str, Any],
    out_path: Path,
    title: str = "Failure Modes",
    formats: Tuple[str, ...] = ("png", "svg"),
    top_k: int = 12,
) -> Dict[str, Any]:
    if not isinstance(failure_modes, dict) or not failure_modes:
        return {"n_modes": 0}
    items = [(str(k), float(v)) for k, v in failure_modes.items() if v is not None]
    items.sort(key=lambda kv: kv[1], reverse=True)
    items = items[:max(1, int(top_k))]
    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    fig_h = max(3.0, 0.35 * len(labels) + 1.5)
    fig, ax = plt.subplots(figsize=(7, fig_h))
    y = np.arange(len(labels))
    ax.barh(y, vals, color="#4C78A8")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Count")
    ax.set_title(title)
    ax.grid(True, axis="x", alpha=0.25)
    _savefig(fig, out_path, formats=formats)
    return {"n_modes": len(failure_modes)}


def generate_diagnostic_plots(
    metrics: Dict[str, Any],
    out_dir: Path,
    prefix: str = "",
    formats: Tuple[str, ...] = ("png", "svg"),
) -> Dict[str, Any]:
    out_dir = _ensure_dir(Path(out_dir))
    pfx = (prefix + "_") if prefix else ""
    results: Dict[str, Any] = {"plots": {}}

    # Expected shapes:
    # metrics["error_detection"] = {"y_true": [...], "y_score": [...]}
    # metrics["calibration"] may alias error_detection or contain its own
    ed = metrics.get("error_detection") or {}
    cal = metrics.get("calibration") or ed

    y_true = cal.get("y_true")
    y_score = cal.get("y_score")
    if y_true is not None and y_score is not None:
        results["plots"]["reliability"] = plot_reliability_curve(
            y_true, y_score, out_dir / f"{pfx}reliability", formats=formats
        )
        results["plots"]["pr_roc"] = plot_pr_roc(
            ed.get("y_true", y_true), ed.get("y_score", y_score), out_dir / f"{pfx}error_detection", formats=formats
        )

    fm = metrics.get("failure_modes") or metrics.get("failure_mode_counts")
    if isinstance(fm, dict) and fm:
        results["plots"]["failure_modes"] = plot_failure_modes_bar(
            fm, out_dir / f"{pfx}failure_modes", formats=formats
        )

    return results


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main(argv: Optional[Iterable[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Generate calibration/diagnostic plots from aggregated metrics JSON.")
    ap.add_argument("metrics_json", type=str, help="Path to aggregated metrics JSON.")
    ap.add_argument("out_dir", type=str, help="Output directory for plots.")
    ap.add_argument("--prefix", type=str, default="", help="Filename prefix for plot artifacts.")
    ap.add_argument("--formats", type=str, default="png,svg", help="Comma-separated formats (e.g., png,svg).")
    args = ap.parse_args(list(argv) if argv is not None else None)
    fmts = tuple([s.strip() for s in args.formats.split(",") if s.strip()])
    metrics = _load_json(Path(args.metrics_json))
    generate_diagnostic_plots(metrics, Path(args.out_dir), prefix=args.prefix, formats=fmts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
