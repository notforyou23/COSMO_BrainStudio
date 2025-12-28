"""Configuration I/O utilities (YAML/JSON), env overrides, and safe path resolution."""

from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any, Mapping, MutableMapping, Iterable, Optional, Union

__all__ = [
    "read_config",
    "write_config",
    "apply_env_overrides",
    "resolve_relative_paths",
    "safe_resolve_path",
]
def _load_yaml(text: str) -> Any:
    try:
        import yaml  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("PyYAML is required to load YAML configuration files") from e
    return yaml.safe_load(text)
def _dump_yaml(obj: Any) -> str:
    try:
        import yaml  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("PyYAML is required to write YAML configuration files") from e
    return yaml.safe_dump(obj, sort_keys=False)
def read_config(path: Union[str, Path]) -> dict:
    """Read JSON/YAML config file into a dict; returns {} for empty files."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    ext = p.suffix.lower()
    if ext in {".json"}:
        obj = json.loads(text)
    elif ext in {".yml", ".yaml"}:
        obj = _load_yaml(text)
    else:
        raise ValueError(f"Unsupported config extension: {p.suffix!r}")
    if obj is None:
        return {}
    if not isinstance(obj, dict):
        raise TypeError("Top-level configuration must be a mapping/dict")
    return obj
def write_config(path: Union[str, Path], data: Mapping[str, Any]) -> None:
    """Write config dict to JSON/YAML based on file extension."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ext = p.suffix.lower()
    if ext == ".json":
        text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    elif ext in {".yml", ".yaml"}:
        text = _dump_yaml(dict(data))
        if not text.endswith("\n"):
            text += "\n"
    else:
        raise ValueError(f"Unsupported config extension: {p.suffix!r}")
    p.write_text(text, encoding="utf-8")
def _parse_env_value(raw: str) -> Any:
    s = raw.strip()
    if s == "":
        return ""
    try:
        return json.loads(s)
    except Exception:
        return raw
def _set_deep(cfg: MutableMapping[str, Any], keys: Iterable[str], value: Any) -> None:
    keys = list(keys)
    cur: MutableMapping[str, Any] = cfg
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur.get(k), dict):
            cur[k] = {}
        cur = cur[k]  # type: ignore[assignment]
    cur[keys[-1]] = value
def apply_env_overrides(
    config: MutableMapping[str, Any],
    *,
    prefix: str = "EVCONV__",
    sep: str = "__",
    environ: Optional[Mapping[str, str]] = None,
) -> MutableMapping[str, Any]:
    """Apply env var overrides like EVCONV__section__key='value'.

    Values are parsed with json.loads when possible (e.g. numbers, booleans, lists, dicts).
    Keys are lowercased to match typical snake_case config keys.
    """
    env = dict(os.environ if environ is None else environ)
    for k, v in env.items():
        if not k.startswith(prefix):
            continue
        tail = k[len(prefix) :]
        if not tail:
            continue
        parts = [p.strip().lower() for p in tail.split(sep) if p.strip()]
        if not parts:
            continue
        _set_deep(config, parts, _parse_env_value(v))
    return config
def safe_resolve_path(
    path: Union[str, Path],
    *,
    base_dir: Union[str, Path],
    must_exist: bool = False,
    allow_outside_base: bool = False,
) -> Path:
    """Resolve a path relative to base_dir and prevent '..' escaping by default."""
    base = Path(base_dir).expanduser().resolve()
    p = Path(path).expanduser()
    resolved = (base / p).resolve() if not p.is_absolute() else p.resolve()
    if not allow_outside_base:
        try:
            resolved.relative_to(base)
        except Exception as e:
            raise ValueError(f"Resolved path escapes base_dir: {resolved}") from e
    if must_exist and not resolved.exists():
        raise FileNotFoundError(str(resolved))
    return resolved
def resolve_relative_paths(
    obj: Any,
    *,
    base_dir: Union[str, Path],
    path_keys: Iterable[str] = ("path", "paths", "file", "dir", "directory"),
    allow_outside_base: bool = False,
) -> Any:
    """Recursively resolve relative paths for keys ending with common suffixes.

    - Dict keys are matched when they end with one of path_keys (case-insensitive),
      or exactly equal to one of them.
    - Lists are traversed; strings under matched keys are resolved.
    """
    base = Path(base_dir)

    def is_path_key(k: str) -> bool:
        lk = k.lower()
        return lk in set(path_keys) or any(lk.endswith(f"_{s}") for s in path_keys)

    def walk(x: Any, *, under_path_key: bool = False) -> Any:
        if isinstance(x, dict):
            out = {}
            for k, v in x.items():
                out[k] = walk(v, under_path_key=under_path_key or is_path_key(str(k)))
            return out
        if isinstance(x, list):
            return [walk(i, under_path_key=under_path_key) for i in x]
        if under_path_key and isinstance(x, str) and x.strip():
            return str(safe_resolve_path(x, base_dir=base, allow_outside_base=allow_outside_base))
        return x

    return walk(obj)
