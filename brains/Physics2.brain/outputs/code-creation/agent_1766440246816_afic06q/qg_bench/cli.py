"""qg_bench command-line interface.

This module is intentionally lightweight and safe to import. It provides a
minimal argparse-based CLI with stable `main()`/`cli()` entry points.

Typical usage:
    python -m qg_bench.cli --help
"""
from __future__ import annotations

import argparse
import json
import sys
from importlib import metadata
from typing import Iterable, Optional
def get_version(dist_name: str = "qg-bench") -> str:
    """Return the installed distribution version if available.

    Falls back to "0.0.0" when running from source or if metadata is missing.
    """
    try:
        return metadata.version(dist_name)
    except metadata.PackageNotFoundError:
        return "0.0.0"
    except Exception:
        # Be conservative: never fail just because version metadata is odd.
        return "0.0.0"
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qg-bench",
        description="qg_bench: lightweight CLI entry point (smoke-test friendly).",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    subparsers = parser.add_subparsers(dest="command")

    p_echo = subparsers.add_parser("echo", help="Echo text to stdout.")
    p_echo.add_argument("text", nargs="*", help="Text to echo.")
    p_echo.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of plain text.",
    )

    subparsers.add_parser("noop", help="Do nothing and exit successfully.")
    return parser
def _cmd_echo(args: argparse.Namespace) -> int:
    text = " ".join(args.text or [])
    if args.json:
        sys.stdout.write(json.dumps({"text": text}) + "\n")
    else:
        sys.stdout.write(text + ("\n" if text else ""))
    return 0
def main(argv: Optional[Iterable[str]] = None) -> int:
    """CLI entry point returning an exit code."""
    parser = build_parser()
    ns = parser.parse_args(list(argv) if argv is not None else None)

    if ns.version:
        sys.stdout.write(get_version() + "\n")
        return 0

    cmd = ns.command
    if cmd in (None, ""):
        parser.print_help(sys.stdout)
        return 0
    if cmd == "echo":
        return _cmd_echo(ns)
    if cmd == "noop":
        return 0

    parser.error(f"Unknown command: {cmd!r}")
    return 2
def cli() -> None:
    """Console_script entry point."""
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    cli()
