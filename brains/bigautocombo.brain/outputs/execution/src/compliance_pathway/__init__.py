"""Compliance/certification pathway artifact generator.

Public API:
- generate_compliance_standards_map: end-to-end deterministic generator.
- render_compliance_standards_map: render data into markdown.
- build_v1_dataset: curated v1 standards/components/tests/checklist/strategy dataset.
- Models: selected dataclasses used across the package.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("generated_library_1766880625858")
except PackageNotFoundError:  # local editable/embedded execution
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    # primary API
    "generate_compliance_standards_map",
    "render_compliance_standards_map",
    "build_v1_dataset",
    # models (re-exported for convenience)
    "StandardRef",
    "ComponentRef",
    "TestRequirement",
    "DocChecklistItem",
    "DecisionNode",
]
# Primary API
from .generate import generate_compliance_standards_map
from .render import render_compliance_standards_map
from .data import build_v1_dataset
# Model re-exports for consumers
from .model import (
    ComponentRef,
    DecisionNode,
    DocChecklistItem,
    StandardRef,
    TestRequirement,
)
