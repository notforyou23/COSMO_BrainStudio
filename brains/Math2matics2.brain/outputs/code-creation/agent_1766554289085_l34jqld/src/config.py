"""Default configuration and lightweight schemas for the toy robust-estimation experiment.

This project simulates heavy-tailed data and compares the sample mean vs median-of-means (MoM).
The config is intentionally simple, JSON-serializable, and stable across runs.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple
@dataclass(frozen=True)
class ExperimentConfig:
    """Default experiment parameters (JSON-serializable via asdict())."""

    seed: int = 12345
    n_list: Tuple[int, ...] = (50, 100, 200, 500, 1000)
    repetitions: int = 400

    # Data generating process
    distribution: str = "student_t"  # {"student_t", "pareto_mixture"}
    true_mean: float = 0.0

    # student_t params
    t_df: float = 2.5  # df <= 2 yields infinite variance; df <= 1 yields infinite mean

    # pareto_mixture params: with prob p, draw Pareto(alpha) with scale xm, else Normal(0,1)
    mixture_p: float = 0.05
    pareto_alpha: float = 1.5
    pareto_xm: float = 1.0

    # Estimators
    mom_blocks: Tuple[int, ...] = (2, 5, 10, 20)

    # Error metric: absolute error around known true_mean
    error_metric: str = "abs"  # {"abs", "sq"}

    # Output paths (relative to repo runtime root)
    out_dir: str = "outputs"
    results_json: str = "outputs/results.json"
    figure_png: str = "outputs/mom_vs_mean.png"
    run_log: str = "outputs/run.log"

    # Plot config
    ci_alpha: float = 0.2  # shading for uncertainty bands (if used)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ExperimentConfig":
        # tolerate tuples/lists interchangeably for sequence fields
        def _as_tuple(x: Any) -> Tuple[int, ...]:
            return tuple(int(v) for v in x)
        kwargs = dict(d)
        if "n_list" in kwargs:
            kwargs["n_list"] = _as_tuple(kwargs["n_list"])
        if "mom_blocks" in kwargs:
            kwargs["mom_blocks"] = _as_tuple(kwargs["mom_blocks"])
        return ExperimentConfig(**kwargs)
DEFAULT_CONFIG: Dict[str, Any] = ExperimentConfig().to_dict()

# Minimal schema-like guidance for results.json. This is not JSON-Schema; it is a stable contract.
RESULTS_CONTRACT: Dict[str, Any] = {
    "version": 1,
    "metadata": {
        "project": "generated_script_1766550130997",
        "created_utc": "ISO-8601 string",
        "python": "sys.version",
        "platform": "platform.platform()",
        "numpy": "np.__version__",
        "matplotlib": "matplotlib.__version__",
        "config": "ExperimentConfig as dict",
        "run_id": "short unique id",
        "seed": "int",
    },
    "data": {
        "n_list": "list[int]",
        "repetitions": "int",
        "distribution": "str",
        "true_mean": "float",
    },
    "results": [
        {
            "n": "int",
            "estimator": "str",  # "mean" or "mom_k"
            "mom_blocks": "int or null",
            "errors": "list[float] length=repetitions",
            "summary": {
                "mean_error": "float",
                "median_error": "float",
                "p90_error": "float",
            },
        }
    ],
}

# Keys that a run logger should record (in addition to arbitrary extras).
RUN_LOG_FIELDS: Tuple[str, ...] = (
    "created_utc",
    "run_id",
    "seed",
    "distribution",
    "repetitions",
    "n_list",
    "mom_blocks",
    "results_json",
    "figure_png",
)
def get_default_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return a JSON-serializable config dict, optionally overridden by `overrides`."""
    cfg = dict(DEFAULT_CONFIG)
    if overrides:
        for k, v in overrides.items():
            cfg[k] = v
    return cfg


def validate_config(cfg: Dict[str, Any]) -> None:
    """Lightweight validation for common mistakes; raises ValueError on failure."""
    if int(cfg.get("repetitions", 0)) <= 0:
        raise ValueError("repetitions must be positive")
    n_list = cfg.get("n_list", [])
    if not isinstance(n_list, (list, tuple)) or len(n_list) == 0:
        raise ValueError("n_list must be a non-empty list/tuple of ints")
    if any(int(n) <= 0 for n in n_list):
        raise ValueError("all n in n_list must be positive")
    dist = cfg.get("distribution")
    if dist not in {"student_t", "pareto_mixture"}:
        raise ValueError("distribution must be 'student_t' or 'pareto_mixture'")
    metric = cfg.get("error_metric")
    if metric not in {"abs", "sq"}:
        raise ValueError("error_metric must be 'abs' or 'sq'")
    blocks = cfg.get("mom_blocks", [])
    if not isinstance(blocks, (list, tuple)) or len(blocks) == 0:
        raise ValueError("mom_blocks must be a non-empty list/tuple of ints")
    if any(int(b) <= 1 for b in blocks):
        raise ValueError("mom_blocks values must be >= 2")
