"""minipipe.run

Module entrypoint for CI-friendly execution:

    python -m minipipe.run

Delegates to minipipe.pipeline and exits with a non-zero code on failure.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m minipipe.run", add_help=True)
    p.add_argument(
        "--outputs",
        default="outputs",
        help="Output directory to create/write (default: outputs)",
    )
    p.add_argument(
        "--cwd",
        default=None,
        help="Working directory to chdir into before running (default: current)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce stdout output (errors still go to stderr).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cwd:
        Path(args.cwd).expanduser().resolve().mkdir(parents=True, exist_ok=True)
        try:
            import os

            os.chdir(args.cwd)
        except Exception as e:  # pragma: no cover
            print(f"ERROR: failed to chdir to {args.cwd!r}: {e}", file=sys.stderr)
            return 2

    out_dir = Path(args.outputs).expanduser().resolve()
    try:
        from . import pipeline as _pipeline
    except Exception as e:
        print(f"ERROR: failed to import minipipe.pipeline: {e}", file=sys.stderr)
        return 2

    try:
        if hasattr(_pipeline, "run_pipeline"):
            result = _pipeline.run_pipeline(out_dir=out_dir)
        elif hasattr(_pipeline, "Pipeline"):
            result = _pipeline.Pipeline(out_dir=out_dir).run()
        else:
            raise AttributeError(
                "minipipe.pipeline must define run_pipeline(out_dir=...) or Pipeline(...).run()"
            )
        if not args.quiet:
            print(f"OK: pipeline completed; outputs at {out_dir}")
            if result is not None:
                print(f"RESULT: {result}")
        return 0
    except SystemExit as e:
        code = int(getattr(e, "code", 1) or 0)
        if code != 0:
            print(f"ERROR: pipeline exited with status {code}", file=sys.stderr)
        return code
    except Exception as e:
        print(f"ERROR: pipeline failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
