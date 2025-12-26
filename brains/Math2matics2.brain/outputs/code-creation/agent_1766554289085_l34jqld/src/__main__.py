"""CLI entrypoint for running the project pipeline via: python -m src

This module delegates to src.pipeline.entrypoint while providing standard flags
for reproducible execution (seed) and output location (out-dir).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src", description="Run the toy pipeline end-to-end.")
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Deterministic seed (int). If omitted, the pipeline will choose and record one.",
    )
    p.add_argument(
        "--out-dir",
        type=str,
        default="outputs",
        help="Output directory for canonical artifacts (default: ./outputs).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    out_dir = Path(args.out_dir).expanduser()
    try:
        from .pipeline.entrypoint import main as pipeline_main
    except Exception as e:
        raise SystemExit(f"Failed to import pipeline entrypoint (src.pipeline.entrypoint.main): {e}") from e

    result = pipeline_main(seed=args.seed, out_dir=out_dir)
    if isinstance(result, int):
        return result
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
