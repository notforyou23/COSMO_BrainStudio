"""Minimal meta-analysis starter kit.

This package provides:
- io: CSV template/schema utilities and robust loaders/validators
- meta: core meta-analysis computations (fixed/random effects)
- report: writing reproducible numeric outputs into runtime/outputs/_build/

The runnable analysis skeleton imports from this package.
"""
from __future__ import annotations

from pathlib import Path
import logging

try:
    from importlib.metadata import version as _pkg_version  # py>=3.8
except Exception:  # pragma: no cover
    _pkg_version = None  # type: ignore
__all__ = [
    "__version__",
    "package_root",
    "get_template_path",
    "load_effects_csv",
    "write_effects_template",
    "fixed_effect",
    "random_effects_dl",
    "write_summary_tables",
]

__version__ = "0.1.0"
if _pkg_version is not None:
    try:
        __version__ = _pkg_version("meta_starter")
    except Exception:
        pass

_logger = logging.getLogger(__name__)
_logger.addHandler(logging.NullHandler())

package_root = Path(__file__).resolve().parent
def get_template_path(name: str) -> Path:
    """Return an absolute path to a shipped template file (if present)."""
    return package_root / "templates" / name
# Convenience re-exports (import lazily to avoid hard import-time coupling).
try:
    from .io import load_effects_csv, write_effects_template  # noqa: F401
except Exception:  # pragma: no cover
    def load_effects_csv(*args, **kwargs):  # type: ignore
        raise ImportError("meta_starter.io is unavailable; cannot load_effects_csv")

    def write_effects_template(*args, **kwargs):  # type: ignore
        raise ImportError("meta_starter.io is unavailable; cannot write_effects_template")

try:
    from .meta import fixed_effect, random_effects_dl  # noqa: F401
except Exception:  # pragma: no cover
    def fixed_effect(*args, **kwargs):  # type: ignore
        raise ImportError("meta_starter.meta is unavailable; cannot fixed_effect")

    def random_effects_dl(*args, **kwargs):  # type: ignore
        raise ImportError("meta_starter.meta is unavailable; cannot random_effects_dl")

try:
    from .report import write_summary_tables  # noqa: F401
except Exception:  # pragma: no cover
    def write_summary_tables(*args, **kwargs):  # type: ignore
        raise ImportError("meta_starter.report is unavailable; cannot write_summary_tables")
