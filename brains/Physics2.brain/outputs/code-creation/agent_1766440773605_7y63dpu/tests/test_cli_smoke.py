"""Smoke tests for CLI-related modules.

These tests are intentionally lightweight: they mainly ensure that modules
import and their --help entrypoints execute without raising unexpected errors.
"""

from __future__ import annotations

import runpy
import sys
from importlib import import_module
from pathlib import Path

import pytest
def test_import_cli_modules_parse_clean() -> None:
    # If any of these modules contain syntax errors, import will fail here.
    for mod in ("numeric_compare", "dgpipe", "experiments", "experiments.registry"):
        import_module(mod)
def test_numeric_compare_module_help_runs() -> None:
    # Running with --help should exit cleanly via argparse (SystemExit code 0/2).
    argv_old = sys.argv[:]
    try:
        sys.argv = ["numeric_compare", "--help"]
        with pytest.raises(SystemExit):
            runpy.run_module("numeric_compare", run_name="__main__")
    finally:
        sys.argv = argv_old
def test_init_repo_skeleton_script_help_runs() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "init_repo_skeleton.py"
    assert script.is_file(), f"Expected script at {script}"

    argv_old = sys.argv[:]
    try:
        sys.argv = [str(script), "--help"]
        with pytest.raises(SystemExit):
            runpy.run_path(str(script), run_name="__main__")
    finally:
        sys.argv = argv_old
