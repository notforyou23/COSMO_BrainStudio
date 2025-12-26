from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
import csv
import datetime as _dt
import hashlib
import json
import os
JsonLike = Union[None, bool, int, float, str, List["JsonLike"], Dict[str, "JsonLike"]]


def _deep_update(base: Dict[str, Any], upd: Mapping[str, Any]) -> Dict[str, Any]:
    for k, v in upd.items():
        if isinstance(v, Mapping) and isinstance(base.get(k), Mapping):
            base[k] = _deep_update(dict(base[k]), v)
        else:
            base[k] = v
    return base


def _stable_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def config_hash(cfg: Mapping[str, Any]) -> str:
    h = hashlib.sha256(_stable_dumps(cfg).encode("utf-8")).hexdigest()
    return h[:12]
def load_config(path: Union[str, Path], schema: Any = None, overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.suffix.lower() in {".json"}:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    elif p.suffix.lower() in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("YAML config requested but PyYAML is not installed") from e
        cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"Unsupported config extension: {p.suffix}")
    if not isinstance(cfg, dict):
        raise TypeError("Config root must be a JSON/YAML object (dict).")
    if overrides:
        cfg = _deep_update(cfg, overrides)
    if schema is not None:
        cfg = validate_config(cfg, schema)
    return cfg
def _type_name(t: Any) -> str:
    if isinstance(t, tuple):
        return " | ".join(_type_name(x) for x in t)
    return getattr(t, "__name__", str(t))


def validate_config(cfg: Dict[str, Any], schema: Any, path: str = "cfg") -> Dict[str, Any]:
    # schema supports:
    # - type or tuple(types)
    # - dict: nested schema or rich spec via keys {type, required, default, choices, min, max}
    # - [elem_schema] for homogeneous sequences
    def err(msg: str) -> None:
        raise ValueError(f"{path}: {msg}")

    if isinstance(schema, (type, tuple)):
        if not isinstance(cfg, schema):
            err(f"expected {_type_name(schema)}, got {type(cfg).__name__}")
        return cfg

    if isinstance(schema, list):
        if len(schema) != 1:
            err("list schema must have exactly one element spec")
        if not isinstance(cfg, list):
            err(f"expected list, got {type(cfg).__name__}")
        for i, item in enumerate(cfg):
            validate_config(item, schema[0], f"{path}[{i}]")
        return cfg

    if not isinstance(schema, Mapping):
        err("invalid schema object")

    # rich spec for a scalar field
    if "type" in schema:
        t = schema.get("type")
        if not isinstance(cfg, t):
            err(f"expected {_type_name(t)}, got {type(cfg).__name__}")
        if "choices" in schema and cfg not in schema["choices"]:
            err(f"value {cfg!r} not in choices {list(schema['choices'])!r}")
        if isinstance(cfg, (int, float)):
            if "min" in schema and cfg < schema["min"]:
                err(f"value {cfg} < min {schema['min']}")
            if "max" in schema and cfg > schema["max"]:
                err(f"value {cfg} > max {schema['max']}")
        return cfg

    # object schema: keys -> subschema / rich spec
    if not isinstance(cfg, dict):
        err(f"expected object, got {type(cfg).__name__}")

    out: Dict[str, Any] = dict(cfg)
    for key, spec in schema.items():
        required = True
        default = None
        if isinstance(spec, Mapping) and "type" in spec:
            required = bool(spec.get("required", True))
            default = spec.get("default", None)
        if key not in out:
            if required:
                if isinstance(spec, Mapping) and "type" in spec and "default" in spec:
                    out[key] = default
                else:
                    raise ValueError(f"{path}: missing required key {key!r}")
            else:
                if isinstance(spec, Mapping) and "default" in spec:
                    out[key] = default
                continue
        out[key] = validate_config(out[key], spec, f"{path}.{key}")
    return out
def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def save_json(path: Union[str, Path], obj: Any, indent: int = 2) -> Path:
    p = Path(path)
    _atomic_write_text(p, json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + "\n")
    return p


def save_csv(path: Union[str, Path], rows: Sequence[Mapping[str, Any]]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if len(rows) == 0:
        _atomic_write_text(p, "")
        return p
    cols: List[str] = sorted({k for r in rows for k in r.keys()})
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    os.replace(tmp, p)
    return p
@dataclass(frozen=True)
class ExperimentRun:
    run_dir: Path
    config: Dict[str, Any]
    meta: Dict[str, Any]

    @property
    def artifacts_dir(self) -> Path:
        return self.run_dir / "artifacts"

    def save_artifact(self, name: str, obj: Any, fmt: str = "json") -> Path:
        fmt = fmt.lower()
        out = self.artifacts_dir / f"{name}.{fmt}"
        if fmt == "json":
            return save_json(out, obj)
        if fmt == "csv":
            if not isinstance(obj, Sequence):
                raise TypeError("CSV artifact expects a sequence of row mappings")
            return save_csv(out, obj)  # type: ignore[arg-type]
        raise ValueError(f"Unsupported artifact format: {fmt}")

    def log_event(self, event: Mapping[str, Any]) -> Path:
        e = dict(event)
        e.setdefault("ts", _dt.datetime.utcnow().isoformat() + "Z")
        path = self.run_dir / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(_stable_dumps(e) + "\n")
        return path
def create_run_dir(
    base_dir: Union[str, Path],
    config: Mapping[str, Any],
    name: Optional[str] = None,
    tag: Optional[str] = None,
    extra_meta: Optional[Mapping[str, Any]] = None,
) -> ExperimentRun:
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    h = config_hash(config)
    stem = name or "run"
    parts = [stem, ts, h]
    if tag:
        parts.insert(1, tag)
    run_dir = base / "_".join(parts)
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)

    meta = {
        "created_utc": ts,
        "config_hash": h,
        "name": stem,
        "tag": tag,
        "cwd": str(Path.cwd()),
    }
    if extra_meta:
        meta.update(dict(extra_meta))

    save_json(run_dir / "config.json", dict(config))
    save_json(run_dir / "meta.json", meta)
    return ExperimentRun(run_dir=run_dir, config=dict(config), meta=meta)
