from __future__ import annotations

from pathlib import Path
import json
import os
import random
import numpy as np

def _set_determinism(seed: int) -> None:
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
    random.seed(seed)
    np.random.seed(seed)

def _stable_json_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    path.write_text(text + "\n", encoding="utf-8")

def _median_of_means(x: np.ndarray, groups: int) -> float:
    x = np.asarray(x, dtype=np.float64)
    n = x.size
    g = int(groups)
    if g < 1:
        raise ValueError("groups must be >= 1")
    g = min(g, n)
    m = n // g
    if m < 1:
        g = n
        m = 1
    used = g * m
    y = x[:used].reshape(g, m).mean(axis=1)
    return float(np.median(y))

def _metrics(estimates: np.ndarray, truth: float) -> dict:
    err = estimates - truth
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err * err)))
    bias = float(np.mean(err))
    return {"mae": mae, "rmse": rmse, "bias": bias}

def _simulate(seed: int, *, trials: int, n: int, p_out: float, sigma: float, sigma_out: float, mom_groups: int) -> dict:
    rng = np.random.default_rng(seed)
    truth = 0.0  # symmetric mixture centered at 0
    mean_est = np.empty(trials, dtype=np.float64)
    mom_est = np.empty(trials, dtype=np.float64)

    for t in range(trials):
        u = rng.random(n)
        x = rng.normal(0.0, sigma, size=n)
        mask = u < p_out
        if np.any(mask):
            x[mask] = rng.normal(0.0, sigma_out, size=int(np.sum(mask)))
        mean_est[t] = float(np.mean(x))
        mom_est[t] = _median_of_means(x, mom_groups)

    out = {
        "seed": int(seed),
        "params": {
            "trials": int(trials),
            "n": int(n),
            "p_out": float(p_out),
            "sigma": float(sigma),
            "sigma_out": float(sigma_out),
            "mom_groups": int(mom_groups),
        },
        "truth": float(truth),
        "metrics": {
            "mean": _metrics(mean_est, truth),
            "median_of_means": _metrics(mom_est, truth),
        },
    }
    # round for stable JSON while preserving meaningful precision
    for k in ("mean", "median_of_means"):
        for m in ("mae", "rmse", "bias"):
            out["metrics"][k][m] = float(round(out["metrics"][k][m], 12))
    return out

def _save_plot(fig_path: Path, results: dict) -> None:
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": 100,
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "lines.linewidth": 2.0,
        "patch.antialiased": True,
        "text.usetex": False,
    })

    metrics = results["metrics"]
    labels = ["Mean", "Median-of-means"]
    rmse = [metrics["mean"]["rmse"], metrics["median_of_means"]["rmse"]]
    mae = [metrics["mean"]["mae"], metrics["median_of_means"]["mae"]]

    x = np.arange(len(labels), dtype=np.float64)
    width = 0.36

    fig, ax = plt.subplots(figsize=(7.0, 4.0), constrained_layout=False)
    ax.bar(x - width / 2.0, rmse, width, label="RMSE", color="#4C72B0")
    ax.bar(x + width / 2.0, mae, width, label="MAE", color="#55A868")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Error")
    ax.set_title("Mean vs Median-of-Means on Heavy-Tailed Data")
    ax.legend(loc="upper right", frameon=True)
    ax.set_axisbelow(True)
    fig.tight_layout(pad=0.8)

    fig_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = fig_path.with_suffix(".tmp.png")
    fig.savefig(
        tmp,
        format="png",
        dpi=100,
        facecolor="white",
        edgecolor="white",
        transparent=False,
        bbox_inches=None,
        pad_inches=0.0,
        metadata={"Software": "deterministic-generate_results"},
    )
    plt.close(fig)

    # Re-save with Pillow to remove any non-deterministic chunks and control compression.
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
    im = Image.open(tmp)
    im = im.convert("RGBA")
    info = PngInfo()
    info.add_text("Software", "deterministic-generate_results")
    im.save(fig_path, format="PNG", compress_level=9, optimize=False, pnginfo=info)
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass

def main() -> None:
    base = Path(__file__).resolve().parents[1]
    out_json = base / "results" / "results.json"
    out_png = base / "figure.png"

    seed = 1337
    _set_determinism(seed)

    results = _simulate(
        seed,
        trials=1500,
        n=200,
        p_out=0.05,
        sigma=1.0,
        sigma_out=25.0,
        mom_groups=10,
    )
    _stable_json_write(out_json, results)
    _save_plot(out_png, results)

if __name__ == "__main__":
    main()
