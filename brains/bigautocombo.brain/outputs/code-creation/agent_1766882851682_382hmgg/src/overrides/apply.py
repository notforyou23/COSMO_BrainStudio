from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, MutableSequence, Sequence, Tuple, Union
import copy
import re


class OverrideApplyError(Exception):
    pass


_Key = Union[str, int]


@dataclass(frozen=True)
class Operation:
    op: str
    path: str
    value: Any = None
    index: int = -1


_PATH_TOKEN_RE = re.compile(r"""(?x)
    (?:^|\.)                                  # start or dot
    (?:
        (?P<name>[^.\[]+)                      # bare name
        |
        \[(?P<idx>-?\d+)\]                   # [0]
        |
        \[(?P<q>['\"])(?P<qname>.*?)(?P=q)\] # ['x'] or ["x"]
    )
""")


def _parse_path(path: str) -> List[_Key]:
    if not isinstance(path, str) or not path:
        raise OverrideApplyError(f"Invalid path: {path!r}")
    pos = 0
    out: List[_Key] = []
    for m in _PATH_TOKEN_RE.finditer(path):
        if m.start() != pos:
            raise OverrideApplyError(f"Invalid path syntax at {path[pos:]} in {path!r}")
        pos = m.end()
        if m.group("name") is not None:
            out.append(m.group("name"))
        elif m.group("idx") is not None:
            out.append(int(m.group("idx")))
        else:
            out.append(m.group("qname"))
    if pos != len(path):
        raise OverrideApplyError(f"Invalid path syntax at {path[pos:]} in {path!r}")
    return out


def _deep_merge(a: Any, b: Any) -> Any:
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = _deep_merge(out[k], v) if k in out else copy.deepcopy(v)
        return out
    return copy.deepcopy(b)


def _ensure_container(cur: Any, key: _Key, next_key: _Key) -> Any:
    if isinstance(key, int):
        if not isinstance(cur, list):
            raise OverrideApplyError(f"Expected list container, got {type(cur).__name__}")
        n = key if key >= 0 else len(cur) + key
        if n < 0:
            raise OverrideApplyError(f"Negative index out of range: {key}")
        while len(cur) <= n:
            cur.append({} if isinstance(next_key, str) else [])
        return cur[n]
    else:
        if not isinstance(cur, dict):
            raise OverrideApplyError(f"Expected dict container, got {type(cur).__name__}")
        if key not in cur or cur[key] is None:
            cur[key] = {} if isinstance(next_key, str) else []
        return cur[key]


def _get_parent(root: Any, keys: Sequence[_Key], create: bool) -> Tuple[Any, _Key]:
    if not keys:
        raise OverrideApplyError("Empty path")
    if len(keys) == 1:
        return root, keys[0]
    cur = root
    for i in range(len(keys) - 1):
        k = keys[i]
        nk = keys[i + 1]
        if isinstance(k, int):
            if not isinstance(cur, list):
                if not create:
                    raise OverrideApplyError(f"Path expects list at {keys[:i]}" )
                raise OverrideApplyError(f"Cannot create list at non-list container for {k}")
            idx = k if k >= 0 else len(cur) + k
            if idx < 0 or idx >= len(cur):
                if not create:
                    raise OverrideApplyError(f"List index out of range at {k} in {keys}")
                while len(cur) <= idx:
                    cur.append({} if isinstance(nk, str) else [])
            if cur[idx] is None and create:
                cur[idx] = {} if isinstance(nk, str) else []
            cur = cur[idx]
        else:
            if not isinstance(cur, dict):
                raise OverrideApplyError(f"Path expects dict at {keys[:i]}" )
            if k not in cur:
                if not create:
                    raise OverrideApplyError(f"Missing key {k!r} in path {keys}")
                cur[k] = {} if isinstance(nk, str) else []
            elif cur[k] is None and create:
                cur[k] = {} if isinstance(nk, str) else []
            cur = cur[k]
    return cur, keys[-1]


def _set_at(parent: Any, key: _Key, value: Any) -> None:
    if isinstance(key, int):
        if not isinstance(parent, list):
            raise OverrideApplyError(f"Expected list for index set, got {type(parent).__name__}")
        idx = key if key >= 0 else len(parent) + key
        if idx < 0:
            raise OverrideApplyError(f"Negative index out of range: {key}")
        while len(parent) <= idx:
            parent.append(None)
        parent[idx] = value
    else:
        if not isinstance(parent, dict):
            raise OverrideApplyError(f"Expected dict for key set, got {type(parent).__name__}")
        parent[key] = value


def _del_at(parent: Any, key: _Key) -> None:
    if isinstance(key, int):
        if not isinstance(parent, list):
            raise OverrideApplyError(f"Expected list for index delete, got {type(parent).__name__}")
        idx = key if key >= 0 else len(parent) + key
        if idx < 0 or idx >= len(parent):
            return
        del parent[idx]
    else:
        if not isinstance(parent, dict):
            raise OverrideApplyError(f"Expected dict for key delete, got {type(parent).__name__}")
        parent.pop(key, None)


