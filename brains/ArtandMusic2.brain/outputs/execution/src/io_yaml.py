from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

try:
    import yaml
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "PyYAML is required to load/save configuration YAML files (pip install pyyaml)."
    ) from e


PathLike = Union[str, Path]


@dataclass
class YamlIOError(Exception):
    message: str
    path: Optional[Path] = None
    schema_hint: Optional[str] = None

    def __str__(self) -> str:
        parts = [self.message]
        if self.path is not None:
            parts.append(f"path={self.path}")
        if self.schema_hint:
            parts.append(f"schema_hint={self.schema_hint}")
        return " | ".join(parts)


def canonicalize_path(path: PathLike, base_dir: Optional[PathLike] = None) -> Path:
    p = Path(path)
    if not p.is_absolute():
        base = Path(base_dir) if base_dir is not None else Path.cwd()
        p = base / p
    try:
        return p.expanduser().resolve()
    except Exception:
        return p.expanduser().absolute()
def _yaml_mark_to_location(err: Exception) -> str:
    mark = getattr(err, "problem_mark", None) or getattr(err, "context_mark", None)
    if not mark:
        return ""
    line = getattr(mark, "line", None)
    col = getattr(mark, "column", None)
    if line is None or col is None:
        return ""
    return f"line {int(line) + 1}, column {int(col) + 1}"


def load_yaml(
    path: PathLike,
    *,
    base_dir: Optional[PathLike] = None,
    required: bool = True,
    schema_hint: Optional[str] = None,
) -> Any:
    p = canonicalize_path(path, base_dir=base_dir)
    if required and not p.exists():
        raise YamlIOError("YAML file does not exist", path=p, schema_hint=schema_hint)
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        raise YamlIOError("Failed reading YAML file", path=p, schema_hint=schema_hint) from e

    try:
        data = yaml.safe_load(text)
    except Exception as e:
        loc = _yaml_mark_to_location(e)
        msg = "Invalid YAML syntax"
        if loc:
            msg += f" ({loc})"
        detail = getattr(e, "problem", None) or getattr(e, "context", None) or str(e)
        raise YamlIOError(f"{msg}: {detail}", path=p, schema_hint=schema_hint) from e

    return data
def save_yaml(
    data: Any,
    path: PathLike,
    *,
    base_dir: Optional[PathLike] = None,
    sort_keys: bool = False,
) -> Path:
    p = canonicalize_path(path, base_dir=base_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        dumped = yaml.safe_dump(
            data,
            sort_keys=sort_keys,
            default_flow_style=False,
            allow_unicode=True,
            width=100,
        )
    except Exception as e:
        raise YamlIOError("Failed serializing data to YAML", path=p) from e

    if dumped is None:
        dumped = "null\n"
    elif not dumped.endswith("\n"):
        dumped += "\n"

    try:
        p.write_text(dumped, encoding="utf-8")
    except Exception as e:
        raise YamlIOError("Failed writing YAML file", path=p) from e
    return p
def require_mapping(
    data: Any,
    *,
    path: Optional[PathLike] = None,
    schema_hint: Optional[str] = None,
) -> dict:
    if isinstance(data, dict):
        return data
    p = canonicalize_path(path) if path is not None else None
    raise YamlIOError(
        f"Top-level YAML must be a mapping (dict); got {type(data).__name__}",
        path=p,
        schema_hint=schema_hint,
    )


def load_yaml_mapping(
    path: PathLike,
    *,
    base_dir: Optional[PathLike] = None,
    required: bool = True,
    schema_hint: Optional[str] = None,
) -> dict:
    data = load_yaml(path, base_dir=base_dir, required=required, schema_hint=schema_hint)
    if data is None:
        return {}
    return require_mapping(data, path=canonicalize_path(path, base_dir=base_dir), schema_hint=schema_hint)
