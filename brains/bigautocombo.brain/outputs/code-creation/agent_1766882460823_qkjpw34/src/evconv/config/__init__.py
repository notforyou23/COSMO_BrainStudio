"""Public configuration package API for the evconv workflow.

This module provides lightweight, dependency-minimal helpers to build a final
configuration bundle from defaults, files, and in-memory overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence, Union
import json
__all__ = [
    "ConfigError",
    "default_config",
    "default_plotting_config",
    "default_paths_config",
    "deep_merge",
    "load_config",
    "merge_config",
    "validate_config",
    "finalize_config",
]
class ConfigError(ValueError):
    """Raised when configuration loading or validation fails."""
def _as_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        return dict(obj.dict())  # pydantic-like
    if isinstance(obj, Mapping):
        return dict(obj)
    raise ConfigError(f"Expected a mapping/dict config, got {type(obj).__name__}")
def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict:
    """Recursively merge two mappings (override wins) without mutating inputs."""
    out: dict = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], Mapping) and isinstance(v, Mapping):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out
def merge_config(*configs: Any) -> dict:
    """Merge multiple config mappings left-to-right (later wins)."""
    merged: dict = {}
    for cfg in configs:
        merged = deep_merge(merged, _as_dict(cfg))
    return merged
def default_paths_config() -> dict:
    return {
        "input_dir": ".",
        "output_dir": "./outputs",
        "cache_dir": "./.cache",
    }
def default_plotting_config() -> dict:
    return {
        "style": "default",
        "dpi": 150,
        "figure_size": [8.0, 5.0],
        "save": True,
        "show": False,
        "format": "png",
    }
def default_config() -> dict:
    """Factory for the workflow default configuration."""
    return {
        "paths": default_paths_config(),
        "run": {"seed": 0, "log_level": "INFO"},
        "io": {"read_format": "auto", "write_format": "json"},
        "plotting": default_plotting_config(),
        "workflow": {"steps": ["load", "compute", "export"]},
    }
def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")
def load_config(path: Union[str, Path], *, allow_missing: bool = False) -> dict:
    """Load a configuration file (JSON or YAML if available) into a dict."""
    p = Path(path)
    if not p.is_absolute():
        p = Path.cwd() / p
    if not p.exists():
        if allow_missing:
            return {}
        raise ConfigError(f"Config file not found: {p}")
    text = _read_text(p)
    suffix = p.suffix.lower()
    if suffix in {".json"}:
        data = json.loads(text or "{}")
    elif suffix in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:  # pragma: no cover
            raise ConfigError("YAML requested but PyYAML is not installed") from e
        data = yaml.safe_load(text) or {}
    else:
        # Auto-detect: try JSON then YAML.
        try:
            data = json.loads(text or "{}")
        except Exception:
            try:
                import yaml  # type: ignore
            except Exception as e:  # pragma: no cover
                raise ConfigError(f"Unsupported config extension: {p.suffix}") from e
            data = yaml.safe_load(text) or {}
    return _as_dict(data)
def validate_config(cfg: Any) -> dict:
    """Validate and normalize a configuration dict; returns normalized config."""
    d = _as_dict(cfg)
    for top in ("paths", "run", "io", "plotting", "workflow"):
        if top not in d:
            raise ConfigError(f"Missing required top-level section: '{top}'")
        if not isinstance(d[top], Mapping):
            raise ConfigError(f"Section '{top}' must be a mapping")
    paths = d["paths"]
    for k in ("input_dir", "output_dir"):
        if k not in paths or not isinstance(paths[k], (str, Path)):
            raise ConfigError(f"paths.{k} must be a string or Path")
    plotting = d["plotting"]
    if "dpi" in plotting and not isinstance(plotting["dpi"], (int, float)):
        raise ConfigError("plotting.dpi must be numeric")
    if "figure_size" in plotting:
        fs = plotting["figure_size"]
        if not (isinstance(fs, Sequence) and len(fs) == 2 and all(isinstance(x, (int, float)) for x in fs)):
            raise ConfigError("plotting.figure_size must be a 2-item numeric sequence")
    wf = d["workflow"]
    if "steps" in wf and not (isinstance(wf["steps"], Sequence) and all(isinstance(s, str) for s in wf["steps"])):
        raise ConfigError("workflow.steps must be a sequence of strings")
    return d
def finalize_config(
    *,
    base: Optional[Any] = None,
    config_paths: Optional[Sequence[Union[str, Path]]] = None,
    user_config: Optional[Any] = None,
    overrides: Optional[Any] = None,
    allow_missing_files: bool = False,
) -> dict:
    """Compose defaults, optional base, files, user_config, and overrides."""
    cfg = merge_config(default_config(), base)
    if config_paths:
        for p in config_paths:
            cfg = deep_merge(cfg, load_config(p, allow_missing=allow_missing_files))
    cfg = merge_config(cfg, user_config, overrides)
    return validate_config(cfg)
