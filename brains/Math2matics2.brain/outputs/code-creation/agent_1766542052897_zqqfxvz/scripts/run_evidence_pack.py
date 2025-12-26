#!/usr/bin/env python3
"""CLI entrypoint to run the end-to-end evidence-pack pipeline.

This script delegates to :mod:`src.pipeline` and ensures the project root is on
``sys.path`` when invoked as ``python scripts/run_evidence_pack.py``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional
def _add_project_root_to_syspath() -> Path:
    # scripts/ -> project_root/
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root
def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the single-cycle evidence pack pipeline.")
    p.add_argument(
        "--outputs-dir",
        type=Path,
        default=None,
        help="Directory to write artifacts into (default: <repo>/outputs).",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Deterministic seed passed through to the pipeline (default: 0).",
    )
    p.add_argument(
        "--run-tests",
        action="store_true",
        help="If supported by the pipeline, execute smoke tests and write test.log.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-essential stdout (errors still print).",
    )
    return p.parse_args(argv)
def _run_pipeline(outputs_dir: Path, seed: int, run_tests: bool) -> Dict[str, Any]:
    try:
        from src import pipeline  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Could not import src.pipeline. Ensure you are running from the repository root "
            "or that the project is installed as a package."
        ) from e

    # Prefer a dedicated entrypoint if present; otherwise fall back to a generic run().
    if hasattr(pipeline, "run_evidence_pack"):
        fn = getattr(pipeline, "run_evidence_pack")
        return fn(outputs_dir=outputs_dir, seed=seed, run_tests=run_tests)
    if hasattr(pipeline, "run"):
        fn = getattr(pipeline, "run")
        try:
            return fn(outputs_dir=outputs_dir, seed=seed, run_tests=run_tests)
        except TypeError:
            # Back-compat: allow older signature without run_tests.
            return fn(outputs_dir=outputs_dir, seed=seed)
    raise RuntimeError("src.pipeline is missing a callable run_evidence_pack(...) or run(...).")
def main(argv: Optional[list[str]] = None) -> int:
    project_root = _add_project_root_to_syspath()
    args = _parse_args(argv)

    outputs_dir = args.outputs_dir or (project_root / "outputs")
    outputs_dir = outputs_dir.resolve()

    try:
        result = _run_pipeline(outputs_dir=outputs_dir, seed=int(args.seed), run_tests=bool(args.run_tests))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if not args.quiet:
        # Keep stdout short while still being useful in CI logs.
        status = result.get("status") if isinstance(result, dict) else None
        print(f"OK: pipeline finished (status={status!r})")
        print(f"OK: outputs_dir={outputs_dir}")
    return 0
if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
