from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int = 123
    n: int = 50
    noise: float = 0.1


def _stable_rng(seed: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


def _ensure_outputs_dir(outputs_dir: Path) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return outputs_dir


def _write_results_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_figure_png(path: Path, x: np.ndarray, y: np.ndarray) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt  # noqa: E402

    plt.rcParams.update(
        {
            "figure.figsize": (6.4, 4.8),
            "figure.dpi": 100,
            "savefig.dpi": 100,
            "savefig.facecolor": "white",
            "savefig.edgecolor": "white",
            "savefig.transparent": False,
            "font.family": "DejaVu Sans",
            "text.usetex": False,
            "axes.linewidth": 1.0,
            "path.simplify": False,
            "agg.path.chunksize": 0,
        }
    )

    fig, ax = plt.subplots()
    ax.plot(x, y, color="#1f77b4", linewidth=2.0, antialiased=False)
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path,
        format="png",
        dpi=100,
        bbox_inches=None,
        pad_inches=0,
        metadata={"Software": "generated_script_1766547893907"},
    )
    plt.close(fig)


def run_toy_experiment(
    seed: int = 123,
    outputs_dir: Optional[Path] = None,
    n: int = 50,
    noise: float = 0.1,
) -> Dict[str, Any]:
    outputs_dir = _ensure_outputs_dir(Path("outputs") if outputs_dir is None else Path(outputs_dir))
    cfg = ExperimentConfig(seed=int(seed), n=int(n), noise=float(noise))

    rng = _stable_rng(cfg.seed)
    x = np.arange(cfg.n, dtype=np.int64)
    trend = 0.05 * x.astype(np.float64)
    eps = rng.normal(loc=0.0, scale=cfg.noise, size=cfg.n).astype(np.float64)
    y = trend + eps
    yhat = trend

    mse = float(np.mean((y - yhat) ** 2))
    mae = float(np.mean(np.abs(y - yhat)))
    corr = float(np.corrcoef(y, yhat)[0, 1])

    results = {
        "schema_version": 1,
        "experiment": "toy_experiment",
        "config": asdict(cfg),
        "metrics": {"mse": mse, "mae": mae, "corr": corr},
        "data": {
            "x_first5": [int(v) for v in x[:5]],
            "y_first5": [float(f"{v:.8f}") for v in y[:5]],
        },
        "artifacts": {"results_json": "outputs/results.json", "figure_png": "outputs/figure.png"},
        "determinism": {"numpy_bitgen": "PCG64", "matplotlib_backend": "Agg"},
    }

    _write_results_json(outputs_dir / "results.json", results)
    _write_figure_png(outputs_dir / "figure.png", x.astype(np.float64), y.astype(np.float64))
    return results


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Deterministic toy experiment producing results.json and figure.png")
    p.add_argument("--seed", type=int, default=123)
    p.add_argument("--outputs-dir", type=Path, default=Path("outputs"))
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--noise", type=float, default=0.1)
    args = p.parse_args(argv)
    run_toy_experiment(seed=args.seed, outputs_dir=args.outputs_dir, n=args.n, noise=args.noise)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
