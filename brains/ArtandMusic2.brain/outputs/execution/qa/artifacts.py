from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union


PathLike = Union[str, Path]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def atomic_write_text(path: PathLike, text: str, encoding: str = "utf-8") -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
        os.replace(tmp, p)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
    return p


def atomic_write_json(path: PathLike, obj: object, *, indent: int = 2, sort_keys: bool = True) -> Path:
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False) + "\n"
    return atomic_write_text(path, text)


def safe_relpath(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except Exception:
        return str(path)


def copy_file(src: PathLike, dst: PathLike, *, overwrite: bool = True) -> Path:
    s, d = Path(src), Path(dst)
    if not s.exists() or not s.is_file():
        raise FileNotFoundError(str(s))
    ensure_dir(d.parent)
    if d.exists() and not overwrite:
        return d
    shutil.copy2(s, d)
    return d


def copy_globs(
    sources: Sequence[Tuple[PathLike, str]],
    out_dir: PathLike,
    *,
    allow_missing: bool = True,
    overwrite: bool = True,
) -> Dict[str, List[str]]:
    out = ensure_dir(out_dir)
    copied: List[str] = []
    missing: List[str] = []
    for base, pattern in sources:
        b = Path(base)
        hits = sorted(b.glob(pattern)) if b.exists() else []
        if not hits:
            missing.append(f"{b}:{pattern}")
            continue
        for h in hits:
            if h.is_file():
                dst = out / h.name
                copy_file(h, dst, overwrite=overwrite)
                copied.append(str(dst))
    if (not allow_missing) and missing:
        raise FileNotFoundError("Missing artifact sources: " + "; ".join(missing))
    return {"copied": copied, "missing": missing}


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    sources: Sequence[Tuple[Path, str]]
    required: bool = False


def collect_artifact_specs(
    specs: Sequence[ArtifactSpec],
    *,
    out_base: PathLike,
    overwrite: bool = True,
) -> Dict[str, object]:
    outb = ensure_dir(out_base)
    results: Dict[str, object] = {"out_base": str(outb), "artifacts": {}, "time_utc": utc_now_iso()}
    for spec in specs:
        out_dir = ensure_dir(outb / spec.name)
        r = copy_globs(spec.sources, out_dir, allow_missing=not spec.required, overwrite=overwrite)
        results["artifacts"][spec.name] = {
            "out_dir": str(out_dir),
            "required": bool(spec.required),
            "copied": r["copied"],
            "missing": r["missing"],
        }
    return results


def canonical_output_dir(project_root: PathLike, *parts: str) -> Path:
    root = Path(project_root)
    return ensure_dir(root.joinpath("outputs", *parts))


def maybe_read_text(path: PathLike, *, max_bytes: int = 256_000, encoding: str = "utf-8") -> Optional[str]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    data = p.read_bytes()
    if len(data) > max_bytes:
        data = data[:max_bytes]
    try:
        return data.decode(encoding, errors="replace")
    except Exception:
        return None
