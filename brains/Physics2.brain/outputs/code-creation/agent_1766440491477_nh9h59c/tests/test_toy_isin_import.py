import importlib
from pathlib import Path

import pytest


def _repo_root() -> Path:
    # tests/ is expected to live at repo_root/tests/
    return Path(__file__).resolve().parents[1]


def _discover_toy_isin_modules() -> list[str]:
    root = _repo_root()

    modules: list[str] = []

    # Common layout: repo_root/src/experiments/toy_isin*.py
    for py in sorted(root.glob("src/experiments/toy_isin*.py")):
        if py.name == "__init__.py":
            continue
        modules.append(f"src.experiments.{py.stem}")

    # Also allow package-style modules: repo_root/src/experiments/toy_isin*/
    for pkg_init in sorted(root.glob("src/experiments/toy_isin*/__init__.py")):
        pkg = pkg_init.parent.name
        modules.append(f"src.experiments.{pkg}")

    # De-duplicate while preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for m in modules:
        if m not in seen:
            uniq.append(m)
            seen.add(m)
    return uniq


TOY_ISIN_MODULES = _discover_toy_isin_modules()


@pytest.mark.parametrize("module_name", TOY_ISIN_MODULES)
def test_toy_isin_modules_import(module_name: str) -> None:
    """Regression: ensure toy_isin* modules are syntactically valid and importable."""
    importlib.import_module(module_name)


def test_toy_isin_modules_present_or_skipped() -> None:
    """If the modules don't exist in this checkout, skip rather than erroring."""
    if not TOY_ISIN_MODULES:
        pytest.skip("No src/experiments/toy_isin* modules found in this checkout.")
