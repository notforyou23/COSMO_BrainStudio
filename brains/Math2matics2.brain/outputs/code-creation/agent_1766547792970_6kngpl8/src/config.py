"""Central configuration for the project.

This module must never default to an absolute `/outputs` path. All output locations
are derived from a single portable OUTPUT_DIR utility (env override supported).
"""

from __future__ import annotations

from pathlib import Path
import os

# Prefer the shared output path utility; fall back to a safe relative default.
try:
    # When `src` is a package (most common).
    from .utils.output_paths import OUTPUT_DIR as OUTPUT_DIR  # type: ignore
except Exception:
    try:
        # When executed with `src` on sys.path.
        from src.utils.output_paths import OUTPUT_DIR as OUTPUT_DIR  # type: ignore
    except Exception:
        OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs")).expanduser().resolve()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Common subdirectories used across the project.
ARTIFACTS_DIR = OUTPUT_DIR / "artifacts"
LOGS_DIR = OUTPUT_DIR / "logs"
CACHE_DIR = OUTPUT_DIR / "cache"
TMP_DIR = OUTPUT_DIR / "tmp"

for _d in (ARTIFACTS_DIR, LOGS_DIR, CACHE_DIR, TMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def ensure_output_dir(subdir: str | Path | None = None) -> Path:
    """Return an output directory (optionally a subdir) and ensure it exists."""
    base = OUTPUT_DIR if subdir in (None, "", ".") else (OUTPUT_DIR / Path(subdir))
    base.mkdir(parents=True, exist_ok=True)
    return base


def output_path(*parts: str | Path, subdir: str | Path | None = None) -> Path:
    """Build an output path under OUTPUT_DIR (and ensure parent directory exists)."""
    base = ensure_output_dir(subdir=subdir)
    p = base.joinpath(*[Path(x) for x in parts]) if parts else base
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
