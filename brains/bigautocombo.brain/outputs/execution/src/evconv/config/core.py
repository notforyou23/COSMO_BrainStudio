from __future__ import annotations

from dataclasses import asdict, is_dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence
import json


def deep_merge(base: Any, override: Any) -> Any:
    if override is None:
        return base
    if base is None:
        return override
    if isinstance(base, Mapping) and isinstance(override, Mapping):
        out: dict[str, Any] = dict(base)
        for k, v in override.items():
            out[k] = deep_merge(base.get(k), v)
        return out
    return override


def _norm_key(k: Any) -> str:
    if isinstance(k, str):
        return k
    if isinstance(k, (Path,)):
        return k.as_posix()
    return str(k)


def normalize_config(obj: Any) -> Any:
    if is_dataclass(obj):
        return normalize_config(asdict(obj))
    if isinstance(obj, Path):
        return obj.as_posix()
    if isinstance(obj, Mapping):
        items = [(_norm_key(k), normalize_config(v)) for k, v in obj.items()]
        items.sort(key=lambda kv: kv[0])
        return {k: v for k, v in items}
    if isinstance(obj, (set, frozenset)):
        return sorted((normalize_config(x) for x in obj), key=lambda x: json.dumps(x, sort_keys=True, separators=(",", ":")))
    if isinstance(obj, tuple):
        return [normalize_config(x) for x in obj]
    if isinstance(obj, list):
        return [normalize_config(x) for x in obj]
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return {"__bytes__": bytes(obj).hex()}
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return {"__repr__": repr(obj)}


def config_canonical_json(obj: Any) -> str:
    norm = normalize_config(obj)
    return json.dumps(norm, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def config_hash(obj: Any, *, algo: str = "sha256") -> str:
    if algo.lower() != "sha256":
        raise ValueError("Only sha256 is supported for deterministic config hashing.")
    s = config_canonical_json(obj).encode("utf-8")
    return sha256(s).hexdigest()


def update_inplace(dst: MutableMapping[str, Any], src: Mapping[str, Any]) -> MutableMapping[str, Any]:
    merged = deep_merge(dst, src)
    dst.clear()
    if isinstance(merged, Mapping):
        dst.update(merged)
    return dst


def get_in(d: Mapping[str, Any], path: Sequence[str], default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, Mapping) or key not in cur:
            return default
        cur = cur[key]
    return cur


def set_in(d: MutableMapping[str, Any], path: Sequence[str], value: Any) -> None:
    cur: MutableMapping[str, Any] = d
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, MutableMapping):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value
