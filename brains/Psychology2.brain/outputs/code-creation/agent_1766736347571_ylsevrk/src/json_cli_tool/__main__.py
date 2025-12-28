"""Entry point for running json_cli_tool via `python -m json_cli_tool`.

Delegates to the package CLI `main` function.
"""

from __future__ import annotations

import sys


def _resolve_cli_main():
    # Prefer a dedicated cli module if present.
    try:
        from .cli import main  # type: ignore
        return main
    except Exception:
        pass

    # Fallback to a public main exposed from the package.
    try:
        from . import main  # type: ignore
        return main
    except Exception as e:
        raise SystemExit(
            "json_cli_tool: could not import CLI main function "
            "(expected json_cli_tool.cli:main or json_cli_tool:main)"
        ) from e


def main(argv: list[str] | None = None) -> int:
    cli_main = _resolve_cli_main()
    result = cli_main(argv) if argv is not None else cli_main()
    if result is None:
        return 0
    try:
        return int(result)
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
