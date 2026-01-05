from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Union
import json
import os
import time
def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")
def _load_yaml(text: str) -> Any:
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError("YAML config provided but PyYAML is not available") from e
    return yaml.safe_load(text)
def load_config_file(path: Optional[Union[str, Path]]) -> Dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    text = _read_text(p)
    suf = p.suffix.lower()
    if suf in (".json",):
        data = json.loads(text or "{}")
    elif suf in (".yaml", ".yml"):
        data = _load_yaml(text or "")
    else:
        # Try JSON first, then YAML.
        try:
            data = json.loads(text)
        except Exception:
            data = _load_yaml(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be an object/dict; got {type(data).__name__}")
    return data
def _coerce_value(v: Any) -> Any:
    if not isinstance(v, str):
        return v
    s = v.strip()
    if s == "":
        return ""
    # Try JSON literals/containers (true/false/null/number/object/array/string)
    try:
        return json.loads(s)
    except Exception:
        return v
def _set_dotted(cfg: Dict[str, Any], key: str, value: Any) -> None:
    parts = [p for p in key.split(".") if p]
    if not parts:
        return
    cur: Dict[str, Any] = cfg
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value
def parse_cli_overrides(overrides: Optional[Union[Mapping[str, Any], Iterable[str]]]) -> Dict[str, Any]:
    if overrides is None:
        return {}
    if isinstance(overrides, Mapping):
        return {str(k): overrides[k] for k in overrides}
    out: Dict[str, Any] = {}
    for item in overrides:
        if item is None:
            continue
        s = str(item)
        if "=" not in s:
            raise ValueError(f"Override must be KEY=VALUE; got {s!r}")
        k, v = s.split("=", 1)
        out[k.strip()] = _coerce_value(v)
    return out
def apply_overrides(base: Dict[str, Any], overrides: Mapping[str, Any]) -> Dict[str, Any]:
    cfg = dict(base)
    for k, v in overrides.items():
        _set_dotted(cfg, str(k), _coerce_value(v))
    return cfg
def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{int(time.time()*1000)}")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
def persist_resolved_config(
    resolved: Mapping[str, Any],
    logs_dir: Optional[Union[str, Path]] = None,
    filename: str = "config.resolved.json",
) -> Path:
    logs = Path(logs_dir) if logs_dir else Path("runtime/_build/logs")
    out = logs / filename
    _atomic_write_json(out, dict(resolved))
    return out
def load_resolve_persist(
    config_path: Optional[Union[str, Path]],
    cli_overrides: Optional[Union[Mapping[str, Any], Iterable[str]]] = None,
    logs_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    base = load_config_file(config_path)
    ov = parse_cli_overrides(cli_overrides)
    resolved = apply_overrides(base, ov)
    persist_resolved_config(resolved, logs_dir=logs_dir)
    return resolved
