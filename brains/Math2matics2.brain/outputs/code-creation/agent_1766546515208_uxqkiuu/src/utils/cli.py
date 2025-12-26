"""Argument parsing helpers for the generator CLI.

This module centralizes common CLI flags used by scripts that deterministically
generate artifacts into an output directory.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
@dataclass(frozen=True)
class OutputPaths:
    """Resolved output locations for generated artifacts."""

    out_dir: Path
    coverage_matrix_csv: Path
    eval_loop_md: Path
def _p(path: str) -> Path:
    return Path(path).expanduser()
def add_output_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add standard output/overwrite controls to an existing parser."""

    grp = parser.add_argument_group("outputs")
    grp.add_argument(
        "--out-dir",
        type=_p,
        default=Path("outputs"),
        help="Directory to write generated artifacts to (default: outputs).",
    )
    grp.add_argument(
        "--coverage-matrix-path",
        type=_p,
        default=None,
        help="Explicit path for coverage_matrix.csv (default: <out-dir>/coverage_matrix.csv).",
    )
    grp.add_argument(
        "--eval-loop-path",
        type=_p,
        default=None,
        help="Explicit path for eval_loop.md (default: <out-dir>/eval_loop.md).",
    )
    grp.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing output files.",
    )
    grp.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse arguments and print resolved paths without writing files.",
    )
    return parser
def build_parser(
    prog: Optional[str] = None,
    description: Optional[str] = None,
    extra_args: Optional[Iterable[tuple[list[str], dict]]] = None,
) -> argparse.ArgumentParser:
    """Create a parser preloaded with the standard output args.

    extra_args: iterable of (flags, kwargs) forwarded to parser.add_argument.
    """

    parser = argparse.ArgumentParser(prog=prog, description=description)
    add_output_args(parser)
    if extra_args:
        for flags, kwargs in extra_args:
            parser.add_argument(*flags, **kwargs)
    return parser
def resolve_output_paths(args: argparse.Namespace) -> OutputPaths:
    """Resolve output paths from parsed args.

    - If explicit per-file paths are not provided, they are derived from out_dir.
    - Returned paths are *not* created here; filesystem operations live elsewhere.
    """

    out_dir = Path(getattr(args, "out_dir")).expanduser()
    cov = getattr(args, "coverage_matrix_path", None)
    evl = getattr(args, "eval_loop_path", None)

    coverage_matrix_csv = (Path(cov).expanduser() if cov else out_dir / "coverage_matrix.csv")
    eval_loop_md = (Path(evl).expanduser() if evl else out_dir / "eval_loop.md")

    return OutputPaths(
        out_dir=out_dir,
        coverage_matrix_csv=coverage_matrix_csv,
        eval_loop_md=eval_loop_md,
    )
def parse_args(argv: Optional[list[str]] = None) -> tuple[argparse.Namespace, OutputPaths]:
    """Convenience wrapper returning (args, resolved_paths)."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return args, resolve_output_paths(args)
