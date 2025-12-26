"""Command-line interface for the blessed_pipeline package.

This CLI is intentionally small and stable: it runs the blessed pipeline and can
emit a JSON artifact/manifest for integration validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence


@dataclass
class RunResult:
    ok: bool
    message: str = ""
    data: Any = None


def _resolve_runner() -> Callable[..., Any]:
    """Resolve a runnable entry from blessed_pipeline.pipeline with fallbacks."""
    try:
        from blessed_pipeline import pipeline as mod  # type: ignore
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"Failed to import blessed_pipeline.pipeline: {e}") from e

    for name in ("run_pipeline", "run", "main"):
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn

    Pipeline = getattr(mod, "Pipeline", None)
    if Pipeline is not None:
        inst = Pipeline()  # type: ignore[call-arg]
        fn = getattr(inst, "run", None)
        if callable(fn):
            return fn  # type: ignore[return-value]

    raise SystemExit(
        "No runnable entry found in blessed_pipeline.pipeline "
        "(expected run_pipeline/run/main or Pipeline().run)."
    )


def _coerce_path(p: Optional[str]) -> Optional[Path]:
    return None if p in (None, "", "-") else Path(p)


def _write_artifact(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_cli(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="blessed-pipeline", add_help=True)
    parser.add_argument("--input", "-i", dest="input_path", default=None, help="Input file/dir path (optional).")
    parser.add_argument("--output", "-o", dest="output_path", default=None, help="Output file/dir path (optional).")
    parser.add_argument(
        "--emit-artifacts",
        dest="artifact_path",
        default=None,
        help="Write a JSON manifest/result to this path (optional).",
    )
    parser.add_argument("--json", action="store_true", help="Print a JSON summary to stdout.")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-error output.")
    parser.add_argument("--version", action="store_true", help="Print version and exit.")

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.version:
        try:
            from blessed_pipeline import __version__  # type: ignore
        except Exception:
            __version__ = "0.0.0"
        print(__version__)
        return 0

    runner = _resolve_runner()

    in_path = _coerce_path(args.input_path)
    out_path = _coerce_path(args.output_path)
    artifact_path = _coerce_path(args.artifact_path)

    result = RunResult(ok=True, message="completed", data=None)
    exc_text: Optional[str] = None

    try:
        try:
            rv = runner(input_path=in_path, output_path=out_path)
        except TypeError:
            try:
                rv = runner(in_path, out_path)
            except TypeError:
                rv = runner()
        result.data = rv
    except SystemExit:
        raise
    except Exception as e:  # pragma: no cover
        result.ok = False
        result.message = f"{type(e).__name__}: {e}"
        exc_text = result.message

    payload = {
        "ok": result.ok,
        "message": result.message,
        "input_path": str(in_path) if in_path else None,
        "output_path": str(out_path) if out_path else None,
        "data": result.data if isinstance(result.data, (dict, list, str, int, float, bool)) or result.data is None else str(result.data),
    }

    if artifact_path is not None:
        _write_artifact(artifact_path, payload)

    if args.json:
        print(json.dumps(payload, sort_keys=True))
    elif not args.quiet:
        if result.ok:
            msg = result.message or "ok"
            print(msg)
        else:
            print(exc_text or result.message, file=sys.stderr)

    return 0 if result.ok else 1


def main() -> None:
    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()
