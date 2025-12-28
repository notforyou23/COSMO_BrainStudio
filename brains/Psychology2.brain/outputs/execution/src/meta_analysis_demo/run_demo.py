"""End-to-end meta-analysis demo runner.

Creates a toy CSV (if missing), runs a simple log risk ratio meta-analysis
(fixed + DerSimonian-Laird random effects), and writes real outputs to:
- outputs/tables/pooled_estimates.csv
- outputs/figures/forest_plot.png
- _build/logs/run_demo.log
"""

from __future__ import annotations
from pathlib import Path
import csv, json, math, datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
OUT_TABLES = ROOT / "outputs" / "tables"
OUT_FIGS = ROOT / "outputs" / "figures"
BUILD_DATA = ROOT / "_build" / "data"
BUILD_LOGS = ROOT / "_build" / "logs"


def _log(msg: str, log_fp: Path) -> None:
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    log_fp.parent.mkdir(parents=True, exist_ok=True)
    with log_fp.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _z975() -> float:
    return 1.959963984540054


def ensure_toy_csv(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path
    rows = [
        ("Study A", 12, 100, 20, 100),
        ("Study B",  7,  80, 12,  80),
        ("Study C", 25, 120, 35, 120),
        ("Study D",  5,  60, 10,  60),
        ("Study E", 18,  90, 22,  90),
        ("Study F",  2,  50,  5,  50),
        ("Study G", 30, 150, 40, 150),
        ("Study H", 10,  70, 14,  70),
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["study", "events_treat", "total_treat", "events_ctrl", "total_ctrl"])
        w.writerows(rows)
    return path


def compute_log_rr(df: pd.DataFrame, cc: float = 0.5) -> pd.DataFrame:
    req = ["study", "events_treat", "total_treat", "events_ctrl", "total_ctrl"]
    missing = [c for c in req if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    d = df.copy()
    for c in req[1:]:
        d[c] = pd.to_numeric(d[c], errors="raise")
    a = d["events_treat"].to_numpy(float)
    b = (d["total_treat"] - d["events_treat"]).to_numpy(float)
    c = d["events_ctrl"].to_numpy(float)
    d0 = (d["total_ctrl"] - d["events_ctrl"]).to_numpy(float)
    zero_any = (a == 0) | (b == 0) | (c == 0) | (d0 == 0)
    if np.any(zero_any):
        a = np.where(zero_any, a + cc, a)
        b = np.where(zero_any, b + cc, b)
        c = np.where(zero_any, c + cc, c)
        d0 = np.where(zero_any, d0 + cc, d0)
    rr = (a / (a + b)) / (c / (c + d0))
    yi = np.log(rr)
    vi = 1.0 / a - 1.0 / (a + b) + 1.0 / c - 1.0 / (c + d0)
    out = pd.DataFrame({"study": df["study"].astype(str), "yi": yi, "vi": vi})
    out["sei"] = np.sqrt(out["vi"])
    out["rr"] = np.exp(out["yi"])
    out["ci_lo"] = np.exp(out["yi"] - _z975() * out["sei"])
    out["ci_hi"] = np.exp(out["yi"] + _z975() * out["sei"])
    return out


def pool_fixed(yi: np.ndarray, vi: np.ndarray) -> dict:
    wi = 1.0 / vi
    mu = float(np.sum(wi * yi) / np.sum(wi))
    se = float(np.sqrt(1.0 / np.sum(wi)))
    return {"mu": mu, "se": se, "tau2": 0.0, "weights": wi}


def pool_random_dl(yi: np.ndarray, vi: np.ndarray) -> dict:
    wi = 1.0 / vi
    mu_fe = float(np.sum(wi * yi) / np.sum(wi))
    Q = float(np.sum(wi * (yi - mu_fe) ** 2))
    k = int(len(yi))
    c = float(np.sum(wi) - (np.sum(wi ** 2) / np.sum(wi)))
    tau2 = max(0.0, (Q - (k - 1)) / c) if c > 0 else 0.0
    wi_star = 1.0 / (vi + tau2)
    mu = float(np.sum(wi_star * yi) / np.sum(wi_star))
    se = float(np.sqrt(1.0 / np.sum(wi_star)))
    I2 = max(0.0, (Q - (k - 1)) / Q) * 100.0 if Q > 0 else 0.0
    return {"mu": mu, "se": se, "tau2": float(tau2), "Q": Q, "I2": float(I2), "weights": wi_star}


def write_outputs(effects: pd.DataFrame, pooled: pd.DataFrame) -> None:
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    OUT_FIGS.mkdir(parents=True, exist_ok=True)
    (OUT_TABLES / "study_effects.csv").write_text(effects.to_csv(index=False), encoding="utf-8")
    (OUT_TABLES / "pooled_estimates.csv").write_text(pooled.to_csv(index=False), encoding="utf-8")
    (OUT_TABLES / "pooled_estimates.json").write_text(
        json.dumps(pooled.to_dict(orient="records"), indent=2), encoding="utf-8"
    )


def forest_plot(effects: pd.DataFrame, pooled_rr: dict, out_fp: Path) -> None:
    k = effects.shape[0]
    y = np.arange(k)[::-1]
    rr = effects["rr"].to_numpy(float)
    lo = effects["ci_lo"].to_numpy(float)
    hi = effects["ci_hi"].to_numpy(float)

    fig_h = max(4.5, 0.35 * k + 2.2)
    fig, ax = plt.subplots(figsize=(8.5, fig_h))
    ax.axvline(1.0, color="0.7", lw=1)
    ax.hlines(y, lo, hi, color="black", lw=1.2)
    ax.plot(rr, y, "s", color="black", markersize=5)

    rr_p = float(pooled_rr["rr"])
    lo_p = float(pooled_rr["ci_lo"])
    hi_p = float(pooled_rr["ci_hi"])
    y_p = -1.0
    diamond_x = [lo_p, rr_p, hi_p, rr_p, lo_p]
    diamond_y = [y_p, y_p + 0.25, y_p, y_p - 0.25, y_p]
    ax.plot(diamond_x, diamond_y, color="tab:blue", lw=1.5)
    ax.fill(diamond_x, diamond_y, color="tab:blue", alpha=0.25)

    ax.set_yticks(list(y) + [y_p])
    ax.set_yticklabels(list(effects["study"].astype(str)) + ["Pooled (RE)"])
    ax.set_xlabel("Risk Ratio (log scale)")
    ax.set_xscale("log")
    xmin = min(lo.min(), lo_p) * 0.8
    xmax = max(hi.max(), hi_p) * 1.25
    ax.set_xlim(max(1e-3, xmin), xmax)
    ax.set_ylim(-2.0, k - 0.25)
    ax.grid(axis="x", color="0.9", lw=0.8)

    ax.set_title("Toy Meta-analysis Demo (log RR; random-effects DL)")
    out_fp.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_fp, dpi=200)
    plt.close(fig)


def main() -> int:
    log_fp = BUILD_LOGS / "run_demo.log"
    for p in [OUT_TABLES, OUT_FIGS, BUILD_DATA, BUILD_LOGS]:
        p.mkdir(parents=True, exist_ok=True)

    _log("Starting meta-analysis demo run.", log_fp)
    toy_csv = ensure_toy_csv(BUILD_DATA / "toy_studies.csv")
    _log(f"Input CSV: {toy_csv}", log_fp)

    df = pd.read_csv(toy_csv)
    eff = compute_log_rr(df)
    yi = eff["yi"].to_numpy(float)
    vi = eff["vi"].to_numpy(float)

    fe = pool_fixed(yi, vi)
    re = pool_random_dl(yi, vi)
    z = _z975()

    def _row(model: str, res: dict) -> dict:
        mu, se = float(res["mu"]), float(res["se"])
        return {
            "model": model,
            "k": int(len(yi)),
            "log_effect": mu,
            "se": se,
            "ci_lo_log": mu - z * se,
            "ci_hi_log": mu + z * se,
            "effect_rr": math.exp(mu),
            "ci_lo_rr": math.exp(mu - z * se),
            "ci_hi_rr": math.exp(mu + z * se),
            "tau2": float(res.get("tau2", 0.0)),
            "Q": float(res.get("Q", np.nan)),
            "I2_percent": float(res.get("I2", np.nan)),
        }

    pooled = pd.DataFrame([_row("fixed", fe), _row("random_DL", re)])
    write_outputs(eff, pooled)

    pooled_rr = {
        "rr": pooled.loc[pooled["model"] == "random_DL", "effect_rr"].iloc[0],
        "ci_lo": pooled.loc[pooled["model"] == "random_DL", "ci_lo_rr"].iloc[0],
        "ci_hi": pooled.loc[pooled["model"] == "random_DL", "ci_hi_rr"].iloc[0],
    }
    fig_fp = OUT_FIGS / "forest_plot.png"
    forest_plot(eff, pooled_rr, fig_fp)

    _log(f"Wrote: {OUT_TABLES/'pooled_estimates.csv'}", log_fp)
    _log(f"Wrote: {fig_fp}", log_fp)
    _log("Done.", log_fp)
    print(str(OUT_TABLES / "pooled_estimates.csv"))
    print(str(fig_fp))
    print(str(log_fp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
