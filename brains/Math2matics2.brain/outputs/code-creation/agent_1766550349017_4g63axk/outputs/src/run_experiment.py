#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def deterministic_compute(n: int) -> dict:
    xs = list(range(n))
    ys = [x * x for x in xs]
    s = sum(ys)
    mean = s / n if n else 0.0
    # Simple stable checksum without hashlib dependency on bytes conversions
    chk = 0
    for y in ys:
        chk = (chk * 1315423911 + y + 0x9E3779B97F4A7C15) & ((1 << 64) - 1)
    return {
        "n": int(n),
        "sum_y": int(s),
        "mean_y": float(mean),
        "checksum64": f"{chk:016x}",
        "first_y": int(ys[0]) if n else 0,
        "last_y": int(ys[-1]) if n else 0,
    }


def save_results(outdir: Path, results: dict) -> Path:
    outpath = outdir / "results.json"
    payload = {
        "status": "ok",
        "method": "deterministic_quadratic",
        "metrics": results,
    }
    outpath.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return outpath


def save_figure(outdir: Path, n: int) -> Path:
    os.environ.setdefault("MPLBACKEND", "Agg")
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    xs = list(range(n))
    ys = [x * x for x in xs]
    figpath = outdir / "figure.png"

    plt.figure(figsize=(6, 4), dpi=150)
    plt.plot(xs, ys, linewidth=2)
    plt.title("Deterministic computation: y=x^2")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.tight_layout()
    plt.savefig(figpath)
    plt.close()
    return figpath


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run a minimal deterministic computation and save artifacts.")
    p.add_argument("--outdir", type=str, default=str(Path.cwd() / "outputs" / "experiment_run"), help="Output directory")
    p.add_argument("--n", type=int, default=100, help="Number of points (>=1)")
    args = p.parse_args(argv)

    try:
        n = int(args.n)
        if n <= 0:
            raise ValueError("--n must be >= 1")
        outdir = Path(args.outdir).expanduser().resolve()
        outdir.mkdir(parents=True, exist_ok=True)

        results = deterministic_compute(n)
        rpath = save_results(outdir, results)
        fpath = save_figure(outdir, n)

        if not rpath.is_file():
            raise RuntimeError("results.json was not created")
        if not fpath.is_file():
            raise RuntimeError("figure.png was not created")

        print(str(outdir))
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
