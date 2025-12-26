from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import os
import random
from typing import Any, Dict, Iterable, List, Optional, Tuple
def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)

def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)

def write_json(path: Path, obj: Any) -> None:
    _atomic_write_text(path, _canonical_json(obj) + "\n")

def write_log(path: Path, lines: Iterable[str]) -> None:
    text = "".join((ln if ln.endswith("\n") else ln + "\n") for ln in lines)
    _atomic_write_text(path, text)
@dataclass(frozen=True)
class PipelineConfig:
    seed: int = 0
    n: int = 101
    a: float = 0.15
    b: float = 0.07

    def to_dict(self) -> Dict[str, Any]:
        return {"seed": int(self.seed), "n": int(self.n), "a": float(self.a), "b": float(self.b)}
def make_run_stamp(config: Dict[str, Any]) -> Dict[str, Any]:
    canonical = _canonical_json(config)
    run_id = _sha256_hex(canonical)[:16]
    return {
        "run_id": run_id,
        "deterministic": True,
        "config": config,
        "config_sha256": _sha256_hex(canonical),
        "generated_utc": "1970-01-01T00:00:00Z",
        "version": 1,
    }

def compute_results(config: Dict[str, Any]) -> Dict[str, Any]:
    seed = int(config.get("seed", 0))
    n = int(config.get("n", 101))
    a = float(config.get("a", 0.15))
    b = float(config.get("b", 0.07))
    if n <= 0:
        raise ValueError("n must be positive")

    rng = random.Random(seed)
    series: List[Dict[str, float]] = []
    acc = 0.0
    acc2 = 0.0
    for i in range(n):
        x = float(i)
        noise = (rng.random() - 0.5) * 0.1
        y = math.sin(a * x) + math.cos(b * x) + noise
        series.append({"x": x, "y": float(y)})
        acc += y
        acc2 += y * y

    mean = acc / n
    var = max(0.0, (acc2 / n) - mean * mean)
    stdev = math.sqrt(var)
    y_min = min(p["y"] for p in series)
    y_max = max(p["y"] for p in series)

    return {
        "summary": {
            "n": n,
            "mean": mean,
            "stdev": stdev,
            "min": y_min,
            "max": y_max,
        },
        "series": series,
        "version": 1,
    }
_TINY_PNG_1X1 = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000A49444154789C6360000002000154A24F600000000049454E44AE426082"
)

def write_figure_png(path: Path, results: Dict[str, Any]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        xs = [p["x"] for p in results.get("series", [])]
        ys = [p["y"] for p in results.get("series", [])]
        fig = plt.figure(figsize=(6.4, 4.8), dpi=100)
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(xs, ys, color="black", linewidth=1.0)
        ax.set_title("Deterministic Results")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(True, color="#cccccc", linewidth=0.5)
        fig.tight_layout()
        fig.savefig(path, format="png", dpi=100, metadata={})
        plt.close(fig)
    except Exception:
        _atomic_write_bytes(path, _TINY_PNG_1X1)
def run_pipeline(
    out_dir: Path,
    config: Optional[Dict[str, Any]] = None,
    extra_log_lines: Optional[List[str]] = None,
) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = PipelineConfig().to_dict()
    if config:
        for k in ("seed", "n", "a", "b"):
            if k in config:
                cfg[k] = config[k]
    cfg = PipelineConfig(**cfg).to_dict()

    run_stamp = make_run_stamp(cfg)
    results = compute_results(cfg)

    log_lines = [
        "pipeline: deterministic=true",
        f"run_id: {run_stamp['run_id']}",
        f"config_sha256: {run_stamp['config_sha256']}",
        f"n: {results['summary']['n']}",
        f"mean: {results['summary']['mean']}",
        f"stdev: {results['summary']['stdev']}",
    ]
    if extra_log_lines:
        log_lines.extend(extra_log_lines)

    write_json(out_dir / "run_stamp.json", run_stamp)
    write_log(out_dir / "run.log", log_lines)
    write_json(out_dir / "results.json", results)
    write_figure_png(out_dir / "figure.png", results)
    return results
