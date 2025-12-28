from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping, Optional, Sequence, Union
import json
import os
import hashlib
JSONLike = Union[dict, list, str, int, float, bool, None]
ConfigDict = dict[str, Any]
Validator = Callable[[ConfigDict], None]
def _deep_merge(base: Any, upd: Any) -> Any:
    """Recursively merge upd into base; dicts merge, other types replace."""
    if base is None:
        return upd
    if upd is None:
        return base
    if isinstance(base, dict) and isinstance(upd, dict):
        out = dict(base)
        for k, v in upd.items():
            out[k] = _deep_merge(out.get(k), v)
        return out
    return upd
def _parse_scalar(s: str) -> Any:
    t = s.strip()
    if t.lower() in {"true", "false"}:
        return t.lower() == "true"
    if t.lower() in {"null", "none"}:
        return None
    try:
        if "." in t or "e" in t.lower():
            return float(t)
        return int(t)
    except Exception:
        pass
    if (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]")):
        try:
            return json.loads(t)
        except Exception:
            return t
    return t
def _set_dotted(d: MutableMapping[str, Any], dotted: str, value: Any) -> None:
    parts = [p for p in dotted.split(".") if p]
    if not parts:
        return
    cur: MutableMapping[str, Any] = d
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value
def _overrides_to_dict(overrides: Any) -> ConfigDict:
    if overrides is None:
        return {}
    if isinstance(overrides, dict):
        return dict(overrides)
    if isinstance(overrides, (str, bytes, os.PathLike)):
        s = str(overrides).strip()
        if not s:
            return {}
        try:
            obj = json.loads(s)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            pairs = [p for p in s.split(",") if p.strip()]
            out: ConfigDict = {}
            for pair in pairs:
                if "=" not in pair:
                    continue
                k, v = pair.split("=", 1)
                _set_dotted(out, k.strip(), _parse_scalar(v))
            return out
    if isinstance(overrides, Sequence):
        out: ConfigDict = {}
        for item in overrides:
            if not item:
                continue
            if isinstance(item, dict):
                out = _deep_merge(out, item)
                continue
            s = str(item)
            if "=" not in s:
                continue
            k, v = s.split("=", 1)
            _set_dotted(out, k.strip(), _parse_scalar(v))
        return out
    raise TypeError(f"Unsupported overrides type: {type(overrides)!r}")
def _read_config_file(path: Path) -> ConfigDict:
    text = path.read_text(encoding="utf-8")
    suf = path.suffix.lower()
    if suf in {".json"}:
        obj = json.loads(text) if text.strip() else {}
    elif suf in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:
            raise RuntimeError("YAML config requested but PyYAML is not installed") from e
        obj = yaml.safe_load(text) if text.strip() else {}
    else:
        raise ValueError(f"Unsupported config extension: {path.suffix}")
    if obj is None:
        return {}
    if not isinstance(obj, dict):
        raise TypeError(f"Config root must be a mapping, got {type(obj)!r}")
    return obj
def _resolve_relative_paths(cfg: Any, base_dir: Path, keys: tuple[str, ...] = ("path", "file", "dir")) -> Any:
    if isinstance(cfg, dict):
        out: dict[str, Any] = {}
        for k, v in cfg.items():
            if isinstance(v, str) and any(k.lower().endswith(s) for s in keys):
                pv = Path(v)
                if not pv.is_absolute():
                    out[k] = str((base_dir / pv).resolve())
                else:
                    out[k] = str(pv)
            else:
                out[k] = _resolve_relative_paths(v, base_dir, keys)
        return out
    if isinstance(cfg, list):
        return [_resolve_relative_paths(x, base_dir, keys) for x in cfg]
    return cfg
def _stable_hash(cfg: ConfigDict) -> str:
    blob = json.dumps(cfg, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
@dataclass(frozen=True)
class ConfigBundle:
    """Final config plus small amount of provenance."""

    config: ConfigDict
    config_hash: str
    sources: tuple[str, ...] = ()
    resolved_base_dir: Optional[str] = None
def build_config(
    *,
    defaults: Optional[Mapping[str, Any]] = None,
    user_config: Optional[Union[Mapping[str, Any], str, os.PathLike]] = None,
    overrides: Any = None,
    validators: Optional[Sequence[Validator]] = None,
    resolve_paths: bool = True,
) -> ConfigBundle:
    """Compose defaults + user config + overrides; validate; return ConfigBundle."""
    base: ConfigDict = dict(defaults or {})
    sources: list[str] = []
    base_dir: Optional[Path] = None

    if user_config is not None:
        if isinstance(user_config, Mapping):
            user_dict = dict(user_config)
            sources.append("mapping")
        else:
            p = Path(user_config).expanduser()
            if not p.is_absolute():
                p = (Path.cwd() / p).resolve()
            user_dict = _read_config_file(p)
            sources.append(str(p))
            base_dir = p.parent
        base = _deep_merge(base, user_dict)

    ov = _overrides_to_dict(overrides)
    if ov:
        sources.append("overrides")
        base = _deep_merge(base, ov)

    if resolve_paths and base_dir is not None:
        base = _resolve_relative_paths(base, base_dir)

    if validators:
        for v in validators:
            v(base)

    if not isinstance(base, dict):
        raise TypeError("Final config must be a mapping")

    return ConfigBundle(
        config=base,
        config_hash=_stable_hash(base),
        sources=tuple(sources),
        resolved_base_dir=str(base_dir) if base_dir is not None else None,
    )
