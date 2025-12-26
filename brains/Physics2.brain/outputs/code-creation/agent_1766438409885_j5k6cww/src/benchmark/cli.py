"""Command-line interface for benchmark reproduction and verification.

This CLI is used by outputs/README.md to:
1) reproduce a benchmark case into a JSON artifact, and
2) optionally verify the produced JSON against an expected JSON with tolerances.

It intentionally wraps :mod:`benchmark.reproduce` and :mod:`benchmark.json_compare`
so both end-to-end pytest and humans use the exact same code paths.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import argparse
import json
import sys
def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _cmd_reproduce(ns: argparse.Namespace) -> int:
    from .reproduce import reproduce, write_json, verify_against_expected

    produced = reproduce(ns.case_id, seed=ns.seed)
    write_json(produced, ns.out)

    if ns.expected is not None:
        verify_against_expected(produced, ns.expected, rtol=ns.rtol, atol=ns.atol)

    if ns.print_json:
        json.dump(produced, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


def _cmd_compare(ns: argparse.Namespace) -> int:
    from .json_compare import assert_json_close

    actual = _load_json(ns.actual)
    expected = _load_json(ns.expected)
    assert_json_close(actual, expected, rtol=ns.rtol, atol=ns.atol, max_diffs=ns.max_diffs)
    return 0
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="benchmark", description="Reproduce and verify deterministic benchmark outputs.")
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("reproduce", help="Reproduce a benchmark case and write JSON.")
    pr.add_argument("case_id", choices=["benchmark_case_001"])
    pr.add_argument("--seed", type=int, default=0, help="RNG seed (default: 0).")
    pr.add_argument("--out", type=Path, required=True, help="Output JSON path to write.")
    pr.add_argument("--expected", type=Path, default=None, help="Optional expected JSON to validate against.")
    pr.add_argument("--rtol", type=float, default=1e-7, help="Relative tolerance for numeric comparisons.")
    pr.add_argument("--atol", type=float, default=1e-9, help="Absolute tolerance for numeric comparisons.")
    pr.add_argument("--print-json", action="store_true", help="Also print the produced JSON to stdout.")
    pr.set_defaults(func=_cmd_reproduce)

    pc = sub.add_parser("compare", help="Compare two JSON files with numeric tolerances.")
    pc.add_argument("--actual", type=Path, required=True, help="Produced/actual JSON file.")
    pc.add_argument("--expected", type=Path, required=True, help="Expected JSON file.")
    pc.add_argument("--rtol", type=float, default=1e-7)
    pc.add_argument("--atol", type=float, default=1e-9)
    pc.add_argument("--max-diffs", type=int, default=20)
    pc.set_defaults(func=_cmd_compare)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    ns = build_parser().parse_args(argv)
    try:
        return int(ns.func(ns))
    except AssertionError as e:
        sys.stderr.write(str(e).rstrip() + "\n")
        return 2
    except Exception as e:  # pragma: no cover
        sys.stderr.write(f"ERROR: {e}\n")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
