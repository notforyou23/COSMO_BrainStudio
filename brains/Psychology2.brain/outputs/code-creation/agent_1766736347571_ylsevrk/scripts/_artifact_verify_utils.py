from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import json


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def norm_exts(exts: Optional[Sequence[str]]) -> Tuple[str, ...]:
    if not exts:
        return tuple()
    out = []
    for e in exts:
        if not e:
            continue
        e = e.strip().lower()
        if not e:
            continue
        if not e.startswith("."):
            e = "." + e
        out.append(e)
    return tuple(sorted(set(out)))


def is_non_empty_file(path: Path, min_bytes: int = 1) -> bool:
    try:
        return path.is_file() and path.stat().st_size >= int(min_bytes)
    except FileNotFoundError:
        return False


def list_files(
    directory: Path,
    *,
    exts: Optional[Sequence[str]] = None,
    recursive: bool = False,
) -> List[Path]:
    exts_n = norm_exts(exts)
    if not directory.exists() or not directory.is_dir():
        return []
    it = directory.rglob("*") if recursive else directory.glob("*")
    files = [p for p in it if p.is_file()]
    if exts_n:
        files = [p for p in files if p.suffix.lower() in exts_n]
    return sorted(files, key=lambda p: p.as_posix())


@dataclass(frozen=True)
class Requirement:
    name: str
    rel_dir: str
    exts: Tuple[str, ...]
    min_count: int = 1
    min_bytes: int = 1
    recursive: bool = False

    @staticmethod
    def from_dict(d: Mapping) -> "Requirement":
        return Requirement(
            name=str(d.get("name") or d.get("rel_dir") or "artifact"),
            rel_dir=str(d["rel_dir"]),
            exts=norm_exts(d.get("exts") or d.get("extensions")),
            min_count=int(d.get("min_count", 1)),
            min_bytes=int(d.get("min_bytes", 1)),
            recursive=bool(d.get("recursive", False)),
        )


def find_matching(requirement: Requirement, base_dir: Path) -> List[Path]:
    directory = base_dir / requirement.rel_dir
    candidates = list_files(directory, exts=requirement.exts or None, recursive=requirement.recursive)
    matches = [p for p in candidates if is_non_empty_file(p, min_bytes=requirement.min_bytes)]
    return sorted(matches, key=lambda p: p.as_posix())


def verify_requirements(
    requirements: Sequence[Requirement],
    base_dir: Path,
) -> Tuple[Dict[str, List[Path]], List[Dict[str, object]]]:
    found: Dict[str, List[Path]] = {}
    missing: List[Dict[str, object]] = []
    for req in sorted(requirements, key=lambda r: (r.rel_dir, r.name, r.exts, r.min_count, r.min_bytes, r.recursive)):
        matches = find_matching(req, base_dir)
        found[req.name] = matches
        if len(matches) < req.min_count:
            missing.append(
                {
                    "name": req.name,
                    "rel_dir": req.rel_dir,
                    "exts": list(req.exts),
                    "min_count": req.min_count,
                    "min_bytes": req.min_bytes,
                    "found_count": len(matches),
                    "found": [p.as_posix() for p in matches],
                    "dir_exists": (base_dir / req.rel_dir).is_dir(),
                }
            )
    missing = sorted(missing, key=lambda m: (str(m["rel_dir"]), str(m["name"])))
    return found, missing


def format_missing(missing: Sequence[Mapping[str, object]], base_dir: Optional[Path] = None) -> str:
    lines: List[str] = []
    prefix = f" under {base_dir.as_posix()}" if base_dir else ""
    lines.append(f"Missing required artifacts{prefix}:")
    for m in missing:
        rel_dir = str(m.get("rel_dir", ""))
        name = str(m.get("name", "artifact"))
        exts = m.get("exts") or []
        min_count = int(m.get("min_count", 1))
        found_count = int(m.get("found_count", 0))
        dir_exists = bool(m.get("dir_exists", False))
        exts_s = ", ".join(exts) if exts else "(any extension)"
        dir_note = "dir missing" if not dir_exists else "no matching non-empty files"
        lines.append(f"- {name}: need >= {min_count} file(s) in {rel_dir} with {exts_s}; found {found_count} ({dir_note})")
    return "\n".join(lines)


def die_if_missing(missing: Sequence[Mapping[str, object]], *, base_dir: Optional[Path] = None, exit_code: int = 2) -> None:
    if missing:
        raise SystemExit(f"{format_missing(missing, base_dir=base_dir)}\n")


def rel_paths(paths: Iterable[Path], base_dir: Path) -> List[str]:
    out = []
    for p in paths:
        try:
            out.append(str(p.relative_to(base_dir)).replace('\\', '/'))
        except Exception:
            out.append(p.as_posix())
    return sorted(out)
