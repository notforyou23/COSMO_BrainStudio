from __future__ import annotations

"""
verifier_policy package.

This initializer exposes primary public entry points via lazy imports and provides
a robust __version__ derived from installed package metadata (or a safe fallback).
"""

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version as _pkg_version

__all__ = [
    "__version__",
    "get_version",
    "VerifierPolicyError",
    "AuditEvent",
    "Claim",
    "Passage",
    "Quote",
    "Decision",
    "VerifierOutput",
    "retrieve",
    "verify",
    "retrieve_then_verify",
    "calibrate_thresholds",
    "evaluate_heldout",
]

try:
    __version__ = _pkg_version("verifier_policy")
except PackageNotFoundError:
    __version__ = "0.0.0"


def get_version() -> str:
    return __version__


class VerifierPolicyError(RuntimeError):
    """Raised when verifier-policy execution cannot proceed due to misconfiguration or missing components."""
_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    # Schemas / models
    "AuditEvent": ("verifier_policy.schemas", "AuditEvent"),
    "Claim": ("verifier_policy.schemas", "Claim"),
    "Passage": ("verifier_policy.schemas", "Passage"),
    "Quote": ("verifier_policy.schemas", "Quote"),
    "Decision": ("verifier_policy.schemas", "Decision"),
    "VerifierOutput": ("verifier_policy.schemas", "VerifierOutput"),
    # Retrieval
    "retrieve": ("verifier_policy.retrieval", "retrieve"),
    # Primary pipeline entry points
    "verify": ("verifier_policy.pipeline", "verify"),
    "retrieve_then_verify": ("verifier_policy.pipeline", "retrieve_then_verify"),
    # Calibration / evaluation
    "calibrate_thresholds": ("verifier_policy.evaluation", "calibrate_thresholds"),
    "evaluate_heldout": ("verifier_policy.evaluation", "evaluate_heldout"),
}


def __getattr__(name: str):
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod_name, attr_name = target
    try:
        mod = import_module(mod_name)
    except Exception as e:  # noqa: BLE001
        raise VerifierPolicyError(
            f"Failed to import {mod_name!r} needed for attribute {name!r}: {e}"
        ) from e
    try:
        value = getattr(mod, attr_name)
    except Exception as e:  # noqa: BLE001
        raise VerifierPolicyError(
            f"Attribute {attr_name!r} not found in {mod_name!r} for public symbol {name!r}: {e}"
        ) from e
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY_ATTRS.keys())))
