from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

__all__ = [
    "RESULTS_PATH",
    "DEFAULT_SEED",
    "get_results_path",
    "run_toy_experiment",
    "validate_results",
]

DEFAULT_SEED: int = 0

RESULTS_PATH: Path = Path("outputs") / "toy_experiment" / "results.json"


def get_results_path(base_dir: Optional[Path] = None) -> Path:
    base = Path.cwd() if base_dir is None else Path(base_dir)
    return base / RESULTS_PATH


def run_toy_experiment(
    *,
    seed: int = DEFAULT_SEED,
    output_path: Optional[Path] = None,
    base_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run the deterministic toy experiment and write the results artifact.

    - Determinism is controlled by `seed` (default: 0).
    - The default output path is `outputs/toy_experiment/results.json` under `base_dir`/CWD.
    """
    from .run import run_toy_experiment as _run

    if output_path is None:
        output_path = get_results_path(base_dir=base_dir)
    return _run(seed=seed, output_path=Path(output_path))


def validate_results(data: Dict[str, Any]) -> None:
    """Validate a results artifact dict; raises ValueError on schema violations."""
    from .results_schema import validate_results as _validate

    _validate(data)
