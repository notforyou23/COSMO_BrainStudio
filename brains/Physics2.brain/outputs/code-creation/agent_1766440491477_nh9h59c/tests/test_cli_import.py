"""Regression tests for importing the CLI module.

These tests ensure the project CLI can be imported without syntax errors and
exposes a callable entrypoint suitable for console_scripts / python -m usage.
"""

from __future__ import annotations

import importlib
import inspect

import pytest
def test_cli_module_importable() -> None:
    """Importing qg_bench.cli should not raise (e.g., SyntaxError)."""
    try:
        importlib.import_module("qg_bench.cli")
    except SyntaxError as e:  # pragma: no cover
        pytest.fail(f"SyntaxError importing qg_bench.cli: {e}")
@pytest.mark.parametrize(
    "candidates",
    [
        ("main", "cli", "app", "entrypoint", "run"),
        ("get_parser", "build_parser"),
    ],
)
def test_cli_exposes_expected_entrypoints(candidates: tuple[str, ...]) -> None:
    """qg_bench.cli should expose at least one conventional entrypoint.

    We accept multiple common patterns (argparse/click/typer) to avoid coupling
    to the implementation details while still preventing regressions.
    """
    mod = importlib.import_module("qg_bench.cli")

    found = []
    for name in candidates:
        if hasattr(mod, name):
            obj = getattr(mod, name)
            if callable(obj) or inspect.isfunction(obj):
                found.append(name)

    assert found, (
        "qg_bench.cli imported but does not expose any expected entrypoint "
        f"attributes from {candidates}. Found none."
    )
