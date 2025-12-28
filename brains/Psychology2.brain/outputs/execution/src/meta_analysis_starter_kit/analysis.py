from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import math
import pandas as pd


@dataclass(frozen=True)
class MetaResult:
    model: str
    pooled_effect: float
    pooled_se: float
    ci_low: float
    ci_high: float
    k: int


def load_extraction_template(csv_path: Path) -> pd.DataFrame:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Extraction template not found: {csv_path}")
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError(f"Extraction template is empty: {csv_path}")
    return df


def _pick_columns(df: pd.DataFrame) -> Tuple[str, str, Optional[str]]:
    cols = {c.lower(): c for c in df.columns}

    effect_candidates = ["yi", "effect", "effect_size", "log_effect", "log_rr", "lnrr", "logor", "lor", "smd"]
    se_candidates = ["sei", "se", "std_error", "standard_error"]
    study_candidates = ["study_id", "study", "author_year", "citation", "id"]

    eff = next((cols[c] for c in effect_candidates if c in cols), None)
    se = next((cols[c] for c in se_candidates if c in cols), None)
    study = next((cols[c] for c in study_candidates if c in cols), None)

    if eff is None or se is None:
        raise ValueError(
            "Could not find required columns for meta-analysis. "
            "Need an effect column (e.g., yi/effect_size) and an SE column (e.g., se/sei). "
            f"Found columns: {list(df.columns)}"
        )
    return eff, se, study


def compute_fixed_effect(df: pd.DataFrame) -> MetaResult:
    eff_col, se_col, _ = _pick_columns(df)
    work = df[[eff_col, se_col]].copy()
    work[eff_col] = pd.to_numeric(work[eff_col], errors="coerce")
    work[se_col] = pd.to_numeric(work[se_col], errors="coerce")
    work = work.dropna()
    if work.empty:
        raise ValueError("No analyzable rows after coercing effect and SE to numeric.")

    yi = work[eff_col].to_numpy()
    sei = work[se_col].to_numpy()
    if (sei <= 0).any():
        raise ValueError("Standard errors must be positive.")

    wi = 1.0 / (sei ** 2)
    pooled = float((wi * yi).sum() / wi.sum())
    pooled_se = float(math.sqrt(1.0 / wi.sum()))
    z = 1.96
    ci_low = pooled - z * pooled_se
    ci_high = pooled + z * pooled_se
    return MetaResult(model="fixed_effect", pooled_effect=pooled, pooled_se=pooled_se, ci_low=ci_low, ci_high=ci_high, k=int(len(work)))


def build_summary_table(df: pd.DataFrame, result: MetaResult) -> pd.DataFrame:
    eff_col, se_col, study_col = _pick_columns(df)
    out = df.copy()
    out["_effect"] = pd.to_numeric(out[eff_col], errors="coerce")
    out["_se"] = pd.to_numeric(out[se_col], errors="coerce")
    out = out.dropna(subset=["_effect", "_se"]).copy()
    z = 1.96
    out["ci_low"] = out["_effect"] - z * out["_se"]
    out["ci_high"] = out["_effect"] + z * out["_se"]
    out["label"] = out[study_col].astype(str) if study_col else [f"Study {i+1}" for i in range(len(out))]
    out = out[["label", "_effect", "_se", "ci_low", "ci_high"]].rename(columns={"_effect": "effect", "_se": "se"})
    pooled_row = pd.DataFrame(
        [{
            "label": f"Pooled ({result.model}, k={result.k})",
            "effect": result.pooled_effect,
            "se": result.pooled_se,
            "ci_low": result.ci_low,
            "ci_high": result.ci_high,
        }]
    )
    return pd.concat([out, pooled_row], ignore_index=True)


def write_summary_table(summary_df: pd.DataFrame, out_csv: Path) -> Path:
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out_csv, index=False)
    return out_csv


def render_forest_plot(summary_df: pd.DataFrame, out_png: Path, title: str = "Forest plot") -> Path:
    import matplotlib.pyplot as plt

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    df = summary_df.copy()
    y = list(range(len(df)))[::-1]
    labels = df["label"].astype(str).tolist()
    eff = df["effect"].astype(float).to_numpy()
    lo = df["ci_low"].astype(float).to_numpy()
    hi = df["ci_high"].astype(float).to_numpy()
    pooled_idx = len(df) - 1

    fig_h = max(3.0, 0.35 * len(df) + 1.2)
    fig, ax = plt.subplots(figsize=(9, fig_h))

    for i in range(len(df)):
        ax.plot([lo[i], hi[i]], [y[i], y[i]], color="black", lw=1)
        if i == pooled_idx:
            ax.scatter([eff[i]], [y[i]], marker="D", s=60, color="black", zorder=3)
        else:
            ax.scatter([eff[i]], [y[i]], marker="s", s=35, color="black", zorder=3)

    ax.axvline(0.0, color="gray", lw=1, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Effect (arbitrary units; template-driven)")
    ax.set_title(title)
    ax.grid(axis="x", color="0.9", lw=0.8)
    plt.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)
    return out_png


def run_analysis(
    extraction_csv: Path,
    outputs_dir: Path,
    summary_csv_name: str = "meta_summary_table.csv",
    forest_png_name: str = "forest_plot.png",
) -> dict:
    extraction_csv = Path(extraction_csv)
    outputs_dir = Path(outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    df = load_extraction_template(extraction_csv)
    res = compute_fixed_effect(df)
    summary = build_summary_table(df, res)

    summary_path = write_summary_table(summary, outputs_dir / summary_csv_name)
    forest_path = render_forest_plot(summary, outputs_dir / forest_png_name)

    return {
        "inputs": {"extraction_csv": str(extraction_csv)},
        "outputs": {"summary_csv": str(summary_path), "forest_png": str(forest_path)},
        "result": {
            "model": res.model,
            "pooled_effect": res.pooled_effect,
            "pooled_se": res.pooled_se,
            "ci_low": res.ci_low,
            "ci_high": res.ci_high,
            "k": res.k,
        },
    }
