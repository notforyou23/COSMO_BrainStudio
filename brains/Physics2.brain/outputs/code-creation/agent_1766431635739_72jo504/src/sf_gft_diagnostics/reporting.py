"""Reporting utilities for spin-foam/GFT continuum-recovery diagnostics.

This module focuses on *reproducible* outputs: JSON bundles + CSV tables and
(optional) simple plots. It is intentionally lightweight and can consume
outputs produced by other parts of the package (observables/scaling/metrics).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import csv
import json
import math
import statistics

try:  # optional
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover
    _np = None

try:  # optional
    import matplotlib.pyplot as _plt  # type: ignore
except Exception:  # pragma: no cover
    _plt = None


def _as_records(x: Any) -> List[Dict[str, Any]]:
    """Normalize common container types into a list of dict records."""
    if x is None:
        return []
    if isinstance(x, list):
        return [dict(r) for r in x]
    if isinstance(x, dict):
        # dict-of-dicts or dict-of-scalars
        if all(isinstance(v, Mapping) for v in x.values()):
            return [dict(v, key=k) for k, v in x.items()]  # type: ignore[arg-type]
        return [dict(x)]
    raise TypeError(f"Unsupported record container: {type(x)!r}")


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    records = list(records)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    keys: List[str] = sorted({k for r in records for k in r.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in keys})


def _rank(records: List[Dict[str, Any]], key: str, reverse: bool = True) -> List[Dict[str, Any]]:
    def _val(r: Mapping[str, Any]) -> float:
        v = r.get(key, float("nan"))
        try:
            return float(v)
        except Exception:
            return float("nan")
    ranked = sorted(records, key=_val, reverse=reverse)
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i
    return ranked
def summarize_priorities(observables: Any) -> Dict[str, Any]:
    """Summarize/standardize a prioritized observable catalog.

    Expected record fields (best-effort): name, priority, family, estimator, notes.
    """
    recs = _as_records(observables)
    for r in recs:
        r.setdefault("priority", r.get("score", 0.0))
        r.setdefault("name", r.get("id", r.get("label", "")))
    ranked = _rank(recs, key="priority", reverse=True)
    top_families: Dict[str, int] = {}
    for r in ranked:
        fam = str(r.get("family", "unknown"))
        top_families[fam] = top_families.get(fam, 0) + 1
    return {"n": len(ranked), "top_families": top_families, "records": ranked}


def summarize_scaling_fits(fits: Any) -> Dict[str, Any]:
    """Summarize scaling-fit outputs.

    Expected fields per fit: observable/name, exponent/nu/eta, stderr, r2, chi2_red.
    """
    recs = _as_records(fits)
    for r in recs:
        r.setdefault("name", r.get("observable", r.get("id", "")))
        for k in ("exponent", "nu", "eta"):
            if k in r and "value" not in r:
                r["value"] = r[k]
        r.setdefault("stderr", r.get("se", r.get("sigma", None)))
        # heuristic fit-quality score: prefer high r2, low chi2
        r2 = float(r.get("r2", 0.0) or 0.0)
        chi = float(r.get("chi2_red", r.get("chi2", 1.0)) or 1.0)
        r["fit_score"] = r2 / max(chi, 1e-12)
    ranked = _rank(recs, key="fit_score", reverse=True)
    values = [float(r.get("value")) for r in ranked if _is_finite(r.get("value"))]
    return {
        "n": len(ranked),
        "value_mean": statistics.fmean(values) if values else None,
        "value_stdev": statistics.pstdev(values) if len(values) > 1 else None,
        "records": ranked,
    }


def _is_finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def summarize_cv(scores: Any) -> Dict[str, Any]:
    """Summarize cross-validation scores across diagnostics/models.

    Records should include: name/model, fold scores or mean/std already computed.
    """
    recs = _as_records(scores)
    for r in recs:
        r.setdefault("name", r.get("model", r.get("observable", r.get("id", ""))))
        if "folds" in r and isinstance(r["folds"], Sequence):
            vals = [float(v) for v in r["folds"] if _is_finite(v)]
            r["cv_mean"] = statistics.fmean(vals) if vals else None
            r["cv_std"] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        r.setdefault("cv_mean", r.get("score", None))
    ranked = _rank(recs, key="cv_mean", reverse=True)
    return {"n": len(ranked), "records": ranked}


def summarize_benchmarks(benchmarks: Any) -> Dict[str, Any]:
    """Summarize benchmark comparisons (semiclassical, TN/lattice RG, etc.).

    Records should include: name, metric, value, reference, and optionally tolerance.
    A normalized "z" score is computed when possible.
    """
    recs = _as_records(benchmarks)
    for r in recs:
        r.setdefault("name", r.get("observable", r.get("id", "")))
        val, ref = r.get("value"), r.get("reference")
        tol = r.get("tolerance", r.get("stderr", r.get("sigma", None)))
        if _is_finite(val) and _is_finite(ref) and _is_finite(tol) and float(tol) > 0:
            r["z"] = (float(val) - float(ref)) / float(tol)
            r["within_tol"] = abs(float(r["z"])) <= 1.0
        elif _is_finite(val) and _is_finite(ref):
            r["abs_err"] = abs(float(val) - float(ref))
    # prefer small |z|, else small abs_err
    for r in recs:
        z = r.get("z", None)
        r["bench_score"] = -abs(float(z)) if _is_finite(z) else -float(r.get("abs_err", float("inf")))
    ranked = _rank(recs, key="bench_score", reverse=True)
    return {"n": len(ranked), "records": ranked}
@dataclass(frozen=True)
class ReportPaths:
    out_dir: Path
    prefix: str = "sf_gft"

    def file(self, stem: str, ext: str) -> Path:
        return self.out_dir / f"{self.prefix}_{stem}.{ext.lstrip('.')}"


def generate_report_bundle(
    out_dir: str | Path,
    *,
    prefix: str = "sf_gft",
    observables: Any = None,
    scaling_fits: Any = None,
    cv_scores: Any = None,
    benchmarks: Any = None,
    make_plots: bool = True,
) -> Dict[str, Any]:
    """Create a compact report bundle (JSON + CSV + optional plots).

    Returns the in-memory summary dict that is also written to `<prefix>_report.json`.
    """
    paths = ReportPaths(Path(out_dir), prefix=prefix)
    paths.out_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {"schema": "sf_gft_diagnostics.report.v1"}
    if observables is not None:
        summary["observables"] = summarize_priorities(observables)
        _write_csv(paths.file("observables", "csv"), summary["observables"]["records"])
    if scaling_fits is not None:
        summary["scaling_fits"] = summarize_scaling_fits(scaling_fits)
        _write_csv(paths.file("scaling_fits", "csv"), summary["scaling_fits"]["records"])
    if cv_scores is not None:
        summary["cv_scores"] = summarize_cv(cv_scores)
        _write_csv(paths.file("cv_scores", "csv"), summary["cv_scores"]["records"])
    if benchmarks is not None:
        summary["benchmarks"] = summarize_benchmarks(benchmarks)
        _write_csv(paths.file("benchmarks", "csv"), summary["benchmarks"]["records"])

    _write_json(paths.file("report", "json"), summary)

    if make_plots and _plt is not None:
        _maybe_plot_top_observables(paths, summary.get("observables"))
        _maybe_plot_scaling_values(paths, summary.get("scaling_fits"))
    return summary


def _maybe_plot_top_observables(paths: ReportPaths, obs_summary: Optional[Mapping[str, Any]]) -> None:
    if not obs_summary:
        return
    recs = list(obs_summary.get("records", []))[:10]
    names = [str(r.get("name", "")) for r in recs]
    vals = [float(r.get("priority", 0.0) or 0.0) for r in recs]
    fig = _plt.figure(figsize=(8, 3.2))
    ax = fig.add_subplot(111)
    ax.bar(range(len(vals)), vals)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("priority")
    ax.set_title("Top continuum diagnostics (priority)")
    fig.tight_layout()
    fig.savefig(paths.file("observables_top", "png"), dpi=160)
    _plt.close(fig)


def _maybe_plot_scaling_values(paths: ReportPaths, fit_summary: Optional[Mapping[str, Any]]) -> None:
    if not fit_summary:
        return
    recs = [r for r in fit_summary.get("records", []) if _is_finite(r.get("value"))][:15]
    if not recs:
        return
    names = [str(r.get("name", "")) for r in recs]
    vals = [float(r.get("value")) for r in recs]
    err = [float(r.get("stderr")) if _is_finite(r.get("stderr")) else 0.0 for r in recs]
    fig = _plt.figure(figsize=(8, 3.2))
    ax = fig.add_subplot(111)
    ax.errorbar(range(len(vals)), vals, yerr=err, fmt="o", capsize=3)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("scaling value")
    ax.set_title("Scaling-fit values (with stderr if provided)")
    fig.tight_layout()
    fig.savefig(paths.file("scaling_values", "png"), dpi=160)
    _plt.close(fig)
