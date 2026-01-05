#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _ensure_toy_csv(csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if csv_path.exists():
        return
    df = pd.DataFrame(
        {
            "study": ["Study A", "Study B", "Study C", "Study D", "Study E", "Study F", "Study G", "Study H"],
            "yi":    [-0.20,     -0.05,     0.10,      -0.12,     0.02,      0.18,      -0.30,     0.07],
            "sei":   [0.12,      0.10,      0.15,      0.11,      0.09,      0.14,      0.20,      0.13],
        }
    )
    df.to_csv(csv_path, index=False)


def _pool_fixed(yi: np.ndarray, vi: np.ndarray) -> dict:
    w = 1.0 / vi
    mu = np.sum(w * yi) / np.sum(w)
    se = float(np.sqrt(1.0 / np.sum(w)))
    ci = (float(mu - 1.96 * se), float(mu + 1.96 * se))
    return {"model": "fixed", "mu": float(mu), "se": se, "ci_low": ci[0], "ci_high": ci[1], "tau2": 0.0}


def _heterogeneity(yi: np.ndarray, vi: np.ndarray, mu_fixed: float) -> dict:
    w = 1.0 / vi
    q = float(np.sum(w * (yi - mu_fixed) ** 2))
    df = max(0, int(len(yi) - 1))
    c = float(np.sum(w) - (np.sum(w**2) / np.sum(w)))
    tau2 = float(max(0.0, (q - df) / c)) if c > 0 else 0.0
    i2 = float(max(0.0, (q - df) / q) * 100.0) if q > 0 else 0.0
    return {"Q": q, "df": df, "C": c, "tau2_DL": tau2, "I2_pct": i2}


def _pool_random(yi: np.ndarray, vi: np.ndarray, tau2: float) -> dict:
    w = 1.0 / (vi + tau2)
    mu = np.sum(w * yi) / np.sum(w)
    se = float(np.sqrt(1.0 / np.sum(w)))
    ci = (float(mu - 1.96 * se), float(mu + 1.96 * se))
    return {"model": "random", "mu": float(mu), "se": se, "ci_low": ci[0], "ci_high": ci[1], "tau2": float(tau2)}


def _forest_plot(df: pd.DataFrame, fixed: dict, random: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    studies = df["study"].astype(str).tolist()
    yi = df["yi"].to_numpy(float)
    sei = df["sei"].to_numpy(float)
    ci_low = yi - 1.96 * sei
    ci_high = yi + 1.96 * sei

    rows = len(df) + 2
    y_positions = np.arange(rows, 0, -1)
    y_studies = y_positions[: len(df)]
    y_fixed = y_positions[len(df)]
    y_random = y_positions[len(df) + 1]

    xmin = float(min(ci_low.min(), fixed["ci_low"], random["ci_low"]))
    xmax = float(max(ci_high.max(), fixed["ci_high"], random["ci_high"]))
    pad = 0.10 * (xmax - xmin if xmax > xmin else 1.0)
    xmin -= pad
    xmax += pad

    fig_h = max(4.5, 0.35 * rows + 1.5)
    fig, ax = plt.subplots(figsize=(8.2, fig_h))

    ax.hlines(y_studies, ci_low, ci_high, color="black", lw=1)
    ax.plot(yi, y_studies, "s", color="black", ms=5)

    ax.hlines(y_fixed, fixed["ci_low"], fixed["ci_high"], color="#1f77b4", lw=2)
    ax.plot([fixed["mu"]], [y_fixed], "D", color="#1f77b4", ms=7)

    ax.hlines(y_random, random["ci_low"], random["ci_high"], color="#d62728", lw=2)
    ax.plot([random["mu"]], [y_random], "D", color="#d62728", ms=7)

    ax.axvline(0.0, color="gray", lw=1, ls="--")

    labels = studies + [
        f"Pooled (fixed): {fixed['mu']:.3f} [{fixed['ci_low']:.3f}, {fixed['ci_high']:.3f}]",
        f"Pooled (random): {random['mu']:.3f} [{random['ci_low']:.3f}, {random['ci_high']:.3f}]",
    ]
    ax.set_yticks(list(y_studies) + [y_fixed, y_random])
    ax.set_yticklabels(labels)
    ax.set_xlim(xmin, xmax)
    ax.set_xlabel("Effect size (yi) with 95% CI")
    ax.set_title("Toy Meta-analysis Forest Plot")
    ax.invert_yaxis()
    ax.grid(axis="x", color="#eeeeee", lw=0.8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    outputs_dir = root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    csv_path = outputs_dir / "toy_extraction.csv"
    _ensure_toy_csv(csv_path)

    df = pd.read_csv(csv_path)
    req = {"study", "yi", "sei"}
    missing = req.difference(df.columns)
    if missing:
        raise SystemExit(f"Input CSV missing columns: {sorted(missing)}")

    df = df.copy()
    df["yi"] = df["yi"].astype(float)
    df["sei"] = df["sei"].astype(float)
    df["vi"] = df["sei"] ** 2

    yi = df["yi"].to_numpy(float)
    vi = df["vi"].to_numpy(float)

    fixed = _pool_fixed(yi, vi)
    het = _heterogeneity(yi, vi, fixed["mu"])
    random = _pool_random(yi, vi, het["tau2_DL"])

    summary_rows = [
        {"model": "fixed", "mu": fixed["mu"], "se": fixed["se"], "ci_low": fixed["ci_low"], "ci_high": fixed["ci_high"], "tau2": 0.0, "I2_pct": het["I2_pct"], "Q": het["Q"], "df": het["df"]},
        {"model": "random", "mu": random["mu"], "se": random["se"], "ci_low": random["ci_low"], "ci_high": random["ci_high"], "tau2": random["tau2"], "I2_pct": het["I2_pct"], "Q": het["Q"], "df": het["df"]},
    ]
    summary_df = pd.DataFrame(summary_rows)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = outputs_dir / f"summary_table_{ts}.csv"
    forest_path = outputs_dir / f"forest_plot_{ts}.png"
    log_path = outputs_dir / "run_log.txt"

    summary_df.to_csv(summary_path, index=False)
    _forest_plot(df, fixed, random, forest_path)

    now_iso = datetime.now().isoformat(timespec="seconds")
    log_lines = [
        f"[{now_iso}] run_meta_analysis.py",
        f"  input_csv: {csv_path}",
        f"  summary_table: {summary_path}",
        f"  forest_plot: {forest_path}",
        f"  fixed: mu={fixed['mu']:.6f}, se={fixed['se']:.6f}, ci=[{fixed['ci_low']:.6f}, {fixed['ci_high']:.6f}]",
        f"  random: mu={random['mu']:.6f}, se={random['se']:.6f}, ci=[{random['ci_low']:.6f}, {random['ci_high']:.6f}], tau2={random['tau2']:.6f}",
        f"  heterogeneity: Q={het['Q']:.6f}, df={het['df']}, I2={het['I2_pct']:.2f}%",
        "",
    ]
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"WROTE: {summary_path}")
    print(f"WROTE: {forest_path}")
    print(f"LOG: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
