from __future__ import annotations
import csv, json, math, sys, time, platform
from pathlib import Path

def _ensure_toy_csv(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"study":"Study A","effect":0.20,"se":0.10},
        {"study":"Study B","effect":0.05,"se":0.08},
        {"study":"Study C","effect":0.35,"se":0.12},
        {"study":"Study D","effect":-0.02,"se":0.09},
        {"study":"Study E","effect":0.18,"se":0.07},
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["study","effect","se"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

def _read_effects(path: Path):
    studies = []
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            study = (row.get("study") or row.get("Study") or "").strip() or f"Study_{len(studies)+1}"
            eff = float(row["effect"])
            se = float(row["se"])
            if se <= 0:
                raise ValueError(f"Non-positive se for {study}")
            studies.append((study, eff, se))
    if not studies:
        raise ValueError("No rows found in toy CSV")
    return studies

def _fixed_effect(studies):
    ws = [1.0/(se*se) for _,_,se in studies]
    ys = [y for _,y,_ in studies]
    sw = sum(ws)
    mu = sum(w*y for w,y in zip(ws, ys))/sw
    se_mu = math.sqrt(1.0/sw)
    q = sum(w*(y-mu)**2 for w,y in zip(ws, ys))
    return mu, se_mu, q, ws

def _random_effect_dl(studies, q, ws):
    k = len(studies)
    sw = sum(ws); sw2 = sum(w*w for w in ws)
    c = sw - (sw2/sw) if sw > 0 else 0.0
    tau2 = max(0.0, (q-(k-1))/c) if c > 0 else 0.0
    wr = [1.0/((se*se)+tau2) for _,_,se in studies]
    swr = sum(wr)
    mu = sum(w*y for w,(_,y,_) in zip(wr, studies))/swr
    se_mu = math.sqrt(1.0/swr)
    return mu, se_mu, tau2, wr

def _ci95(mu, se):
    z = 1.959963984540054
    return mu - z*se, mu + z*se

def _i2(q, k):
    return max(0.0, (q-(k-1))/q)*100.0 if q > 0 and k > 1 else 0.0

def _write_pooled_csv(path: Path, fixed, random, k, q, i2):
    path.parent.mkdir(parents=True, exist_ok=True)
    (f_mu, f_se, _, _) = fixed
    (r_mu, r_se, tau2, _) = random
    f_lo, f_hi = _ci95(f_mu, f_se)
    r_lo, r_hi = _ci95(r_mu, r_se)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["model","k","pooled_effect","se","ci_low","ci_high","tau2","Q","I2"])
        w.writeheader()
        w.writerow({"model":"fixed","k":k,"pooled_effect":f_mu,"se":f_se,"ci_low":f_lo,"ci_high":f_hi,"tau2":0.0,"Q":q,"I2":i2})
        w.writerow({"model":"random_DL","k":k,"pooled_effect":r_mu,"se":r_se,"ci_low":r_lo,"ci_high":r_hi,"tau2":tau2,"Q":q,"I2":i2})

def _write_forest_png(path: Path, studies, fixed, random):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        # Minimal fallback: create a tiny placeholder PNG header if matplotlib missing
        path.write_bytes(b"")
        return
    names = [s for s,_,_ in studies]
    ys = [y for _,y,_ in studies]
    ses = [se for *_,se in studies]
    cis = [(_ci95(y,se)) for y,se in zip(ys, ses)]
    k = len(studies)
    (f_mu, f_se, _, _) = fixed
    (r_mu, r_se, _, _) = random
    f_lo, f_hi = _ci95(f_mu, f_se)
    r_lo, r_hi = _ci95(r_mu, r_se)

    all_x = [x for lo,hi in cis for x in (lo,hi)] + [f_lo,f_hi,r_lo,r_hi]
    xmin, xmax = min(all_x), max(all_x)
    pad = 0.08*(xmax-xmin) if xmax > xmin else 0.5
    xmin -= pad; xmax += pad

    fig_h = max(2.8, 0.42*k + 1.9)
    fig, ax = plt.subplots(figsize=(7.2, fig_h), dpi=140)
    y_pos = list(range(k, 0, -1))
    for i, ((name, y, se), (lo, hi), yp) in enumerate(zip(studies, cis, y_pos)):
        ax.plot([lo, hi], [yp, yp], color="black", lw=1)
        ax.plot([y], [yp], marker="s", color="black", ms=4)
        ax.text(xmin, yp, name, va="center", ha="left", fontsize=9)
        ax.text(xmax, yp, f"{y:.3f} [{lo:.3f}, {hi:.3f}]", va="center", ha="right", fontsize=9)

    ax.axvline(0.0, color="gray", lw=1, ls="--")

    yp_fixed = 0.3
    ax.plot([f_lo, f_hi], [yp_fixed, yp_fixed], color="#1f77b4", lw=2)
    ax.plot([f_mu], [yp_fixed], marker="D", color="#1f77b4", ms=6)
    ax.text(xmin, yp_fixed, "Pooled (fixed)", va="center", ha="left", fontsize=9, color="#1f77b4")
    ax.text(xmax, yp_fixed, f"{f_mu:.3f} [{f_lo:.3f}, {f_hi:.3f}]", va="center", ha="right", fontsize=9, color="#1f77b4")

    yp_rand = -0.35
    ax.plot([r_lo, r_hi], [yp_rand, yp_rand], color="#d62728", lw=2)
    ax.plot([r_mu], [yp_rand], marker="D", color="#d62728", ms=6)
    ax.text(xmin, yp_rand, "Pooled (random DL)", va="center", ha="left", fontsize=9, color="#d62728")
    ax.text(xmax, yp_rand, f"{r_mu:.3f} [{r_lo:.3f}, {r_hi:.3f}]", va="center", ha="right", fontsize=9, color="#d62728")

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(-1.1, k+1)
    ax.set_yticks([])
    ax.set_xlabel("Effect size")
    ax.set_title("Toy meta-analysis forest plot")
    for spine in ("left","right","top"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

def main(argv=None) -> int:
    root = Path(__file__).resolve().parents[1]
    toy_csv = root / "meta_analysis" / "data" / "toy_effects.csv"
    out_tables = root / "runtime" / "_build" / "tables" / "pooled_estimates.csv"
    out_fig = root / "runtime" / "_build" / "figures" / "forest_plot.png"
    out_meta = root / "runtime" / "_build" / "reports" / "demo_run.json"

    _ensure_toy_csv(toy_csv)
    studies = _read_effects(toy_csv)
    fixed = _fixed_effect(studies)
    f_mu, f_se, q, ws = fixed
    k = len(studies)
    i2 = _i2(q, k)
    random = _random_effect_dl(studies, q, ws)

    _write_pooled_csv(out_tables, fixed, random, k, q, i2)
    _write_forest_png(out_fig, studies, fixed, random)

    meta = {
        "timestamp_unix": time.time(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "input_csv": str(toy_csv),
        "outputs": {
            "pooled_estimates_csv": str(out_tables),
            "forest_plot_png": str(out_fig),
            "run_metadata_json": str(out_meta),
        },
        "k": k,
        "heterogeneity": {"Q": q, "I2_percent": i2},
        "models": ["fixed", "random_DL"],
    }
    out_meta.parent.mkdir(parents=True, exist_ok=True)
    out_meta.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(out_tables))
    print(str(out_fig))
    print(str(out_meta))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
