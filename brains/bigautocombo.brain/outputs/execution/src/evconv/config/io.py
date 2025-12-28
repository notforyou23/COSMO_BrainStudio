"""Configuration IO utilities (YAML/JSON), deep-merge, basic validation hooks, and path resolution."""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping, Optional, Union
import json
import os

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

JSONLike = Union[dict, list, str, int, float, bool, None]
Validator = Callable[[dict], None]
def _to_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"Config must be a dict or dataclass, got {type(obj).__name__}")
def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict:
    """Recursively merge override into base. Dicts merge; other types replace."""
    out = dict(base)
    for k, v in (override or {}).items():
        if k in out and isinstance(out[k], Mapping) and isinstance(v, Mapping):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out
def validate_config(cfg: dict, validator: Optional[Validator] = None) -> dict:
    """Optional validation hook; raise ValueError/TypeError inside validator to fail."""
    if not isinstance(cfg, dict):
        raise TypeError(f"Configuration root must be a dict, got {type(cfg).__name__}")
    if validator is not None:
        validator(cfg)
    return cfg
def validate_spec(cfg: dict, spec: Mapping[str, Any], *, allow_extra: bool = True) -> dict:
    """Lightweight schema-like validation for nested dicts.
    spec values may be: type, tuple(types), nested spec dict, or callable(value)->bool.
    """
    def _check(path: str, value: Any, rule: Any) -> None:
        if isinstance(rule, Mapping):
            if not isinstance(value, Mapping):
                raise TypeError(f"{path} must be a mapping")
            for kk, rr in rule.items():
                if kk not in value:
                    raise KeyError(f"Missing required key: {path}.{kk}" if path else f"Missing required key: {kk}")
                _check(f"{path}.{kk}" if path else kk, value[kk], rr)
            if not allow_extra:
                extra = set(value.keys()) - set(rule.keys())
                if extra:
                    raise KeyError(f"Unexpected keys at {path or '<root>'}: {sorted(extra)}")
        elif isinstance(rule, type) or (isinstance(rule, tuple) and all(isinstance(t, type) for t in rule)):
            if value is not None and not isinstance(value, rule):
                raise TypeError(f"{path} must be {rule}, got {type(value).__name__}")
        elif callable(rule):
            ok = bool(rule(value))
            if not ok:
                raise ValueError(f"{path} failed validation")
        else:
            raise TypeError(f"Invalid spec rule at {path}: {rule!r}")

    _check("", cfg, spec)
    return cfg
def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
def load(path: Union[str, Path], *, validator: Optional[Validator] = None, base_dir: Optional[Union[str, Path]] = None) -> dict:
    """Load YAML/JSON config from path, optionally validating and resolving paths."""
    p = Path(path)
    data: Any
    ext = p.suffix.lower()
    raw = _read_text(p)
    if ext in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML files")
        data = yaml.safe_load(raw) or {}
    elif ext == ".json":
        data = json.loads(raw) if raw.strip() else {}
    else:
        raise ValueError(f"Unsupported config extension: {ext}")
    cfg = _to_dict(data)
    cfg = resolve_paths(cfg, base_dir=base_dir or p.parent)
    return validate_config(cfg, validator=validator)
def save(cfg: Any, path: Union[str, Path], *, sort_keys: bool = True) -> Path:
    """Save config dict/dataclass to YAML/JSON based on file extension."""
    p = Path(path)
    obj = _to_dict(cfg)
    ext = p.suffix.lower()
    if ext in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to save YAML files")
        text = yaml.safe_dump(obj, sort_keys=sort_keys, default_flow_style=False)
    elif ext == ".json":
        text = json.dumps(obj, indent=2, sort_keys=sort_keys, ensure_ascii=False) + "\n"
    else:
        raise ValueError(f"Unsupported config extension: {ext}")
    _write_text(p, text)
    return p
def load_merged(*paths: Union[str, Path], validator: Optional[Validator] = None, base_dir: Optional[Union[str, Path]] = None) -> dict:
    """Load and deep-merge multiple config files left-to-right (later overrides earlier)."""
    cfg: dict = {}
    for p in paths:
        part = load(p, validator=None, base_dir=base_dir)
        cfg = deep_merge(cfg, part)
    cfg = resolve_paths(cfg, base_dir=base_dir)
    return validate_config(cfg, validator=validator)
def resolve_paths(obj: Any, *, base_dir: Optional[Union[str, Path]] = None, key_pred: Optional[Callable[[str], bool]] = None) -> Any:
    """Resolve path-like string values inside nested structures.

    - Expands env vars and ~
    - If relative, resolves against base_dir (defaults to CWD)
    - By default, resolves keys ending with: path/paths/dir/file/files
    """
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    if key_pred is None:
        def key_pred(k: str) -> bool:
            lk = k.lower()
            return lk.endswith(("path", "paths", "dir", "file", "files"))

    def _res(v: Any, k: Optional[str] = None) -> Any:
        if isinstance(v, Mapping):
            return {kk: _res(vv, kk) for kk, vv in v.items()}
        if isinstance(v, list):
            return [_res(x, k) for x in v]
        if isinstance(v, str) and (k is None or key_pred(k)):
            s = os.path.expandvars(os.path.expanduser(v))
            if not s:
                return v
            ps = Path(s)
            if not ps.is_absolute():
                ps = (base / ps).resolve()
            return str(ps)
        return v

    return _res(obj)
