"""toy_pipeline: a tiny, deterministic end-to-end toy experiment pipeline.

Public API is intentionally small and stable:
- run_experiment: execute the experiment end-to-end and write artifacts
- ensure_outputs_dir, write_json: reproducible output helpers
- plot_results: deterministic plotting helper
"""
from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Optional

__all__ = [
    "__version__",
    "run_experiment",
    "ensure_outputs_dir",
    "write_json",
    "plot_results",
]

__version__ = "0.1.0"
def _load_attr(module: str, attr: str):
    try:
        mod = import_module(module)
    except Exception as e:  # pragma: no cover
        raise ImportError(
            f"Failed to import '{module}'. Package may be partially installed or missing runtime dependencies."
        ) from e
    try:
        return getattr(mod, attr)
    except AttributeError as e:  # pragma: no cover
        raise ImportError(f"Module '{module}' does not define '{attr}'.") from e
def run_experiment(
    *,
    outputs_dir: str = "./outputs",
    seed: int = 0,
    n_samples: int = 256,
    noise: float = 0.1,
) -> Dict[str, Any]:
    """Run the toy experiment and write JSON + PNG artifacts into outputs_dir."""
    fn = _load_attr("toy_pipeline.experiment", "run_experiment")
    return fn(outputs_dir=outputs_dir, seed=seed, n_samples=n_samples, noise=noise)
def ensure_outputs_dir(outputs_dir: str = "./outputs") -> str:
    """Create (if needed) and return the canonical outputs directory path."""
    fn = _load_attr("toy_pipeline.io", "ensure_outputs_dir")
    return fn(outputs_dir=outputs_dir)
def write_json(path: str, obj: Dict[str, Any], *, indent: int = 2) -> None:
    """Write canonical JSON with stable ordering for reproducible artifacts."""
    fn = _load_attr("toy_pipeline.io", "write_json")
    return fn(path, obj, indent=indent)
def plot_results(
    results: Dict[str, Any],
    *,
    out_path: Optional[str] = None,
    outputs_dir: str = "./outputs",
) -> str:
    """Create a deterministic plot from results and save it as a PNG."""
    fn = _load_attr("toy_pipeline.plotting", "plot_results")
    return fn(results, out_path=out_path, outputs_dir=outputs_dir)
