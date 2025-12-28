from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

__all__ = [
    "YamlLoadError",
    "YamlDumpError",
    "load_yaml",
    "loads_yaml",
    "dump_yaml",
    "dumps_yaml",
]


PathLike = Union[str, Path]


@dataclass
class YamlLoadError(RuntimeError):
    message: str
    path: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    original: Optional[BaseException] = None

    def __str__(self) -> str:
        loc = []
        if self.path:
            loc.append(self.path)
        if self.line is not None:
            loc.append(f"line {self.line}")
        if self.column is not None:
            loc.append(f"col {self.column}")
        suffix = f" ({', '.join(loc)})" if loc else ""
        return f"{self.message}{suffix}"


@dataclass
class YamlDumpError(RuntimeError):
    message: str
    path: Optional[str] = None
    original: Optional[BaseException] = None

    def __str__(self) -> str:
        suffix = f" ({self.path})" if self.path else ""
        return f"{self.message}{suffix}"
def _pick_yaml_backend():
    try:
        from ruamel.yaml import YAML  # type: ignore
        from ruamel.yaml.error import YAMLError  # type: ignore

        yaml = YAML(typ="rt")
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096
        yaml.allow_duplicate_keys = False
        return "ruamel", yaml, YAMLError
    except Exception:
        try:
            import yaml as pyyaml  # type: ignore

            return "pyyaml", pyyaml, Exception
        except Exception as e:
            raise RuntimeError("No YAML backend available (ruamel.yaml or PyYAML).") from e


_BACKEND, _YAML, _YAML_ERROR = _pick_yaml_backend()


def _extract_mark(err: BaseException):
    for attr in ("problem_mark", "context_mark", "mark"):
        m = getattr(err, attr, None)
        if m is not None:
            line = getattr(m, "line", None)
            col = getattr(m, "column", None)
            if line is not None:
                line = int(line) + 1
            if col is not None:
                col = int(col) + 1
            return line, col
    return None, None
def loads_yaml(text: str, *, path: Optional[PathLike] = None) -> Any:
    p = str(path) if path is not None else None
    try:
        if _BACKEND == "ruamel":
            import io

            return _YAML.load(io.StringIO(text))
        return _YAML.safe_load(text)
    except Exception as e:
        line, col = _extract_mark(e)
        msg = "Failed to parse YAML"
        raise YamlLoadError(msg, path=p, line=line, column=col, original=e) from e


def load_yaml(path: PathLike) -> Any:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except Exception as e:
        raise YamlLoadError("Failed to read YAML file", path=str(p), original=e) from e
    return loads_yaml(text, path=p)


def dumps_yaml(data: Any) -> str:
    try:
        if _BACKEND == "ruamel":
            import io

            buf = io.StringIO()
            _YAML.dump(data, buf)
            return buf.getvalue()
        return _YAML.safe_dump(data, sort_keys=False, allow_unicode=True)
    except Exception as e:
        raise YamlDumpError("Failed to dump YAML", original=e) from e


def dump_yaml(data: Any, path: PathLike) -> None:
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(dumps_yaml(data), encoding="utf-8")
    except YamlDumpError:
        raise
    except Exception as e:
        raise YamlDumpError("Failed to write YAML file", path=str(p), original=e) from e
