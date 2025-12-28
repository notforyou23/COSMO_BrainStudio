from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover
    yaml = None
    _YAML_IMPORT_ERROR = e
else:
    _YAML_IMPORT_ERROR = None
@dataclass
class YamlParseError(ValueError):
    message: str
    path: Optional[Union[str, Path]] = None
    line: Optional[int] = None
    column: Optional[int] = None

    def __str__(self) -> str:
        loc = ""
        if self.path is not None:
            loc += str(self.path)
        if self.line is not None:
            loc += f":{self.line}"
            if self.column is not None:
                loc += f":{self.column}"
        if loc:
            return f"{loc}: {self.message}"
        return self.message
def _require_yaml() -> None:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for overrides YAML support but is not installed."
        ) from _YAML_IMPORT_ERROR
def _coerce_path(path: Optional[Union[str, Path]]) -> Optional[str]:
    if path is None:
        return None
    return str(path)
def format_yaml_error(exc: BaseException, *, path: Optional[Union[str, Path]] = None) -> YamlParseError:
    msg = str(exc).strip() or exc.__class__.__name__
    line = col = None
    mark = getattr(exc, "problem_mark", None)
    if mark is not None:
        line = getattr(mark, "line", None)
        col = getattr(mark, "column", None)
        if isinstance(line, int):
            line += 1
        if isinstance(col, int):
            col += 1
    return YamlParseError(message=msg, path=_coerce_path(path), line=line, column=col)
def safe_load_yaml(text: str, *, path: Optional[Union[str, Path]] = None) -> Any:
    _require_yaml()
    try:
        data = yaml.safe_load(text)  # type: ignore[attr-defined]
    except Exception as e:
        raise format_yaml_error(e, path=path) from e
    return data
def safe_dump_yaml(
    data: Any,
    *,
    sort_keys: bool = False,
    explicit_start: bool = False,
    width: int = 88,
) -> str:
    _require_yaml()
    try:
        return yaml.safe_dump(  # type: ignore[attr-defined]
            data,
            sort_keys=sort_keys,
            explicit_start=explicit_start,
            default_flow_style=False,
            allow_unicode=True,
            width=width,
        )
    except Exception as e:
        raise YamlParseError(message=str(e).strip() or e.__class__.__name__) from e
def load_yaml_file(path: Union[str, Path], *, encoding: str = "utf-8") -> Any:
    p = Path(path)
    text = p.read_text(encoding=encoding)
    return safe_load_yaml(text, path=p)
def dump_yaml_file(
    path: Union[str, Path],
    data: Any,
    *,
    encoding: str = "utf-8",
    sort_keys: bool = False,
    explicit_start: bool = False,
    width: int = 88,
) -> Path:
    p = Path(path)
    text = safe_dump_yaml(
        data, sort_keys=sort_keys, explicit_start=explicit_start, width=width
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding=encoding)
    return p
__all__ = [
    "YamlParseError",
    "format_yaml_error",
    "safe_load_yaml",
    "safe_dump_yaml",
    "load_yaml_file",
    "dump_yaml_file",
]
