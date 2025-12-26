"""Top-level package for the reproducible JSON pipeline.

This module defines stable exports for downstream usage and unit tests.
"""

from __future__ import annotations
from .repro_json_pipeline import run_pipeline, PipelineResult

__all__ = ["run_pipeline", "PipelineResult"]
