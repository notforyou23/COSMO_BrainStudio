"""
Writers package initializer.

This module centralizes shared output directory behavior for all writer modules by
re-exporting the project's single output-path utility surface.
"""

from __future__ import annotations

from pathlib import Path

try:
    # Canonical, portable output directory utilities (single source of truth).
    from ..utils.output_paths import (  # type: ignore
        OUTPUT_DIR,
        ensure_dir,
        ensure_output_dir,
        output_path,
        output_subdir,
    )
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Failed to import shared output path utilities. Ensure "
        "'src/utils/output_paths.py' exists and is importable."
    ) from e

__all__ = [
    "Path",
    "OUTPUT_DIR",
    "ensure_dir",
    "ensure_output_dir",
    "output_path",
    "output_subdir",
]
