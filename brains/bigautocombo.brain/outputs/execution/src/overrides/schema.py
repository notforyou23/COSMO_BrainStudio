from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union


__all__ = [
    "OverrideValidationError",
    "OverrideOp",
    "SCHEMA",
    "parse_path",
    "normalize_overrides_doc",
    "validate_overrides_doc",
]


class OverrideValidationError(ValueError):
    def __init__(self, message: str, *, where: str = "") -> None:
        super().__init__(f"{where}: {message}" if where else message)
        self.where = where
        self.message = message


PathToken = Union[str, int]
PathSpec = Union[str, Sequence[PathToken]]
@dataclass(frozen=True)
class OverrideOp:
    op: str
    path: Tuple[PathToken, ...]
    value: Any = None


_ALLOWED_OPS = {"set", "delete", "merge", "append", "extend"}

SCHEMA: Dict[str, Any] = {
    "version": {"type": "int", "default": 1, "min": 1, "description": "Overrides document version."},
    "overrides": {
        "type": "list",
        "description": "Ordered list of override operations applied in sequence.",
        "items": {
            "op": {"type": "str", "enum": sorted(_ALLOWED_OPS)},
            "path": {"type": "path", "description": "Target location; string or list of keys/indices."},
            "value": {"type": "any", "optional": True, "description": "Operation payload (when required)."},
        },
    },
}
def _err(where: str, msg: str) -> OverrideValidationError:
    return OverrideValidationError(msg, where=where)


def parse_path(path: PathSpec, *, where: str = "path") -> Tuple[PathToken, ...]:
    if isinstance(path, (list, tuple)):
        out: List[PathToken] = []
        for i, tok in enumerate(path):
            w = f"{where}[{i}]"
            if isinstance(tok, bool) or tok is None:
                raise _err(w, "path token must be str or int")
            if isinstance(tok, int):
                if tok < 0:
                    raise _err(w, "list index must be >= 0")
                out.append(tok)
            elif isinstance(tok, str):
                if tok == "":
                    raise _err(w, "path token must be non-empty")
                out.append(tok)
            else:
                raise _err(w, "path token must be str or int")
        return tuple(out)

    if not isinstance(path, str) or path.strip() == "":
        raise _err(where, "path must be a non-empty string or a list of tokens")

    s = path.strip()
    if s.startswith("/"):
        parts = [p for p in s.split("/")[1:] if p != ""]
        out2: List[PathToken] = []
        for p in parts:
            p = p.replace("~1", "/").replace("~0", "~")
            if p.isdigit():
                out2.append(int(p))
            else:
                out2.append(p)
        return tuple(out2)

    out3: List[PathToken] = []
    i = 0
    buf: List[str] = []
    def flush_buf() -> None:
        nonlocal buf
        if buf:
            tok = "".join(buf).strip()
            if tok == "":
                raise _err(where, "invalid empty path segment")
            out3.append(tok)
            buf = []

    while i < len(s):
        ch = s[i]
        if ch == ".":
            flush_buf()
            i += 1
            continue
        if ch == "[":
            flush_buf()
            j = s.find("]", i + 1)
            if j == -1:
                raise _err(where, "unclosed '[' in path")
            inner = s[i + 1 : j].strip()
            if inner == "" or not inner.isdigit():
                raise _err(where, "bracket segment must be a non-negative integer index")
            out3.append(int(inner))
            i = j + 1
            continue
        buf.append(ch)
        i += 1
    flush_buf()
    return tuple(out3)
def _require_mapping(x: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(x, Mapping):
        raise _err(where, "must be a mapping/object")
    return x


def _require_list(x: Any, where: str) -> List[Any]:
    if not isinstance(x, list):
        raise _err(where, "must be a list")
    return x


def _require_str(x: Any, where: str) -> str:
    if not isinstance(x, str) or x.strip() == "":
        raise _err(where, "must be a non-empty string")
    return x


def normalize_overrides_doc(doc: Any) -> Dict[str, Any]:
    m = _require_mapping(doc, "doc")
    out: Dict[str, Any] = dict(m)
    if "version" not in out or out["version"] is None:
        out["version"] = SCHEMA["version"]["default"]
    if "overrides" not in out or out["overrides"] is None:
        out["overrides"] = []
    return out


def validate_overrides_doc(doc: Any) -> Tuple[int, List[OverrideOp]]:
    d = normalize_overrides_doc(doc)
    v = d.get("version")
    if isinstance(v, bool) or not isinstance(v, int):
        raise _err("version", "must be an integer")
    if v < int(SCHEMA["version"]["min"]):
        raise _err("version", f"must be >= {SCHEMA['version']['min']}")
    ops_raw = _require_list(d.get("overrides"), "overrides")
    ops: List[OverrideOp] = []
    for idx, item in enumerate(ops_raw):
        w = f"overrides[{idx}]"
        im = _require_mapping(item, w)
        op = _require_str(im.get("op"), f"{w}.op")
        if op not in _ALLOWED_OPS:
            raise _err(f"{w}.op", f"unsupported op '{op}' (allowed: {sorted(_ALLOWED_OPS)})")
        path = parse_path(im.get("path"), where=f"{w}.path")
        needs_value = op in {"set", "merge", "append", "extend"}
        if needs_value and "value" not in im:
            raise _err(f"{w}.value", f"missing required value for op '{op}'")
        if not needs_value and "value" in im and im.get("value") is not None:
            raise _err(f"{w}.value", f"value not permitted for op '{op}'")
        value = im.get("value", None)
        if op in {"append", "extend"} and len(path) == 0:
            raise _err(f"{w}.path", f"op '{op}' requires a non-empty path")
        ops.append(OverrideOp(op=op, path=path, value=value))
    return v, ops
