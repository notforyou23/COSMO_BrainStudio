from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union


PathLike = Union[str, Path]


@dataclass
class UpdateResult:
    data: Any
    changes: List[Tuple[str, str]]
    missing_files: List[str]


def _root_dir_for_tracker(tracker_path: Path) -> Path:
    p = tracker_path.resolve()
    for parent in p.parents:
        if parent.name == "execution":
            return parent
    return p.parents[2] if len(p.parents) >= 3 else p.parent


def _norm_path_str(s: str) -> str:
    s = s.strip().replace("\\", "/")
    s = re.sub(r"^\./+", "", s)
    return s


def _detect_indent(text: str, default: int = 2) -> int:
    for line in text.splitlines():
        m = re.match(r'^(\s+)"', line)
        if m:
            return max(2, len(m.group(1).replace("\t", " " * 4)))
    return default


def load_project_tracker(tracker_path: PathLike) -> Tuple[Any, int, str]:
    p = Path(tracker_path)
    raw = p.read_text(encoding="utf-8")
    indent = _detect_indent(raw)
    data = json.loads(raw, object_pairs_hook=OrderedDict)
    return data, indent, raw


def _build_mapping(mapping: Dict[PathLike, PathLike], root_dir: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in mapping.items():
        ks = _norm_path_str(str(k))
        vs = _norm_path_str(str(v))
        out[ks] = vs
        try:
            kp = Path(ks)
            if kp.is_absolute() and root_dir in kp.resolve().parents:
                out[_norm_path_str(str(kp.resolve().relative_to(root_dir)))] = vs
        except Exception:
            pass
    return out


def _maybe_rel_to_root(s: str, root_dir: Path) -> str:
    try:
        p = Path(s)
        if p.is_absolute():
            pr = p.resolve()
            if root_dir in pr.parents or pr == root_dir:
                return _norm_path_str(str(pr.relative_to(root_dir)))
    except Exception:
        pass
    return _norm_path_str(s)


def rewrite_tracked_paths(data: Any, mapping: Dict[PathLike, PathLike], tracker_path: PathLike) -> Tuple[Any, List[Tuple[str, str]]]:
    tracker_path = Path(tracker_path)
    root_dir = _root_dir_for_tracker(tracker_path)
    m = _build_mapping(mapping, root_dir)
    changes: List[Tuple[str, str]] = []

    def rec(x: Any) -> Any:
        if isinstance(x, str):
            key = _maybe_rel_to_root(x, root_dir)
            if key in m:
                newv = m[key]
                changes.append((x, newv))
                return newv
            key2 = _norm_path_str(x)
            if key2 in m:
                newv = m[key2]
                changes.append((x, newv))
                return newv
            return x
        if isinstance(x, list):
            return [rec(i) for i in x]
        if isinstance(x, dict):
            od = OrderedDict() if not isinstance(x, OrderedDict) else x.__class__()
            for k, v in x.items():
                od[k] = rec(v)
            return od
        return x

    return rec(data), changes


def iter_possible_file_paths(data: Any) -> Iterable[str]:
    def rec(x: Any) -> Iterable[str]:
        if isinstance(x, str):
            if ("/" in x or "\\" in x or x.startswith(".")) and len(x) < 4096:
                yield x
        elif isinstance(x, list):
            for i in x:
                yield from rec(i)
        elif isinstance(x, dict):
            for v in x.values():
                yield from rec(v)

    seen = set()
    for s in rec(data):
        ns = _norm_path_str(s)
        if ns and ns not in seen:
            seen.add(ns)
            yield s


def validate_referenced_files(data: Any, tracker_path: PathLike, root_dir: Optional[PathLike] = None) -> List[str]:
    tracker_path = Path(tracker_path)
    root = Path(root_dir) if root_dir is not None else _root_dir_for_tracker(tracker_path)
    missing: List[str] = []
    for s in iter_possible_file_paths(data):
        ss = _norm_path_str(s)
        p = Path(ss)
        candidate = (root / p) if not p.is_absolute() else p
        if candidate.exists():
            continue
        if p.is_absolute() and p.exists():
            continue
        missing.append(ss)
    return missing


def save_project_tracker(tracker_path: PathLike, data: Any, indent: int = 2) -> None:
    p = Path(tracker_path)
    text = json.dumps(data, ensure_ascii=False, indent=indent) + "\n"
    p.write_text(text, encoding="utf-8")


def update_project_tracker(
    tracker_path: PathLike,
    mapping: Dict[PathLike, PathLike],
    *,
    root_dir: Optional[PathLike] = None,
    validate: bool = True,
    write: bool = True,
) -> UpdateResult:
    p = Path(tracker_path)
    data, indent, _raw = load_project_tracker(p)
    new_data, changes = rewrite_tracked_paths(data, mapping, p)
    missing = validate_referenced_files(new_data, p, root_dir=root_dir) if validate else []
    if write:
        save_project_tracker(p, new_data, indent=indent)
    return UpdateResult(data=new_data, changes=changes, missing_files=missing)