def _as_ops(overrides: Any) -> List[Operation]:
    if overrides is None:
        return []
    if isinstance(overrides, Mapping):
        if "overrides" in overrides:
            overrides = overrides["overrides"]
        elif "ops" in overrides:
            overrides = overrides["ops"]
        else:
            raise OverrideApplyError("Override document must contain 'overrides' or 'ops' list")
    if not isinstance(overrides, Sequence) or isinstance(overrides, (str, bytes)):
        raise OverrideApplyError("Overrides must be a sequence of operation mappings")
    ops: List[Operation] = []
    for i, item in enumerate(overrides):
        if not isinstance(item, Mapping):
            raise OverrideApplyError(f"Operation #{i} must be a mapping")
        op = str(item.get("op", "set")).strip().lower()
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise OverrideApplyError(f"Operation #{i} missing/invalid path")
        val = item.get("value", None)
        ops.append(Operation(op=op, path=path, value=val, index=i))
    # If caller provided a non-list Sequence, enforce deterministic order by path then index.
    return sorted(ops, key=lambda o: (o.path, o.index))
def apply_overrides(target: Any, overrides: Any, *, strict: bool = True) -> Any:
    """Apply validated overrides to target in a deterministic order.

    Supported ops:
      - set: set value at path (creates intermediate dict keys; list indices must exist or be within extendable range)
      - merge: deep-merge dict at path with provided dict value (falls back to set for non-dict)
      - delete: delete key/index at path (no-op if missing/out of range)
      - append: append value to list at path
      - extend: extend list at path with value (must be a sequence)
      - insert: insert into list at path at integer index provided as value: {'index': int, 'value': any} or (idx, val)
    """
    root = target
    ops = _as_ops(overrides)

    def fail(msg: str) -> None:
        if strict:
            raise OverrideApplyError(msg)

    for o in ops:
        try:
            keys = _parse_path(o.path)
            if o.op == "set":
                parent, k = _get_parent(root, keys, create=True)
                _set_at(parent, k, copy.deepcopy(o.value))
            elif o.op == "merge":
                parent, k = _get_parent(root, keys, create=True)
                existing = None
                try:
                    existing = parent[k] if isinstance(k, str) and isinstance(parent, dict) else parent[k] if isinstance(parent, list) else None
                except Exception:
                    existing = None
                if isinstance(existing, dict) and isinstance(o.value, dict):
                    _set_at(parent, k, _deep_merge(existing, o.value))
                else:
                    _set_at(parent, k, copy.deepcopy(o.value))
            elif o.op == "delete":
                parent, k = _get_parent(root, keys, create=False)
                _del_at(parent, k)
            elif o.op in ("append", "extend", "insert"):
                parent, k = _get_parent(root, keys, create=True)
                container = None
                if isinstance(k, int):
                    fail(f"List ops not supported at index path: {o.path}")
                    continue
                if not isinstance(parent, dict):
                    fail(f"Expected dict at parent for list op at {o.path}")
                    continue
                if k not in parent or parent[k] is None:
                    parent[k] = []
                container = parent[k]
                if not isinstance(container, list):
                    fail(f"Expected list at {o.path}, got {type(container).__name__}")
                    continue
                if o.op == "append":
                    container.append(copy.deepcopy(o.value))
                elif o.op == "extend":
                    if not isinstance(o.value, Sequence) or isinstance(o.value, (str, bytes, dict)):
                        fail(f"extend value must be a sequence at {o.path}")
                        continue
                    container.extend(copy.deepcopy(list(o.value)))
                else:  # insert
                    idx = val = None
                    v = o.value
                    if isinstance(v, Mapping) and "index" in v:
                        idx, val = v.get("index"), v.get("value")
                    elif isinstance(v, (list, tuple)) and len(v) == 2:
                        idx, val = v[0], v[1]
                    else:
                        fail(f"insert value must be {{'index': int, 'value': any}} or (idx, val) at {o.path}")
                        continue
                    if not isinstance(idx, int):
                        fail(f"insert index must be int at {o.path}")
                        continue
                    if idx < 0:
                        idx = max(0, len(container) + idx)
                    if idx > len(container):
                        idx = len(container)
                    container.insert(idx, copy.deepcopy(val))
            else:
                fail(f"Unknown op {o.op!r} for path {o.path!r}")
        except OverrideApplyError:
            if strict:
                raise
        except Exception as e:
            if strict:
                raise OverrideApplyError(f"Failed applying op={o.op!r} path={o.path!r}: {e}") from e
    return root


def apply_overrides_copy(target: Any, overrides: Any, *, strict: bool = True) -> Any:
    return apply_overrides(copy.deepcopy(target), overrides, strict=strict)
