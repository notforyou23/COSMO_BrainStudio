"""Central schema/models for overrides.

These dataclasses are deliberately small and dependency-free; they provide:
- Well-typed override structures (suitable for YAML/JSON serialization).
- Validation helpers with actionable error messages.
- A stable public surface for apply/yaml modules.

An override is a list of "patch" operations applied to in-memory objects/dicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence, Union, List


PathToken = Union[str, int]
OverridePath = List[PathToken]


class OverrideOp(str, Enum):
    """Supported override operations.

    - set: assign value at path (creates dict/list nodes as needed by applier)
    - delete: remove key/index at path
    - merge: shallow-merge mapping into mapping at path
    - append: append value(s) to list at path
    """

    SET = "set"
    DELETE = "delete"
    MERGE = "merge"
    APPEND = "append"


class OverrideValidationError(ValueError):
    """Raised when an override or patch fails validation."""


def _is_int_like(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def validate_path(path: Sequence[Any], *, where: str = "path") -> OverridePath:
    """Validate and normalize an override path as a list of tokens."""
    if not isinstance(path, Sequence) or isinstance(path, (str, bytes)):
        raise OverrideValidationError(f"{where} must be a sequence of tokens (got {type(path).__name__})")
    if len(path) == 0:
        raise OverrideValidationError(f"{where} must not be empty")
    out: OverridePath = []
    for i, tok in enumerate(path):
        if isinstance(tok, str):
            if tok == "":
                raise OverrideValidationError(f"{where}[{i}] must not be empty string")
            out.append(tok)
        elif _is_int_like(tok):
            if tok < 0:
                raise OverrideValidationError(f"{where}[{i}] must be >= 0")
            out.append(int(tok))
        else:
            raise OverrideValidationError(f"{where}[{i}] must be str or int (got {type(tok).__name__})")
    return out


def validate_op(op: Any) -> OverrideOp:
    """Validate and normalize an override operation."""
    if isinstance(op, OverrideOp):
        return op
    if not isinstance(op, str):
        raise OverrideValidationError(f"op must be a string (got {type(op).__name__})")
    try:
        return OverrideOp(op)
    except Exception:
        allowed = ", ".join(o.value for o in OverrideOp)
        raise OverrideValidationError(f"unsupported op {op!r} (allowed: {allowed})") from None


def _is_mapping(x: Any) -> bool:
    return isinstance(x, Mapping)


def _is_sequence_not_str(x: Any) -> bool:
    return isinstance(x, Sequence) and not isinstance(x, (str, bytes, bytearray))


@dataclass(frozen=True, slots=True)
class OverridePatch:
    """A single override operation.

    Attributes:
        path: Sequence of keys (str) and/or list indices (int).
        op: Operation name.
        value: Payload for the operation (required for set/merge/append).
        note: Optional human-readable comment; ignored by applier.
    """

    path: OverridePath
    op: OverrideOp
    value: Any = None
    note: str | None = None

    def validate(self) -> "OverridePatch":
        p = validate_path(self.path, where="patch.path")
        o = validate_op(self.op)
        v = self.value
        if o == OverrideOp.DELETE:
            if v is not None:
                raise OverrideValidationError("patch.value must be null/omitted for op='delete'")
        elif o == OverrideOp.MERGE:
            if not _is_mapping(v):
                raise OverrideValidationError("patch.value must be a mapping for op='merge'")
        elif o == OverrideOp.APPEND:
            if v is None:
                raise OverrideValidationError("patch.value is required for op='append'")
        elif o == OverrideOp.SET:
            if v is None:
                raise OverrideValidationError("patch.value is required for op='set'")
        return OverridePatch(path=p, op=o, value=v, note=self.note)


@dataclass(frozen=True, slots=True)
class OverridesDoc:
    """A complete overrides document.

    The YAML/JSON representation is expected to be:
        version: int (default 1)
        patches: list[OverridePatch]
        meta: optional mapping for provenance, timestamps, etc.
    """

    patches: List[OverridePatch] = field(default_factory=list)
    version: int = 1
    meta: Mapping[str, Any] | None = None

    def validate(self) -> "OverridesDoc":
        if not _is_int_like(self.version) or self.version <= 0:
            raise OverrideValidationError("version must be a positive integer")
        if not isinstance(self.patches, list):
            raise OverrideValidationError("patches must be a list")
        validated: List[OverridePatch] = []
        for i, p in enumerate(self.patches):
            if not isinstance(p, OverridePatch):
                raise OverrideValidationError(f"patches[{i}] must be OverridePatch (got {type(p).__name__})")
            validated.append(p.validate())
        if self.meta is not None and not _is_mapping(self.meta):
            raise OverrideValidationError("meta must be a mapping when provided")
        return OverridesDoc(patches=validated, version=int(self.version), meta=self.meta)


def doc_from_obj(obj: Mapping[str, Any]) -> OverridesDoc:
    """Construct and validate OverridesDoc from a decoded mapping (e.g., YAML/JSON)."""
    if not _is_mapping(obj):
        raise OverrideValidationError(f"overrides document must be a mapping (got {type(obj).__name__})")
    version = obj.get("version", 1)
    meta = obj.get("meta")
    raw_patches = obj.get("patches", obj.get("overrides"))
    if raw_patches is None:
        raise OverrideValidationError("overrides document must contain 'patches' (or legacy 'overrides')")
    if not isinstance(raw_patches, list):
        raise OverrideValidationError("'patches' must be a list")
    patches: List[OverridePatch] = []
    for i, p in enumerate(raw_patches):
        if not _is_mapping(p):
            raise OverrideValidationError(f"patches[{i}] must be a mapping")
        patch = OverridePatch(
            path=validate_path(p.get("path"), where=f"patches[{i}].path"),
            op=validate_op(p.get("op")),
            value=p.get("value"),
            note=p.get("note") or p.get("comment"),
        ).validate()
        patches.append(patch)
    return OverridesDoc(patches=patches, version=version, meta=meta).validate()


def doc_to_obj(doc: OverridesDoc) -> dict[str, Any]:
    """Convert OverridesDoc to a plain JSON/YAML-serializable mapping."""
    doc = doc.validate()
    out: dict[str, Any] = {"version": doc.version, "patches": []}
    if doc.meta is not None:
        out["meta"] = dict(doc.meta)
    for p in doc.patches:
        d: dict[str, Any] = {"path": list(p.path), "op": p.op.value}
        if p.op != OverrideOp.DELETE:
            d["value"] = p.value
        if p.note:
            d["note"] = p.note
        out["patches"].append(d)
    return out
