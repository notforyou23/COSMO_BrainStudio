"""cli_tool package initializer.

Exposes:
- __version__ / get_version(): runtime package version (best-effort).
- run(): high-level entry point used by console scripts / CLI wrappers.
"""

from __future__ import annotations

from typing import Optional, Sequence


def _detect_version() -> str:
    """Return installed distribution version if available; otherwise '0.0.0'."""
    try:
        from importlib.metadata import PackageNotFoundError, version  # type: ignore
    except Exception:
        return "0.0.0"

    for dist_name in ("cli_tool", __package__ or "cli_tool"):
        try:
            v = version(dist_name)
            if v:
                return v
        except PackageNotFoundError:
            continue
        except Exception:
            continue
    return "0.0.0"


__version__ = _detect_version()


def get_version() -> str:
    """Return the package version."""
    return __version__


def _normalize_argv(argv: Optional[Sequence[str]]) -> list[str]:
    if argv is None:
        import sys

        return list(sys.argv[1:])
    return list(argv)


def run(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI implementation and return an exit code."""
    argv_list = _normalize_argv(argv)
    try:
        from . import cli as _cli  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "cli_tool.cli could not be imported; ensure the CLI implementation exists."
        ) from e

    entry = getattr(_cli, "main", None)
    if not callable(entry):
        entry = getattr(_cli, "run", None)
    if not callable(entry):
        raise RuntimeError("cli_tool.cli must expose a callable 'main' or 'run' function.")

    result = entry(argv_list)
    try:
        return int(result) if result is not None else 0
    except Exception:
        return 0


__all__ = ["__version__", "get_version", "run"]
