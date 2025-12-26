from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    _atomic_write_bytes(path, text.encode(encoding))


def canonical_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
def _compute_stats(x: np.ndarray) -> Dict[str, Any]:
    x = np.asarray(x, dtype=np.float64)
    return {
        "n": int(x.size),
        "mean": float(x.mean()),
        "std": float(x.std(ddof=0)),
        "min": float(x.min()),
        "max": float(x.max()),
    }


def _make_results(seed: int, samples: List[float]) -> Dict[str, Any]:
    arr = np.array(samples, dtype=np.float64)
    stats = _compute_stats(arr)
    return {
        "schema_version": 1,
        "seed": int(seed),
        "parameters": {"n_samples": int(len(samples))},
        "data": {"samples": [float(v) for v in samples]},
        "summary": stats,
        "artifacts": {"results_json": "results.json", "figure_png": "figure.png"},
    }
def _write_figure_png(path: Path, samples: List[float]) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt  # noqa: E402

    plt.rcParams.update(
        {
            "figure.figsize": (6.4, 4.8),
            "figure.dpi": 100,
            "savefig.dpi": 100,
            "font.family": "DejaVu Sans",
            "axes.grid": True,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "path.simplify": False,
            "figure.constrained_layout.use": False,
        }
    )

    x = np.arange(len(samples), dtype=np.int64)
    y = np.array(samples, dtype=np.float64)

    fig, ax = plt.subplots()
    ax.plot(x, y, color="#1f77b4", linewidth=1.5, marker="o", markersize=3)
    ax.set_title("Deterministic Sample Series")
    ax.set_xlabel("index")
    ax.set_ylabel("value")
    ax.margins(x=0.02)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=str(path.parent)) as tmp:
        tmp_path = Path(tmp.name)
    try:
        fig.savefig(
            tmp_path,
            format="png",
            bbox_inches="tight",
            pad_inches=0.1,
            facecolor="white",
            edgecolor="none",
            metadata={},
        )
        plt.close(fig)
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
@dataclass(frozen=True)
class PipelineOutputs:
    output_dir: Path
    results_json: Path
    figure_png: Path


def run_pipeline(output_dir: Path, seed: int = 0, n_samples: int = 50) -> Tuple[Dict[str, Any], PipelineOutputs]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(int(seed))
    samples = rng.normal(loc=0.0, scale=1.0, size=int(n_samples)).astype(np.float64).tolist()

    results = _make_results(seed=int(seed), samples=samples)

    results_path = output_dir / "results.json"
    fig_path = output_dir / "figure.png"

    _atomic_write_text(results_path, canonical_json_dumps(results), encoding="utf-8")
    _write_figure_png(fig_path, samples=samples)

    return results, PipelineOutputs(output_dir=output_dir, results_json=results_path, figure_png=fig_path)


def run_and_hash(output_dir: Path, seed: int = 0, n_samples: int = 50) -> Dict[str, str]:
    _, outs = run_pipeline(output_dir=output_dir, seed=seed, n_samples=n_samples)
    return {"results.json": file_sha256(outs.results_json), "figure.png": file_sha256(outs.figure_png)}
