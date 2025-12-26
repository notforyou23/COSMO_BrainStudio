"""Import smoke tests.

These tests are intentionally small and strict: they fail fast on any
ImportError/SyntaxError so CI catches broken packaging or invalid syntax.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
# Ensure the local `src/` layout is importable when running tests without an
# installed wheel (e.g. `pytest` from a fresh checkout).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
PUBLIC_ENTRYPOINTS = [
    # Top-level package (namespace package is OK).
    "cosmo_contracts",
    # Key module explicitly mentioned in the mission summary.
    "cosmo_contracts.markdown",
]
@pytest.mark.parametrize("module_name", PUBLIC_ENTRYPOINTS)
def test_import_public_entrypoints(module_name: str) -> None:
    """Import each public entrypoint; any ImportError/SyntaxError fails."""
    importlib.import_module(module_name)
