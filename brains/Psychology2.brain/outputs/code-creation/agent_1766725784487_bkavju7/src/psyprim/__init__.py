"""psyprim: standardized primary-source workflows + lightweight tooling.

This package initializer exposes:
- __version__ (PEP 440)
- high-level public interfaces used by the CLI via stable re-exports / lazy imports
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

__all__ = [
    "__version__",
    "get_version",
    # Protocol / schema / checklists
    "Protocol",
    "Checklist",
    "ChecklistItem",
    "MetadataSchema",
    "ProtocolRegistry",
    "get_default_protocol",
    "validate_metadata",
    # Provenance / variants / citations
    "ProvenanceFlag",
    "VariantRef",
    "variant_number",
    "parse_repository_citation",
    "link_repository_citation",
]

def get_version(package: str = "psyprim") -> str:
    """Return installed distribution version; falls back to '0.0.0' when unavailable."""
    try:
        from importlib.metadata import version as _v  # py3.8+
    except Exception:  # pragma: no cover
        return "0.0.0"
    try:
        return _v(package)
    except Exception:
        return "0.0.0"

__version__ = get_version()

# Map attribute name -> (module, attribute)
_LAZY: Dict[str, Tuple[str, str]] = {
    # Protocol / schema / checklists
    "Protocol": ("psyprim.protocol", "Protocol"),
    "Checklist": ("psyprim.protocol", "Checklist"),
    "ChecklistItem": ("psyprim.protocol", "ChecklistItem"),
    "MetadataSchema": ("psyprim.protocol", "MetadataSchema"),
    "ProtocolRegistry": ("psyprim.protocol", "ProtocolRegistry"),
    "get_default_protocol": ("psyprim.protocol", "get_default_protocol"),
    "validate_metadata": ("psyprim.protocol", "validate_metadata"),
    # Provenance / variants / citations
    "ProvenanceFlag": ("psyprim.protocol", "ProvenanceFlag"),
    "VariantRef": ("psyprim.protocol", "VariantRef"),
    "variant_number": ("psyprim.protocol", "variant_number"),
    "parse_repository_citation": ("psyprim.protocol", "parse_repository_citation"),
    "link_repository_citation": ("psyprim.protocol", "link_repository_citation"),
}

def __getattr__(name: str) -> Any:
    """Lazy attribute resolution for CLI-facing APIs.

    This keeps import-time side effects small while allowing stable re-exports.
    """
    spec = _LAZY.get(name)
    if spec is None:
        raise AttributeError(f"module 'psyprim' has no attribute {name!r}")
    mod_name, attr_name = spec
    mod = import_module(mod_name)
    try:
        val = getattr(mod, attr_name)
    except AttributeError as e:  # pragma: no cover
        raise AttributeError(
            f"Requested attribute {name!r} maps to missing {mod_name}.{attr_name}"
        ) from e
    globals()[name] = val
    return val

def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY.keys())))
