"""atomic_claims package entry point.

Exports the public atomic-claim schema objects and small dataset utilities.
The module is designed to be import-safe even if optional submodules
(schema/rubric) are not yet present.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union
import json
__all__ = [
    "Label",
    "AtomicClaim",
    "ClaimExample",
    "load_jsonl",
    "dump_jsonl",
    "load_dataset",
    "save_dataset",
]

__version__ = "0.1.0"
JSON = Dict[str, Any]
class Label(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"

    @classmethod
    def coerce(cls, value: Union["Label", str]) -> "Label":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).strip().lower())
        except Exception as e:
            raise ValueError(f"Invalid label: {value!r}") from e
@dataclass(frozen=True)
class AtomicClaim:
    """Minimal, self-contained proposition with explicit scope and provenance needs."""

    subject: str
    predicate: str
    obj: Optional[str] = None
    scope: Optional[str] = None
    provenance_required: Tuple[str, ...] = ()
    qualifiers: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> JSON:
        d = asdict(self)
        d["provenance_required"] = list(self.provenance_required)
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "AtomicClaim":
        return cls(
            subject=str(d.get("subject", "")),
            predicate=str(d.get("predicate", "")),
            obj=(None if d.get("obj", None) is None else str(d.get("obj"))),
            scope=(None if d.get("scope", None) is None else str(d.get("scope"))),
            provenance_required=tuple(d.get("provenance_required", ()) or ()),
            qualifiers=dict(d.get("qualifiers", {}) or {}),
        )
@dataclass(frozen=True)
class ClaimExample:
    """Gold-labeled example linking an atomic claim to a reference context."""

    claim_id: str
    claim: AtomicClaim
    reference_id: str
    label: Label
    rationale: Optional[str] = None
    evidence: Tuple[str, ...] = ()
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> JSON:
        return {
            "claim_id": self.claim_id,
            "claim": self.claim.to_dict(),
            "reference_id": self.reference_id,
            "label": self.label.value,
            "rationale": self.rationale,
            "evidence": list(self.evidence),
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ClaimExample":
        return cls(
            claim_id=str(d.get("claim_id", "")),
            claim=AtomicClaim.from_dict(d.get("claim", {}) or {}),
            reference_id=str(d.get("reference_id", "")),
            label=Label.coerce(d.get("label", "")),
            rationale=(None if d.get("rationale", None) is None else str(d.get("rationale"))),
            evidence=tuple(d.get("evidence", ()) or ()),
            meta=dict(d.get("meta", {}) or {}),
        )
def load_jsonl(path: Union[str, Path]) -> List[JSON]:
    p = Path(path)
    rows: List[JSON] = []
    with p.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                continue
            try:
                rows.append(json.loads(s))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_no} of {p}") from e
    return rows


def dump_jsonl(path: Union[str, Path], rows: Iterable[Mapping[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True))
            f.write("\n")
def load_dataset(path: Union[str, Path]) -> List[ClaimExample]:
    return [ClaimExample.from_dict(r) for r in load_jsonl(path)]


def save_dataset(path: Union[str, Path], examples: Sequence[ClaimExample]) -> None:
    dump_jsonl(path, (ex.to_dict() for ex in examples))
# Prefer dedicated submodules when available; fall back to local definitions above.
try:  # pragma: no cover
    from .schema import AtomicClaim as AtomicClaim  # type: ignore
except Exception:
    pass

try:  # pragma: no cover
    from .rubric import Label as Label  # type: ignore
except Exception:
    pass
