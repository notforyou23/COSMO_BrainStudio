"""
Canonicalization library for consolidating scattered runtime/agent artifacts into a single
canonical outputs/ tree with a refreshed ARTIFACT_INDEX.md.

This package is intended to be used by scripts/canonicalize_outputs.py and exposes
stable, convenience imports for discovery, selection, and migration utilities.
"""
from __future__ import annotations

__all__ = [
    "discover_candidates",
    "score_and_select_authoritative",
    "migrate_to_canonical_outputs",
]

__version__ = "0.1.0"
# Convenience re-exports (modules are expected to exist alongside this package).
from .discovery import discover_candidates
from .selection import score_and_select_authoritative
from .migrate import migrate_to_canonical_outputs
