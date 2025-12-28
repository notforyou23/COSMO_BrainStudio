#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys, math, json, datetime

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")

def log_line(log_path: Path, event: str, **fields):
    rec = {"ts": now_iso(), "event": event, **fields}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def die(code: int, msg: str, log_path: Path | None = None, **fields):
    if log_path is not None:
        log_line(log_path, "error", message=msg, **fields)
    print(msg, file=sys.stderr)
    raise SystemExit(code)

def read_csv(path: Path):
    import pandas as pd
    return pd.read_csv(path)

def compute_effects(df):
    # Expect: study, events_treat, n_treat, events_control, n_control
    required = ["study","events_treat","n_treat","events_control","n_control"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    out = df.copy()
    for c in required[1:]:
        out[c] = out[c].astype(float)
    # Continuity correction 0.5 for zero cells
    a = out["events_treat"]; b = out["n_treat"] - out["events_treat"]
    c = out["events_control"]; d = out["n_control"] - out["events_control"]
    cc = 0.5
    zero = (a==0) | (b==0) | (c==0) | (d==0)
    a2 = a.where(~zero, a+cc); b2 = b.where(~zero, b+cc)
    c2 = c.where(~zero, c+cc); d2 = d.where(~zero, d+cc)
    rr = (a2/out["n_treat"]) / (c2/out["n_control"])
    lnrr = rr.apply(lambda x: math.log(x))
    se = (1.0/a2 - 1.0/out["n_treat"] + 1.0/c2 - 1.0/out["n_control"]).apply(lambda x: math.sqrt(max(x, 1e-12)))
    out["rr"] = rr
    out["log_rr"] = lnrr
    out["se_log_rr"] = se
    out["ci_lo_rr"] = (out["log_rr"] - 1.96*out["se_log_rr"]).apply(math.exp)
    out["ci_hi_rr"] = (out["log_rr"] + 1.96*out["se_log_rr"]).apply(math.exp)
    out["weight_fe"] = 1.0/(out["se_log_rr"]**2)
    return out

def pooled_fixed_effect(effects_df):
    w = effects_df["weight_fe"]
    theta = effects_df["log_rr"]
    s = float(w.sum())
    if not math.isfinite(s) or s <= 0:
        raise ValueError("Nonpositive total weight; cannot pool.")
    pooled = float((w*theta).sum()/s)
    se = math.sqrt(1.0/s)
    return {
        "model": "fixed_effect_inverse_variance",
        "pooled_log_rr": pooled,
        "pooled_rr": math.exp(pooled),
        "se_log_rr": se,
        "ci_lo_rr": math.exp(pooled - 1.96*se),
        "ci_hi_rr": math.exp(pooled + 1.96*se),
        "k": int(len(effects_df))
    }

def forest_plot(effects_df, pooled, out_png: Path, title: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = effects_df.copy()
    df["label"] = df["study"].astype(str)
    df = df.reset_index(drop=True)
    y = list(range(len(df), 0, -1))
    fig_h = max(2.5, 0.45*len(df) + 1.6)
    fig, ax = plt.subplots(figsize=(8.2, fig_h))

    ax.axvline(1.0, color="#777777", lw=1)
    for i, row in df.iterrows():
        yy = y[i]
        ax.plot([row["ci_lo_rr"], row["ci_hi_rr"]], [yy, yy], color="black", lw=1)
        ax.scatter([row["rr"]], [yy], s=22, color="black", zorder=3)

    # Pooled diamond-ish
    py = 0.5
    ax.plot([pooled["ci_lo_rr"], pooled["ci_hi_rr"]], [py, py], color="#1f77b4", lw=2)
    ax.scatter([pooled["pooled_rr"]], [py], s=40, color="#1f77b4", zorder=3)

    ax.set_yticks(y + [py])
    ax.set_yticklabels(list(df["label"]) + ["Pooled"])
    ax.set_xscale("log")
    ax.set_xlabel("Risk Ratio (log scale)")
    ax.set_title(title)
    ax.set_ylim(0, len(df) + 1)
    ax.grid(axis="x", which="both", ls=":", lw=0.6, color="#bbbbbb")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=200)
    plt.close(fig)

def main():
    here = Path(__file__).resolve()
    root = here.parents[1]  # .../execution
    input_csv = root / "outputs" / "goal_2_meta_starter_kit" / "data" / "toy_extraction.csv"
    reports_dir = root / "runtime" / "_build" / "reports"
    log_path = reports_dir / "toy_meta_analysis.log"
    plot_path = reports_dir / "toy_forest_plot.png"
    table_path = reports_dir / "toy_summary_table.csv"
    json_path = reports_dir / "toy_pooled_estimate.json"

    if not input_csv.is_file():
        die(2, f"Missing required input CSV: {input_csv}", log_path)
    if not reports_dir.is_dir():
        die(3, f"Missing required output directory: {reports_dir}", log_path)

    log_line(log_path, "start", script=str(here), input_csv=str(input_csv), reports_dir=str(reports_dir))

    try:
        df = read_csv(input_csv)
        effects = compute_effects(df)
        pooled = pooled_fixed_effect(effects)

        # Save summary table
        import pandas as pd
        cols = ["study","events_treat","n_treat","events_control","n_control","rr","ci_lo_rr","ci_hi_rr","weight_fe"]
        table = effects[cols].copy()
        table["weight_fe"] = table["weight_fe"] / table["weight_fe"].sum()
        table.to_csv(table_path, index=False)

        # Save pooled estimate JSON
        json_path.write_text(json.dumps(pooled, indent=2, sort_keys=True), encoding="utf-8")

        # Save plot
        forest_plot(effects, pooled, plot_path, title="Toy Meta-analysis (Fixed Effect)")

        # Verify outputs exist
        for p in (plot_path, table_path, json_path, log_path):
            if not p.is_file() or p.stat().st_size <= 0:
                die(4, f"Expected output missing/empty: {p}", log_path)

        log_line(log_path, "done", k=pooled["k"], pooled_rr=pooled["pooled_rr"], ci=[pooled["ci_lo_rr"], pooled["ci_hi_rr"]])
        print(f"OK: wrote {plot_path.name}, {table_path.name}, {json_path.name}")
        return 0
    except SystemExit:
        raise
    except Exception as e:
        die(5, f"Analysis failed: {type(e).__name__}: {e}", log_path)

if __name__ == "__main__":
    raise SystemExit(main())
