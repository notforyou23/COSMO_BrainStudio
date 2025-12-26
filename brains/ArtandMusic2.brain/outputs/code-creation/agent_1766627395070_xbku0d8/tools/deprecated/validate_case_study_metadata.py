"""Deprecated compatibility wrapper for case-study metadata validation.

This module exists to preserve older invocation paths while the repository
standardizes on a single blessed entrypoint: `tools/metadata_cli.py`.

Use instead:
  python -m tools.metadata_cli validate <metadata.json>
  python -m tools.metadata_cli --help
"""

from __future__ import annotations

import importlib
import os
import sys
from typing import List, Optional


_DEPRECATION_MESSAGE = (
    "DEPRECATION: 'tools/deprecated/validate_case_study_metadata.py' is deprecated and will be removed.\n"
    "Please use the single blessed CLI entrypoint instead:\n"
    "  python -m tools.metadata_cli validate <metadata.json>\n"
    "Run `python -m tools.metadata_cli --help` for usage.\n"
)


def _emit_deprecation_notice() -> None:
    stream = sys.stderr
    try:
        stream.write(_DEPRECATION_MESSAGE)
        if not _DEPRECATION_MESSAGE.endswith("\n"):
            stream.write("\n")
        stream.flush()
    except Exception:
        pass


def _run_metadata_cli(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Avoid duplicate banners if nested/recursive invocations occur.
    if os.environ.get("COSMO_METADATA_CLI_NO_DEPRECATION") != "1":
        _emit_deprecation_notice()
        os.environ["COSMO_METADATA_CLI_NO_DEPRECATION"] = "1"

    try:
        mod = importlib.import_module("tools.metadata_cli")
    except Exception as e:
        sys.stderr.write(
            "ERROR: Could not import 'tools.metadata_cli'. Ensure you are running from the repo root "
            "and that the 'tools' package exists. Details: %r\n" % (e,)
        )
        return 2

    # Prefer an explicit `main(argv)` if present; fall back to `cli()` or module execution.
    for attr in ("main", "cli"):
        fn = getattr(mod, attr, None)
        if callable(fn):
            try:
                rc = fn(argv)
            except SystemExit as se:
                return int(se.code) if se.code is not None else 0
            return int(rc) if rc is not None else 0

    sys.stderr.write(
        "ERROR: 'tools.metadata_cli' does not expose a callable 'main(argv)' or 'cli(argv)'.\n"
    )
    return 2


def main(argv: Optional[List[str]] = None) -> int:
    return _run_metadata_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
