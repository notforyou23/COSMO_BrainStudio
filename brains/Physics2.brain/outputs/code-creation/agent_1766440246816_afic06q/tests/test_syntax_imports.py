"""Regression tests: importing key modules must not raise SyntaxError.

These tests protect against accidental broken syntax or import-time crashes in
modules that are used by the CLI and package helpers.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def _ensure_import_paths() -> None:
    """Ensure repo root and src/ are importable when running tests."""
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "src"
    for p in (str(repo_root), str(src_dir)):
        if p not in sys.path:
            sys.path.insert(0, p)


@pytest.mark.parametrize(
    "module_name",
    [
        "qg_bench.cli",
        "cosmo_contracts.markdown",
    ],
)
def test_import_modules_no_syntaxerror(module_name: str) -> None:
    _ensure_import_paths()
    try:
        importlib.import_module(module_name)
    except SyntaxError as e:
        pytest.fail(f"SyntaxError importing {module_name}: {e}", pytrace=True)
    except Exception as e:
        pytest.fail(f"Importing {module_name} raised {type(e).__name__}: {e}", pytrace=True)
