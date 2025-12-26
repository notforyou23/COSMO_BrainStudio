"""Deterministic command-line entrypoint.

Writes fixed outputs:
- /outputs/results.json
- /outputs/figure.png
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
except Exception as e:  # pragma: no cover
    np = None  # type: ignore

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as e:  # pragma: no cover
    plt = None  # type: ignore

try:
    from importlib import metadata as importlib_metadata
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore
def _git_hash() -> str | None:
    """Return current git commit hash if available."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=os.getcwd(),
            text=True,
        ).strip()
        return out or None
    except Exception:
        return None


def _pkg_version(name: str) -> str | None:
    try:
        return importlib_metadata.version(name)
    except Exception:
        return None


def _set_determinism(seed: int) -> None:
    """Best-effort determinism for common RNGs."""
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)
    if np is not None:
        np.random.seed(seed)
def _compute(seed: int, n: int) -> tuple[list[float], dict]:
    """Deterministic computation producing data and summary stats."""
    _set_determinism(seed)
    if np is None:
        # Fallback: deterministic pure-Python random numbers.
        data = [random.random() for _ in range(n)]
        mean = sum(data) / n if n else 0.0
        var = sum((x - mean) ** 2 for x in data) / n if n else 0.0
        std = var ** 0.5
    else:
        arr = np.random.normal(loc=0.0, scale=1.0, size=int(n))
        data = arr.astype(float).tolist()
        mean = float(arr.mean()) if n else 0.0
        std = float(arr.std()) if n else 0.0
    stats = {
        "seed": int(seed),
        "n": int(n),
        "mean": round(float(mean), 12),
        "std": round(float(std), 12),
        "min": round(float(min(data)) if data else 0.0, 12),
        "max": round(float(max(data)) if data else 0.0, 12),
    }
    return data, stats


def _write_figure(data: list[float], path: Path) -> None:
    """Write a deterministic histogram figure."""
    if plt is None:
        return
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.hist(data, bins=30, range=(-4, 4), color="#4C72B0", edgecolor="white")
    ax.set_title("Deterministic histogram")
    ax.set_xlabel("value")
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(path, format="png")
    plt.close(fig)
def _metadata(seed: int) -> dict:
    return {
        "git_hash": _git_hash(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "seed": int(seed),
        "env": {
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
        },
        "packages": {
            "numpy": _pkg_version("numpy"),
            "matplotlib": _pkg_version("matplotlib"),
            "deterministic-runner": _pkg_version("deterministic-runner"),
        },
    }


def run(seed: int = 0, n: int = 1000, outdir: str | Path = "/outputs") -> dict:
    """Run the deterministic job and write fixed outputs."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    data, stats = _compute(seed=seed, n=n)
    fig_path = out / "figure.png"
    _write_figure(data, fig_path)
    results = {
        "status": "ok",
        "summary": stats,
        "outputs": {
            "results_json": str((out / "results.json").resolve()),
            "figure_png": str(fig_path.resolve()),
        },
        "metadata": _metadata(seed),
    }
    (out / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return results


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="deterministic-runner")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--outdir", type=str, default="/outputs")
    args = p.parse_args(argv)
    run(seed=args.seed, n=args.n, outdir=args.outdir)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
