"""
Backward-compatible shim for historical imports/CLI entrypoint.

This module preserves the legacy surface of `customer_discovery_outputs.py` while
delegating all implementation to `src.customer_discovery.outputs`.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from typing import Any, Optional, Sequence


def _impl():
    try:
        return importlib.import_module("src.customer_discovery.outputs")
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "Could not import refactored implementation module "
            "`src.customer_discovery.outputs`. Ensure the package exists on "
            "PYTHONPATH and the refactor stage has been applied."
        ) from e


def __getattr__(name: str) -> Any:
    # Delegate unknown attributes to the implementation module to preserve
    # historical import patterns without needing to hardcode every symbol.
    return getattr(_impl(), name)


def generate_customer_discovery_outputs(*args: Any, **kwargs: Any) -> Any:
    """
    Legacy-friendly wrapper.

    Delegates to the refactored implementation's `generate_customer_discovery_outputs`
    if present, otherwise falls back to `generate_outputs`.
    """
    m = _impl()
    if hasattr(m, "generate_customer_discovery_outputs"):
        return m.generate_customer_discovery_outputs(*args, **kwargs)
    if hasattr(m, "generate_outputs"):
        return m.generate_outputs(*args, **kwargs)
    raise AttributeError(
        "Implementation module lacks `generate_customer_discovery_outputs` "
        "and `generate_outputs`."
    )


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="customer_discovery_outputs.py",
        description="Customer discovery output generator (shim).",
        add_help=True,
    )
    # Keep arguments minimal and permissive; prefer deferring to implementation CLI.
    p.add_argument(
        "--version",
        action="store_true",
        help="Print the underlying implementation module name and exit.",
    )
    p.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to the implementation CLI if available.",
    )
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ns = _parse_args(argv)
    if ns.version:
        sys.stdout.write("src.customer_discovery.outputs\n")
        return 0

    m = _impl()

    # Prefer a first-class CLI in the implementation module.
    if hasattr(m, "main") and callable(m.main):
        # Forward only remaining args to avoid double-parsing conflicts.
        return int(m.main(ns.args))

    if hasattr(m, "cli") and callable(m.cli):
        return int(m.cli(ns.args))

    raise SystemExit(
        "No CLI entrypoint found in `src.customer_discovery.outputs` "
        "(expected `main(argv)` or `cli(argv)`)."
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
