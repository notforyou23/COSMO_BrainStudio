"""COSMO benchmark contracts package.

Public API for:
- Contract data model + JSON schema validation
- Idempotent markdown rewriting to add/update 'Contract' sections
- Canonical contract generation + normalization helpers
- Compliance runner producing pass/fail + diagnostics per implementation

This module intentionally uses lazy imports so the package can be imported
even when optional submodules are not yet available in a partial install.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

__all__ = [
    "__version__",
    # schema/model
    "Contract",
    "ContractValidationError",
    "load_contract",
    "dump_contract",
    "validate_contract",
    "contract_json_schema",
    # markdown rewriting
    "rewrite_benchmarks_markdown",
    "parse_contract_blocks",
    # contract generation/helpers
    "default_contract",
    "normalize_contract",
    "render_contract_markdown",
    # compliance runner
    "run_compliance",
    "ComplianceReport",
]

__version__ = "0.1.0"
_EXPORTS: Dict[str, Tuple[str, str]] = {
    # schema/model
    "Contract": ("cosmo_contracts.schema", "Contract"),
    "ContractValidationError": ("cosmo_contracts.schema", "ContractValidationError"),
    "load_contract": ("cosmo_contracts.schema", "load_contract"),
    "dump_contract": ("cosmo_contracts.schema", "dump_contract"),
    "validate_contract": ("cosmo_contracts.schema", "validate_contract"),
    "contract_json_schema": ("cosmo_contracts.schema", "contract_json_schema"),
    # markdown rewriting
    "rewrite_benchmarks_markdown": ("cosmo_contracts.markdown", "rewrite_benchmarks_markdown"),
    "parse_contract_blocks": ("cosmo_contracts.markdown", "parse_contract_blocks"),
    # contract generation/helpers
    "default_contract": ("cosmo_contracts.contracts", "default_contract"),
    "normalize_contract": ("cosmo_contracts.contracts", "normalize_contract"),
    "render_contract_markdown": ("cosmo_contracts.contracts", "render_contract_markdown"),
    # compliance runner
    "run_compliance": ("cosmo_contracts.runner", "run_compliance"),
    "ComplianceReport": ("cosmo_contracts.runner", "ComplianceReport"),
}
def _lazy_import(module: str, name: str) -> Any:
    try:
        mod = import_module(module)
    except Exception as e:  # pragma: no cover
        raise ImportError(
            f"cosmo_contracts: failed to import '{module}' required for '{name}'. "
            f"Install/ship the corresponding module. Original error: {e}"
        ) from e
    try:
        return getattr(mod, name)
    except AttributeError as e:  # pragma: no cover
        raise ImportError(
            f"cosmo_contracts: module '{module}' does not export '{name}'."
        ) from e
def __getattr__(attr: str) -> Any:
    if attr in _EXPORTS:
        module, name = _EXPORTS[attr]
        value = _lazy_import(module, name)
        globals()[attr] = value  # cache
        return value
    raise AttributeError(attr)
def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_EXPORTS.keys())))
