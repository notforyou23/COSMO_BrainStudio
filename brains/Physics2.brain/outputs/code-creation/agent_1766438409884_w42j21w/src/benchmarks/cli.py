"""Command-line interface for the benchmarks reference implementation.

Validates a benchmark run JSON file against the local JSON Schema and can
optionally compare an outputs directory to an expected-outputs directory.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

from .validate import format_errors, validate_run_file
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*")):
        if p.is_file():
            yield p


def _compare_dirs(expected: Path, actual: Path, *, strict: bool = True) -> Tuple[bool, List[str]]:
    """Compare directory trees by file presence and SHA-256.

    If strict is True, extra files in `actual` that are not in `expected` fail.
    """
    exp_files = {p.relative_to(expected): p for p in _iter_files(expected)}
    act_files = {p.relative_to(actual): p for p in _iter_files(actual)}

    problems: List[str] = []
    for rel, pexp in exp_files.items():
        pact = act_files.get(rel)
        if pact is None:
            problems.append(f"MISSING: {rel.as_posix()}")
            continue
        if _sha256(pexp) != _sha256(pact):
            problems.append(f"DIFFERS: {rel.as_posix()}")
    if strict:
        for rel in sorted(set(act_files) - set(exp_files)):
            problems.append(f"EXTRA: {rel.as_posix()}")
    return (len(problems) == 0), problems
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="benchmarks-validate", description="Validate benchmark runs.")
    p.add_argument("run", type=Path, help="Path to a benchmark run JSON file.")
    p.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="Optional path to the root schema JSON file (or a directory containing it).",
    )
    p.add_argument(
        "--outputs",
        type=Path,
        default=None,
        help="Directory containing produced outputs to compare (optional).",
    )
    p.add_argument(
        "--expected",
        type=Path,
        default=None,
        help="Directory containing expected outputs to compare against (optional).",
    )
    p.add_argument(
        "--non-strict",
        action="store_true",
        help="Allow extra files in --outputs that are not present in --expected.",
    )
    p.add_argument("--max-errors", type=int, default=50, help="Max schema errors to print.")
    return p


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    schema = None
    if args.schema is not None:
        # Defer import to keep the CLI small and to reuse schema loader behavior.
        from .schema import load_schema

        schema = load_schema(schema_path=args.schema)

    ok, errors, _run = validate_run_file(args.run, schema=schema)
    if not ok:
        print(format_errors(errors, max_errors=args.max_errors), file=sys.stderr)
        return 2

    if (args.outputs is None) ^ (args.expected is None):
        print("Both --outputs and --expected must be provided to compare outputs.", file=sys.stderr)
        return 2

    if args.outputs is not None and args.expected is not None:
        exp = args.expected.expanduser().resolve()
        out = args.outputs.expanduser().resolve()
        if not exp.is_dir():
            print(f"--expected is not a directory: {exp}", file=sys.stderr)
            return 2
        if not out.is_dir():
            print(f"--outputs is not a directory: {out}", file=sys.stderr)
            return 2

        same, problems = _compare_dirs(exp, out, strict=not args.non_strict)
        if not same:
            for line in problems:
                print(line, file=sys.stderr)
            return 3

    print("OK")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
