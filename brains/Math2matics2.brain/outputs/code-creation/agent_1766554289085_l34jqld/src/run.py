#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)

def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)

def set_all_seeds(seed: int) -> None:
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)
    try:
        import numpy as np  # type: ignore
        np.random.seed(seed)
    except Exception:
        pass
    try:
        import torch  # type: ignore
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass

def _round_floats(x: Any, nd: int = 10) -> Any:
    if isinstance(x, float):
        return float(f"{x:.{nd}g}")
    if isinstance(x, dict):
        return {k: _round_floats(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round_floats(v, nd) for v in x]
    return x

@dataclass(frozen=True)
class PipelineResults:
    schema_version: int
    seed: int
    n: int
    x_mean: float
    y_mean: float
    x_std: float
    y_std: float
    corr_xy: float
    linreg_slope: float
    linreg_intercept: float
    linreg_r2: float

def run_pipeline(seed: int, n: int = 200) -> tuple[PipelineResults, bytes]:
    import numpy as np  # type: ignore

    rng = np.random.default_rng(seed)
    x = rng.normal(loc=0.0, scale=1.0, size=n)
    noise = rng.normal(loc=0.0, scale=0.5, size=n)
    y = 1.75 * x - 0.4 + noise

    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    x_std = float(np.std(x, ddof=0))
    y_std = float(np.std(y, ddof=0))
    corr_xy = float(np.corrcoef(x, y)[0, 1])

    X = np.column_stack([x, np.ones_like(x)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    slope = float(beta[0])
    intercept = float(beta[1])
    y_hat = slope * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y_mean) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot != 0.0 else 0.0

    res = PipelineResults(
        schema_version=1,
        seed=seed,
        n=int(n),
        x_mean=x_mean,
        y_mean=y_mean,
        x_std=x_std,
        y_std=y_std,
        corr_xy=corr_xy,
        linreg_slope=slope,
        linreg_intercept=intercept,
        linreg_r2=r2,
    )

    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt  # type: ignore

    plt.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": 100,
        "font.size": 10,
        "axes.grid": True,
        "axes.edgecolor": "black",
        "axes.linewidth": 1.0,
        "lines.linewidth": 2.0,
    })

    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=100)
    ax.scatter(x, y, s=18, alpha=0.85, color="#1f77b4", edgecolors="none")
    xs = np.linspace(float(np.min(x)), float(np.max(x)), 200)
    ax.plot(xs, slope * xs + intercept, color="#d62728")
    ax.set_title("Deterministic Linear Relationship")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_xlim(float(np.min(x) - 0.1), float(np.max(x) + 0.1))
    ax.set_ylim(float(np.min(y) - 0.1), float(np.max(y) + 0.1))
    fig.tight_layout()

    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor="white", edgecolor="white")
    plt.close(fig)
    return res, buf.getvalue()

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic canonical pipeline CLI")
    ap.add_argument("--seed", type=int, default=123, help="RNG seed (default: 123)")
    ap.add_argument("--n", type=int, default=200, help="Number of samples (default: 200)")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    outdir = root / "outputs"
    results_path = outdir / "results.json"
    figure_path = outdir / "figure.png"
    hashes_path = outdir / "hashes.json"

    set_all_seeds(int(args.seed))
    res, png_bytes = run_pipeline(seed=int(args.seed), n=int(args.n))

    payload: Dict[str, Any] = {
        "schema_version": 1,
        "artifact_paths": {
            "results_json": str(results_path.relative_to(root).as_posix()),
            "figure_png": str(figure_path.relative_to(root).as_posix()),
            "hashes_json": str(hashes_path.relative_to(root).as_posix()),
        },
        "results": _round_floats(asdict(res), nd=10),
    }
    results_text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    _atomic_write_text(results_path, results_text, encoding="utf-8")
    _atomic_write_bytes(figure_path, png_bytes)

    hashes = {
        "schema_version": 1,
        "sha256": {
            "results.json": _sha256_file(results_path),
            "figure.png": _sha256_file(figure_path),
        },
    }
    hashes_text = json.dumps(hashes, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    _atomic_write_text(hashes_path, hashes_text, encoding="utf-8")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
