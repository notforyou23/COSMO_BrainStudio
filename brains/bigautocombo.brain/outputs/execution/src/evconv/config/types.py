from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union
class ConfigError(ValueError):
    """Raised when configuration validation fails."""
class StrEnum(str, Enum):
    @classmethod
    def coerce(cls, v: Any) -> "StrEnum":
        if isinstance(v, cls):
            return v
        if isinstance(v, str):
            try:
                return cls(v)
            except Exception as e:
                raise ConfigError(f"Invalid {cls.__name__}: {v!r}") from e
        raise ConfigError(f"Expected {cls.__name__} or str, got {type(v).__name__}")
class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL" 
class IOFormat(StrEnum):
    JSON = "json"
    YAML = "yaml" 
class PlotTheme(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SCIENTIFIC = "scientific" 
def _as_path(v: Any) -> Path:
    if isinstance(v, Path):
        return v.expanduser()
    if isinstance(v, str):
        return Path(v).expanduser()
    raise ConfigError(f"Expected path-like (str/Path), got {type(v).__name__}")

def _pos_int(name: str, v: Any) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise ConfigError(f"{name} must be a positive int, got {v!r}")
    return v

def _pos_float(name: str, v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or float(v) <= 0:
        raise ConfigError(f"{name} must be a positive number, got {v!r}")
    return float(v)

def _dict(name: str, v: Any) -> Dict[str, Any]:
    if v is None:
        return {}
    if isinstance(v, Mapping):
        return dict(v)
    raise ConfigError(f"{name} must be a mapping, got {type(v).__name__}")
@dataclass(frozen=True)
class PathsConfig:
    root: Path = Path(".")
    data_dir: Path = Path("data")
    output_dir: Path = Path("outputs")
    cache_dir: Path = Path(".cache")

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", _as_path(self.root))
        object.__setattr__(self, "data_dir", _as_path(self.data_dir))
        object.__setattr__(self, "output_dir", _as_path(self.output_dir))
        object.__setattr__(self, "cache_dir", _as_path(self.cache_dir))

    def resolve_under_root(self) -> "PathsConfig":
        r = self.root.resolve()
        return PathsConfig(
            root=r,
            data_dir=(r / self.data_dir).resolve(),
            output_dir=(r / self.output_dir).resolve(),
            cache_dir=(r / self.cache_dir).resolve(),
        )
@dataclass(frozen=True)
class IOConfig:
    format: IOFormat = IOFormat.YAML
    encoding: str = "utf-8"
    allow_env: bool = True
    strict: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "format", IOFormat.coerce(self.format))
        if not isinstance(self.encoding, str) or not self.encoding:
            raise ConfigError("encoding must be a non-empty string")
        if not isinstance(self.allow_env, bool) or not isinstance(self.strict, bool):
            raise ConfigError("allow_env/strict must be bool")
@dataclass(frozen=True)
class PlottingConfig:
    theme: PlotTheme = PlotTheme.SCIENTIFIC
    dpi: int = 150
    figsize: Sequence[float] = (6.4, 4.8)
    colormap: str = "viridis"
    rcparams: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "theme", PlotTheme.coerce(self.theme))
        object.__setattr__(self, "dpi", _pos_int("dpi", self.dpi))
        if (not isinstance(self.figsize, Sequence)) or len(self.figsize) != 2:
            raise ConfigError("figsize must be a 2-sequence (width, height)")
        w, h = self.figsize[0], self.figsize[1]
        object.__setattr__(self, "figsize", (float(_pos_float("figsize[0]", w)), float(_pos_float("figsize[1]", h))))
        if not isinstance(self.colormap, str) or not self.colormap:
            raise ConfigError("colormap must be a non-empty string")
        object.__setattr__(self, "rcparams", _dict("rcparams", self.rcparams))
@dataclass(frozen=True)
class StageConfig:
    name: str
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConfigError("stage.name must be a non-empty string")
        if not isinstance(self.enabled, bool):
            raise ConfigError("stage.enabled must be bool")
        object.__setattr__(self, "params", _dict("stage.params", self.params))
@dataclass(frozen=True)
class WorkflowConfig:
    name: str = "default"
    seed: Optional[int] = None
    log_level: LogLevel = LogLevel.INFO
    paths: PathsConfig = field(default_factory=PathsConfig)
    io: IOConfig = field(default_factory=IOConfig)
    plotting: PlottingConfig = field(default_factory=PlottingConfig)
    stages: List[StageConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConfigError("workflow.name must be a non-empty string")
        object.__setattr__(self, "log_level", LogLevel.coerce(self.log_level))
        if self.seed is not None:
            if isinstance(self.seed, bool) or not isinstance(self.seed, int):
                raise ConfigError("workflow.seed must be int or None")
        if not isinstance(self.paths, PathsConfig) or not isinstance(self.io, IOConfig) or not isinstance(self.plotting, PlottingConfig):
            raise ConfigError("paths/io/plotting must be their respective config types")
        if not isinstance(self.stages, list) or any(not isinstance(s, StageConfig) for s in self.stages):
            raise ConfigError("stages must be a list[StageConfig]")

    def stage_map(self) -> Dict[str, StageConfig]:
        d: Dict[str, StageConfig] = {}
        for s in self.stages:
            if s.name in d:
                raise ConfigError(f"Duplicate stage name: {s.name}")
            d[s.name] = s
        return d
def as_jsonable(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dataclass_fields__"):
        return {k: as_jsonable(getattr(obj, k)) for k in obj.__dataclass_fields__}
    if isinstance(obj, dict):
        return {str(k): as_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [as_jsonable(v) for v in obj]
    return obj

def dumps_config(obj: Any, *, indent: int = 2, sort_keys: bool = True) -> str:
    return json.dumps(as_jsonable(obj), indent=indent, sort_keys=sort_keys)
