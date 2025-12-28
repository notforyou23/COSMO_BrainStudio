from __future__ import annotations

from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Union, IO


try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    yaml = None  # type: ignore
    _YAML_IMPORT_ERROR = e
else:
    _YAML_IMPORT_ERROR = None


PathLike = Union[str, Path]


__all__ = [
    "PathLike",
    "ensure_yaml_available",
    "resolve_path",
    "read_text",
    "write_text",
    "safe_load_yaml",
    "safe_dump_yaml",
    "load_yaml_file",
    "dump_yaml_file",
]
def ensure_yaml_available() -> None:
    if yaml is None:  # pragma: no cover
        raise RuntimeError(
            "PyYAML is required for competitive_landscape YAML support but could not be imported."
        ) from _YAML_IMPORT_ERROR
def resolve_path(path: PathLike, *, base_dir: Optional[PathLike] = None) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        base = Path(base_dir).expanduser() if base_dir is not None else Path.cwd()
        p = base / p
    try:
        return p.resolve()
    except Exception:
        return p.absolute()
def read_text(path: PathLike, *, base_dir: Optional[PathLike] = None, encoding: str = "utf-8") -> str:
    p = resolve_path(path, base_dir=base_dir)
    return p.read_text(encoding=encoding)
def write_text(
    path: PathLike,
    text: str,
    *,
    base_dir: Optional[PathLike] = None,
    encoding: str = "utf-8",
    mkdir: bool = True,
) -> Path:
    p = resolve_path(path, base_dir=base_dir)
    if mkdir:
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding=encoding)
    return p
def safe_load_yaml(stream: Union[str, bytes, IO[str], IO[bytes]]) -> Any:
    ensure_yaml_available()
    if isinstance(stream, bytes):
        stream = stream.decode("utf-8")
    data = yaml.safe_load(stream)  # type: ignore[attr-defined]
    return {} if data is None else data
def _to_plain_data(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _to_plain_data(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain_data(v) for v in obj]
    return obj
def safe_dump_yaml(
    data: Any,
    *,
    sort_keys: bool = False,
    default_flow_style: bool = False,
    indent: int = 2,
) -> str:
    ensure_yaml_available()
    payload = _to_plain_data(data)
    return yaml.safe_dump(  # type: ignore[attr-defined]
        payload,
        sort_keys=sort_keys,
        default_flow_style=default_flow_style,
        indent=indent,
        allow_unicode=True,
    )
def load_yaml_file(
    path: PathLike,
    *,
    base_dir: Optional[PathLike] = None,
    encoding: str = "utf-8",
) -> Dict[str, Any]:
    p = resolve_path(path, base_dir=base_dir)
    text = p.read_text(encoding=encoding)
    data = safe_load_yaml(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at '{p}', got {type(data).__name__}")
    return data
def dump_yaml_file(
    path: PathLike,
    data: Any,
    *,
    base_dir: Optional[PathLike] = None,
    encoding: str = "utf-8",
    mkdir: bool = True,
    **dump_kwargs: Any,
) -> Path:
    text = safe_dump_yaml(data, **dump_kwargs)
    return write_text(path, text, base_dir=base_dir, encoding=encoding, mkdir=mkdir)
