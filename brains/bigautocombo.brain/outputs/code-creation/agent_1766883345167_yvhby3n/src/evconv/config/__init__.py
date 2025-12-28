"""evconv.config

Public, version-stable configuration API for IO, plotting, and workflow utilities.

This package intentionally re-exports the primary configuration types and helpers
so downstream code can rely on stable imports such as:

    from evconv.config import load_config, PlotConfig, WorkflowConfig
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, Optional
__all__ = [
    "__version__",
    "get_version",
    # Types
    "ConfigError",
    "PathLike",
    "IOConfig",
    "PlotConfig",
    "WorkflowConfig",
    # IO
    "load_config",
    "save_config",
    "merge_configs",
    "resolve_paths",
    # Plotting
    "apply_plot_config",
    "serialize_plot_config",
    # Workflow
    "assemble_workflow",
    "validate_workflow",
]
def get_version(package: str = "evconv") -> str:
    """Return installed package version, or '0+unknown' when unavailable."""
    try:
        from importlib.metadata import version as _version  # py>=3.8

        return _version(package)
    except Exception:
        return "0+unknown"
__version__ = get_version()
# Optional, stable re-exports with graceful degradation when submodules
# are absent during partial refactors or minimal installs.
def _missing(name: str, err: BaseException):
    def _fn(*_a: Any, **_kw: Any) -> Any:
        raise ImportError(
            f"evconv.config: '{name}' is unavailable because a submodule failed to import: {err}"
        ) from err

    return _fn
# Types
try:
    from .types import ConfigError, IOConfig, PathLike, PlotConfig, WorkflowConfig
except Exception as _e:
    class ConfigError(Exception):
        pass

    PathLike = Any  # type: ignore[assignment]
    IOConfig = Any  # type: ignore[assignment]
    PlotConfig = Any  # type: ignore[assignment]
    WorkflowConfig = Any  # type: ignore[assignment]
# IO
try:
    from .io import load_config, merge_configs, resolve_paths, save_config
except Exception as _e:
    load_config = _missing("load_config", _e)
    save_config = _missing("save_config", _e)
    merge_configs = _missing("merge_configs", _e)
    resolve_paths = _missing("resolve_paths", _e)
# Plotting
try:
    from .plotting import apply_plot_config, serialize_plot_config
except Exception as _e:
    apply_plot_config = _missing("apply_plot_config", _e)
    serialize_plot_config = _missing("serialize_plot_config", _e)
# Workflow
try:
    from .workflow import assemble_workflow, validate_workflow
except Exception as _e:
    assemble_workflow = _missing("assemble_workflow", _e)
    validate_workflow = _missing("validate_workflow", _e)
if TYPE_CHECKING:
    # Provide precise type-checking experience when modules are present.
    from .io import load_config as load_config
    from .io import merge_configs as merge_configs
    from .io import resolve_paths as resolve_paths
    from .io import save_config as save_config
    from .plotting import apply_plot_config as apply_plot_config
    from .plotting import serialize_plot_config as serialize_plot_config
    from .types import ConfigError as ConfigError
    from .types import IOConfig as IOConfig
    from .types import PathLike as PathLike
    from .types import PlotConfig as PlotConfig
    from .types import WorkflowConfig as WorkflowConfig
    from .workflow import assemble_workflow as assemble_workflow
    from .workflow import validate_workflow as validate_workflow
