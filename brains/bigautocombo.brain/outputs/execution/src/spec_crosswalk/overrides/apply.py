"""Core logic for applying overrides to in-memory objects in a deterministic way.

Supported override forms:
- Mapping {path: value} -> implicit 'set'
- Sequence of ops: {'op': 'set'|'delete'|'merge', 'path': <str|list>, 'value': <any?>}

Paths are dot/bracket style (e.g., "a.b[0].c") or an explicit list of keys/indices.
Targets may be dicts, lists, or objects with attributes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, MutableMapping, MutableSequence, Sequence, Union
import re


class OverrideError(Exception):
    """Raised when an override cannot be applied."""


_PathSeg = Union[str, int]
_PATH_RE = re.compile(r"(\\.[^\\.\\[]+)|(\\[[0-9]+\\])|(^[^\\.\\[]+)")
@dataclass(frozen=True)
class OverrideOp:
    op: str
    path: Union[str, Sequence[_PathSeg]]
    value: Any = None


def parse_path(path: Union[str, Sequence[_PathSeg]]) -> list[_PathSeg]:
    if isinstance(path, (list, tuple)):
        out: list[_PathSeg] = []
        for s in path:
            if isinstance(s, (str, int)):
                out.append(s)
            else:
                raise OverrideError(f"Invalid path segment type: {type(s)!r}")
        return out
    if not isinstance(path, str) or not path:
        raise OverrideError("path must be a non-empty string or a list of segments")
    out: list[_PathSeg] = []
    for m in _PATH_RE.finditer(path):
        tok = m.group(0)
        if tok.startswith('.'):
            out.append(tok[1:])
        elif tok.startswith('['):
            out.append(int(tok[1:-1]))
        else:
            out.append(tok)
    if not out:
        raise OverrideError(f"Unable to parse path: {path!r}")
    return out
def _is_mapping(x: Any) -> bool:
    return isinstance(x, MutableMapping)


def _is_sequence(x: Any) -> bool:
    return isinstance(x, MutableSequence)


def _get_child(container: Any, seg: _PathSeg) -> Any:
    if isinstance(seg, int):
        if not _is_sequence(container):
            raise OverrideError(f"Expected list at segment {seg!r}, got {type(container).__name__}")
        if seg < 0 or seg >= len(container):
            raise OverrideError(f"Index out of range: {seg}")
        return container[seg]
    if _is_mapping(container):
        if seg not in container:
            raise OverrideError(f"Missing key: {seg!r}")
        return container[seg]
    try:
        return getattr(container, seg)
    except Exception as e:
        raise OverrideError(f"Missing attribute: {seg!r}") from e


def _set_child(container: Any, seg: _PathSeg, value: Any) -> None:
    if isinstance(seg, int):
        if not _is_sequence(container):
            raise OverrideError(f"Expected list for index set, got {type(container).__name__}")
        if seg < 0:
            raise OverrideError("Negative indices not supported")
        while len(container) <= seg:
            container.append(None)
        container[seg] = value
        return
    if _is_mapping(container):
        container[seg] = value
        return
    try:
        setattr(container, seg, value)
    except Exception as e:
        raise OverrideError(f"Unable to set attribute {seg!r} on {type(container).__name__}") from e


def _del_child(container: Any, seg: _PathSeg) -> None:
    if isinstance(seg, int):
        if not _is_sequence(container):
            raise OverrideError(f"Expected list for index delete, got {type(container).__name__}")
        if seg < 0 or seg >= len(container):
            raise OverrideError(f"Index out of range: {seg}")
        del container[seg]
        return
    if _is_mapping(container):
        if seg in container:
            del container[seg]
            return
        raise OverrideError(f"Missing key: {seg!r}")
    if hasattr(container, seg):
        try:
            delattr(container, seg)
            return
        except Exception as e:
            raise OverrideError(f"Unable to delete attribute {seg!r} on {type(container).__name__}") from e
    raise OverrideError(f"Missing attribute: {seg!r}")
def _ensure_path(root: Any, segs: Sequence[_PathSeg]) -> tuple[Any, _PathSeg]:
    if not segs:
        raise OverrideError("Empty path")
    cur = root
    for i in range(len(segs) - 1):
        s = segs[i]
        nxt = segs[i + 1]
        try:
            child = _get_child(cur, s)
        except OverrideError:
            child = [] if isinstance(nxt, int) else {}
            _set_child(cur, s, child)
        if child is None:
            child = [] if isinstance(nxt, int) else {}
            _set_child(cur, s, child)
        cur = child
    return cur, segs[-1]


def _deep_merge(dst: Any, src: Any) -> Any:
    if _is_mapping(dst) and isinstance(src, Mapping):
        for k, v in src.items():
            if k in dst:
                dst[k] = _deep_merge(dst[k], v)
            else:
                dst[k] = v
        return dst
    if _is_sequence(dst) and isinstance(src, Sequence) and not isinstance(src, (str, bytes, bytearray)):
        dst.extend(list(src))
        return dst
    return src
def normalize_overrides(overrides: Any) -> list[OverrideOp]:
    if overrides is None:
        return []
    if isinstance(overrides, Mapping) and not isinstance(overrides, (str, bytes, bytearray)):
        return [OverrideOp(op="set", path=k, value=v) for k, v in sorted(overrides.items(), key=lambda kv: str(kv[0]))]
    if isinstance(overrides, Sequence) and not isinstance(overrides, (str, bytes, bytearray)):
        out: list[OverrideOp] = []
        for item in overrides:
            if isinstance(item, OverrideOp):
                out.append(item)
            elif isinstance(item, Mapping):
                op = str(item.get("op", "set")).lower()
                if "path" not in item:
                    raise OverrideError("Override item missing 'path'")
                out.append(OverrideOp(op=op, path=item["path"], value=item.get("value")))
            else:
                raise OverrideError(f"Invalid override item type: {type(item)!r}")
        return out
    raise OverrideError(f"Invalid overrides type: {type(overrides)!r}")


def apply_overrides(obj: Any, overrides: Any) -> Any:
    ops = normalize_overrides(overrides)
    for op in ops:
        segs = parse_path(op.path)
        if op.op == "set":
            parent, leaf = _ensure_path(obj, segs)
            _set_child(parent, leaf, op.value)
        elif op.op == "delete":
            parent, leaf = _ensure_path(obj, segs)
            _del_child(parent, leaf)
        elif op.op == "merge":
            parent, leaf = _ensure_path(obj, segs)
            try:
                cur = _get_child(parent, leaf)
            except OverrideError:
                cur = {} if isinstance(op.value, Mapping) else []
            _set_child(parent, leaf, _deep_merge(cur, op.value))
        else:
            raise OverrideError(f"Unsupported op: {op.op!r}")
    return obj


__all__ = ["OverrideError", "OverrideOp", "parse_path", "normalize_overrides", "apply_overrides"]
