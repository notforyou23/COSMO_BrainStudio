"""qg_bench: minimal, deterministic benchmarking utilities.

The project provides a small CLI that ingests a JSONL dataset, computes a couple
of simple observables, and writes standardized results with a deterministic
hash/metadata block.
"""

from __future__ import annotations

__all__ = ["__version__", "__description__"]

#: Public package version (kept here so tools can read it without imports).
__version__ = "0.1.0"

#: Short description used by CLI help text and metadata.
__description__ = "Minimal deterministic benchmarking CLI + result schema."
