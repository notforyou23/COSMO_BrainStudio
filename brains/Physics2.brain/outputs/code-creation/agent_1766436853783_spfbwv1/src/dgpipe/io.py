"""dgpipe.io

Robust, reproducible I/O helpers for configs, datasets, results, and provenance.
Supports JSON / CSV / NPZ with lightweight schema validation and deterministic seeding.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence
import csv
import hashlib
import json
import os
import platform
import random
import sys
import time

import numpy as np
def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def _json_dumps_deterministic(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, obj: Any) -> None:
    _atomic_write_text(Path(path), _json_dumps_deterministic(obj))


def load_csv_dicts(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_csv_dicts(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    fieldnames = sorted({k for r in rows for k in r.keys()})
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    os.replace(tmp, path)


def save_npz(path: str | Path, **arrays: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    np.savez_compressed(tmp, **arrays)
    os.replace(tmp, path)


def load_npz(path: str | Path) -> dict[str, np.ndarray]:
    with np.load(Path(path), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}
@dataclass(frozen=True)
class Schema:
    """Very small schema: mapping key -> type / nested Schema / (type, ...) / list[Schema]."""

    spec: Mapping[str, Any]

    def validate(self, obj: Any, *, where: str = "root") -> None:
        if not isinstance(obj, Mapping):
            raise TypeError(f"{where}: expected mapping, got {type(obj).__name__}")
        for key, rule in self.spec.items():
            if key not in obj:
                raise KeyError(f"{where}: missing required key '{key}'")
            _validate_rule(obj[key], rule, where=f"{where}.{key}")


def _validate_rule(val: Any, rule: Any, *, where: str) -> None:
    if isinstance(rule, Schema):
        rule.validate(val, where=where)
        return
    if isinstance(rule, list):
        if len(rule) != 1 or not isinstance(rule[0], (type, Schema, tuple)):
            raise TypeError(f"{where}: invalid list rule")
        if not isinstance(val, Sequence) or isinstance(val, (str, bytes, bytearray)):
            raise TypeError(f"{where}: expected sequence, got {type(val).__name__}")
        for i, v in enumerate(val):
            _validate_rule(v, rule[0], where=f"{where}[{i}]")
        return
    if isinstance(rule, tuple):
        if not isinstance(val, rule):
            exp = ",".join(t.__name__ for t in rule)
            raise TypeError(f"{where}: expected one of ({exp}), got {type(val).__name__}")
        return
    if isinstance(rule, type):
        if not isinstance(val, rule):
            raise TypeError(f"{where}: expected {rule.__name__}, got {type(val).__name__}")
        return
    raise TypeError(f"{where}: invalid schema rule {rule!r}")


def load_config(path: str | Path, schema: Schema | None = None) -> dict[str, Any]:
    cfg = load_json(path)
    if schema is not None:
        schema.validate(cfg)
    if not isinstance(cfg, dict):
        raise TypeError("config: expected JSON object at top-level")
    return cfg
def stable_int_hash(obj: Any, *, salt: str = "") -> int:
    payload = _json_dumps_deterministic({"salt": salt, "obj": obj}).encode("utf-8")
    h = hashlib.sha256(payload).digest()
    return int.from_bytes(h[:8], "big", signed=False)


def set_global_seed(seed: int) -> None:
    """Seed Python + NumPy deterministically (call early in the pipeline)."""
    random.seed(int(seed) & 0xFFFFFFFF)
    np.random.seed(int(seed) & 0xFFFFFFFF)


def seed_from_config(cfg: Mapping[str, Any], *, salt: str = "dgpipe") -> int:
    """Derive a deterministic 64-bit seed from a config mapping."""
    return stable_int_hash(cfg, salt=salt)


def provenance(cfg: Mapping[str, Any], *, seed: int | None = None, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    prov: MutableMapping[str, Any] = {
        "time_unix": time.time(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cwd": os.getcwd(),
    }
    if seed is not None:
        prov["seed"] = int(seed)
    prov["config_hash64"] = stable_int_hash(cfg, salt="config")
    if extra:
        prov["extra"] = dict(extra)
    return dict(prov)


def write_bundle(outdir: str | Path, *, cfg: Mapping[str, Any], results: Mapping[str, Any] | None = None,
                 arrays: Mapping[str, Any] | None = None, seed: int | None = None,
                 cfg_schema: Schema | None = None, prov_extra: Mapping[str, Any] | None = None) -> dict[str, str]:
    """Write a minimal, reproducible result bundle: config.json, provenance.json, results.json, arrays.npz."""
    if cfg_schema is not None:
        cfg_schema.validate(cfg)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    save_json(out / "config.json", dict(cfg))
    save_json(out / "provenance.json", provenance(cfg, seed=seed, extra=prov_extra))
    if results is not None:
        save_json(out / "results.json", results)
    if arrays:
        save_npz(out / "arrays.npz", **dict(arrays))
    return {
        "config": str(out / "config.json"),
        "provenance": str(out / "provenance.json"),
        "results": str(out / "results.json") if results is not None else "",
        "arrays": str(out / "arrays.npz") if arrays else "",
    }
