"""rtv_baseline: minimal retrieve-then-verify (RTV) baseline.

This package initializer exposes stable, minimal entrypoints for:
- pipeline execution (retrieve-then-verify)
- evaluation over a curated set

Implementation details live in submodules; these wrappers keep a small, clean API.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def get_version(default: str = "0.0.0") -> str:
    """Best-effort package version lookup."""
    try:
        from importlib.metadata import version as _v  # py>=3.8

        return _v("rtv_baseline")
    except Exception:
        return default


__version__ = get_version()


def run_pipeline(
    claim: str,
    *,
    config: Optional[Dict[str, Any]] = None,
) -> Any:
    """Run the RTV pipeline on a single claim.

    Expected downstream return type is typically a VerificationDecision (see types.py),
    but this function is intentionally typed as Any to keep __init__ dependency-light.
    """
    try:
        from .pipeline import run_pipeline as _run  # type: ignore
    except Exception as e:
        raise ImportError(
            "rtv_baseline.pipeline.run_pipeline is not available yet; ensure submodules are installed/built."
        ) from e
    return _run(claim, config=config)


def evaluate(
    dataset_path: str,
    *,
    out_dir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Any:
    """Evaluate the RTV baseline on a dataset file.

    The evaluator is expected to emit metrics plus calibration / false-accept-by-risk-tier summaries.
    """
    try:
        from .eval import evaluate as _eval  # type: ignore
    except Exception as e:
        raise ImportError(
            "rtv_baseline.eval.evaluate is not available yet; ensure submodules are installed/built."
        ) from e
    return _eval(dataset_path, out_dir=out_dir, config=config)


def main(argv: Optional[list[str]] = None) -> int:
    """Console entrypoint delegating to rtv_baseline.cli if present."""
    try:
        from .cli import main as _main  # type: ignore
    except Exception as e:
        raise ImportError(
            "rtv_baseline.cli.main is not available yet; console scripts require the cli module."
        ) from e
    return int(_main(argv))


__all__ = [
    "__version__",
    "evaluate",
    "get_version",
    "main",
    "run_pipeline",
]
