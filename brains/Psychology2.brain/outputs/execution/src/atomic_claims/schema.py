from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional
import json

__all__ = [
    "ValidationError",
    "ProvenanceRequirement",
    "AtomicClaim",
    "validate_claim_dict",
]


class ValidationError(ValueError):
    """Raised when an AtomicClaim (or dict form) fails schema validation."""


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _as_dict(x: Any, name: str) -> Dict[str, Any]:
    if x is None:
        return {}
    if not isinstance(x, Mapping):
        raise ValidationError(f"{name} must be an object/dict")
    return dict(x)


@dataclass(frozen=True)
class ProvenanceRequirement:
    """Machine-readable provenance expectations for evaluating a claim."""

    min_sources: int = 1
    require_urls: bool = False
    require_quotes: bool = False
    allowed_source_types: Optional[List[str]] = None

    def validate(self) -> None:
        if not isinstance(self.min_sources, int) or self.min_sources < 0:
            raise ValidationError("provenance.min_sources must be an integer >= 0")
        if self.allowed_source_types is not None:
            if not isinstance(self.allowed_source_types, list) or not all(
                _is_nonempty_str(s) for s in self.allowed_source_types
            ):
                raise ValidationError("provenance.allowed_source_types must be a list of non-empty strings")

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "min_sources": self.min_sources,
            "require_urls": self.require_urls,
            "require_quotes": self.require_quotes,
        }
        if self.allowed_source_types is not None:
            d["allowed_source_types"] = list(self.allowed_source_types)
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ProvenanceRequirement":
        dd = dict(d)
        obj = cls(
            min_sources=int(dd.get("min_sources", 1)),
            require_urls=bool(dd.get("require_urls", False)),
            require_quotes=bool(dd.get("require_quotes", False)),
            allowed_source_types=dd.get("allowed_source_types"),
        )
        obj.validate()
        return obj


@dataclass
class AtomicClaim:
    """A minimal, self-contained proposition suitable for labeling.

    Fields:
      - subject: the entity being asserted about
      - predicate: the relation/action/attribute being asserted
      - object: optional target/value (use for relational predicates)
      - scope: optional constraints (time/location/population/modality/etc.)
      - provenance: requirements to consider evidence sufficient
    """

    subject: str
    predicate: str
    object: Optional[str] = None
    scope: Dict[str, Any] = field(default_factory=dict)
    provenance: ProvenanceRequirement = field(default_factory=ProvenanceRequirement)
    claim_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not _is_nonempty_str(self.subject):
            raise ValidationError("subject must be a non-empty string")
        if not _is_nonempty_str(self.predicate):
            raise ValidationError("predicate must be a non-empty string")
        if self.object is not None and not _is_nonempty_str(self.object):
            raise ValidationError("object must be a non-empty string if provided")
        self.scope = _as_dict(self.scope, "scope")
        self.metadata = _as_dict(self.metadata, "metadata")
        if self.claim_id is not None and not _is_nonempty_str(self.claim_id):
            raise ValidationError("claim_id must be a non-empty string if provided")
        if not isinstance(self.provenance, ProvenanceRequirement):
            raise ValidationError("provenance must be a ProvenanceRequirement")
        self.provenance.validate()

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        out: Dict[str, Any] = {
            "subject": self.subject.strip(),
            "predicate": self.predicate.strip(),
            "scope": dict(self.scope),
            "provenance": self.provenance.to_dict(),
            "metadata": dict(self.metadata),
        }
        if self.object is not None:
            out["object"] = self.object.strip()
        if self.claim_id is not None:
            out["claim_id"] = self.claim_id.strip()
        return out

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "AtomicClaim":
        if not isinstance(d, Mapping):
            raise ValidationError("claim must be an object/dict")
        dd = dict(d)
        prov = dd.get("provenance", {})
        obj = cls(
            subject=dd.get("subject", ""),
            predicate=dd.get("predicate", ""),
            object=dd.get("object"),
            scope=_as_dict(dd.get("scope"), "scope"),
            provenance=ProvenanceRequirement.from_dict(_as_dict(prov, "provenance")),
            claim_id=dd.get("claim_id"),
            metadata=_as_dict(dd.get("metadata"), "metadata"),
        )
        obj.validate()
        return obj

    def to_json(self, *, ensure_ascii: bool = False, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, s: str) -> "AtomicClaim":
        try:
            data = json.loads(s)
        except json.JSONDecodeError as e:
            raise ValidationError(f"invalid JSON: {e}") from e
        return cls.from_dict(data)


def validate_claim_dict(d: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate dict-form claim; returns a normalized dict suitable for storage."""
    return AtomicClaim.from_dict(d).to_dict()
