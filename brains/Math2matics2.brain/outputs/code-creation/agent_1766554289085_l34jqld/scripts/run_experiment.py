#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, os, platform, socket, sys, time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

def median_of_means(x: np.ndarray, k: int, rng: np.random.Generator) -> float:
    x = np.asarray(x, dtype=float)
    n = x.size
    k = int(k)
    if k <= 1 or n < 2:
        return float(np.mean(x))
    k = min(k, n)
    idx = rng.permutation(n)
    blocks = np.array_split(x[idx], k)
    means = np.array([b.mean() for b in blocks], dtype=float)
    return float(np.median(means))

def ecdf(a: np.ndarray):
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return np.array([0.0]), np.array([0.0])
    x = np.sort(a)
    y = np.arange(1, x.size + 1) / x.size
    return x, y

def atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp_{os.getpid()}_{int(time.time()*1e6)}")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def append_log(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")

@dataclass
class RunMeta:
    timestamp_utc: str
    hostname: str
    platform: str
    python: str
    pid: int
    cwd: str

def summarize(arr: np.ndarray) -> dict:
    arr = np.asarray(arr, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"n": 0}
    qs = np.quantile(arr, [0.5, 0.9, 0.95, 0.99])
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "median": float(qs[0]),
        "q90": float(qs[1]),
        "q95": float(qs[2]),
        "q99": float(qs[3]),
        "max": float(arr.max()),
    }

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Toy heavy-tailed experiment: sample mean vs median-of-means.")
    p.add_argument("--n", type=int, default=2000, help="Samples per trial.")
    p.add_argument("--trials", type=int, default=500, help="Number of repeated trials.")
    p.add_argument("--df", type=float, default=2.2, help="Student-t degrees of freedom (heavy-tailed if small).")
    p.add_argument("--mom-blocks", type=int, default=20, help="Number of blocks for median-of-means.")
    p.add_argument("--seed", type=int, default=0, help="RNG seed.")
    p.add_argument("--outdir", type=str, default="outputs", help="Output directory (relative to script CWD).")
    args = p.parse_args(argv)

    base_dir = Path(__file__).resolve().parent.parent
    outdir = (base_dir / args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    true_mean = 0.0

    mean_err = np.empty(args.trials, dtype=float)
    mom_err = np.empty(args.trials, dtype=float)

    t0 = time.time()
    for t in range(args.trials):
        x = rng.standard_t(df=args.df, size=args.n).astype(float)
        mean_est = float(x.mean())
        mom_est = median_of_means(x, args.mom_blocks, rng)
        mean_err[t] = abs(mean_est - true_mean)
        mom_err[t] = abs(mom_est - true_mean)
    elapsed = time.time() - t0

    meta = RunMeta(
        timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        hostname=socket.gethostname(),
        platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
        python=sys.version.split()[0],
        pid=os.getpid(),
        cwd=str(Path.cwd()),
    )

    results = {
        "meta": asdict(meta),
        "params": {
            "n": args.n,
            "trials": args.trials,
            "df": args.df,
            "mom_blocks": args.mom_blocks,
            "seed": args.seed,
            "true_mean": true_mean,
        },
        "timing_sec": {"total": float(elapsed), "per_trial": float(elapsed / max(1, args.trials))},
        "errors": {
            "sample_mean_abs_error": mean_err.tolist(),
            "median_of_means_abs_error": mom_err.tolist(),
        },
        "summary": {"sample_mean": summarize(mean_err), "median_of_means": summarize(mom_err)},
    }

    results_path = outdir / "results.json"
    atomic_write_json(results_path, results)

    # Plot ECDF on log-x to highlight tail behavior
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xm, ym = ecdf(mean_err)
    xmom, ymom = ecdf(mom_err)
    eps = 1e-12
    xm = np.maximum(xm, eps)
    xmom = np.maximum(xmom, eps)

    fig, ax = plt.subplots(figsize=(7.2, 4.6), dpi=160)
    ax.step(xm, ym, where="post", label="Sample mean", linewidth=2.0)
    ax.step(xmom, ymom, where="post", label=f"Median-of-means (k={args.mom_blocks})", linewidth=2.0)
    ax.set_xscale("log")
    ax.set_xlabel("Absolute error |estimate - true mean| (log scale)")
    ax.set_ylabel("ECDF")
    ax.set_title(f"Heavy-tailed mean estimation (Student-t df={args.df}, n={args.n}, trials={args.trials})")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="lower right", frameon=True)
    fig.tight_layout()
    plot_path = outdir / "mom_vs_mean.png"
    fig.savefig(plot_path)
    plt.close(fig)

    log_record = {
        "timestamp_utc": meta.timestamp_utc,
        "script": str(Path(__file__).name),
        "outdir": str(outdir),
        "results_json": str(results_path),
        "plot_png": str(plot_path),
        "params": results["params"],
        "timing_sec": results["timing_sec"],
        "summary": results["summary"],
    }
    append_log(outdir / "run.log", log_record)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
