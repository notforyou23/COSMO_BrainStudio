"""
customer_discovery package.

This package contains the refactored implementation for generating customer
discovery outputs and managing historical prompt artifacts.

Public API is re-exported here to provide a stable import surface:
    from customer_discovery import ...

Do not import internal helpers from submodules unless you are maintaining the
package internals.
"""

from __future__ import annotations
# Stable re-exports (intended public surface)

try:
    from .outputs import (
        CustomerDiscoveryOutputs,
        GenerateOutputsParams,
        generate_customer_discovery_outputs,
    )
except Exception as _exc:  # pragma: no cover
    _IMPORT_ERROR = _exc

    def __getattr__(name: str):
        raise ImportError(
            "customer_discovery public API could not be imported; "
            "ensure customer_discovery.outputs is available and importable."
        ) from _IMPORT_ERROR

    CustomerDiscoveryOutputs = None  # type: ignore[assignment]
    GenerateOutputsParams = None  # type: ignore[assignment]
    generate_customer_discovery_outputs = None  # type: ignore[assignment]
try:
    from .prompt_artifacts import (
        PromptArtifact,
        PromptArtifactStore,
        load_prompt_artifact,
        load_prompt_artifacts,
    )
except Exception:
    PromptArtifact = None  # type: ignore[assignment]
    PromptArtifactStore = None  # type: ignore[assignment]
    load_prompt_artifact = None  # type: ignore[assignment]
    load_prompt_artifacts = None  # type: ignore[assignment]
__all__ = [
    "CustomerDiscoveryOutputs",
    "GenerateOutputsParams",
    "generate_customer_discovery_outputs",
    "PromptArtifact",
    "PromptArtifactStore",
    "load_prompt_artifact",
    "load_prompt_artifacts",
]
