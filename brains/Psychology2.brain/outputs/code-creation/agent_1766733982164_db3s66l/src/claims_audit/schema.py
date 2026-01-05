from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

def _get_base_model():
    try:
        from pydantic import BaseModel  # type: ignore
        from pydantic import Field  # type: ignore

        class _B(BaseModel):
            model_config = {"extra": "forbid", "frozen": True}

        return _B, Field
    except Exception:
        from dataclasses import dataclass, field

        class _B:
            pass

        def Field(default=None, default_factory=None, description: str = ""):
            if default_factory is not None:
                return field(default_factory=default_factory, metadata={"description": description})
            return field(default=default, metadata={"description": description})

        return _B, Field


BaseModel, Field = _get_base_model()

class ClaimLabel(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    INSUFFICIENT = "insufficient"


LABEL_DEFINITIONS: Dict[str, Dict[str, str]] = {
    ClaimLabel.SUPPORTED.value: {
        "description": "Claim is entailed by the reference corpus evidence; no material contradictions in retrieved evidence.",
        "decision_rule": "Use when evidence directly supports the atomic proposition under stated qualifiers/timeframe/modality.",
    },
    ClaimLabel.UNSUPPORTED.value: {
        "description": "Claim is contradicted by the reference corpus evidence.",
        "decision_rule": "Use when evidence directly refutes the atomic proposition (including negation or incompatible quantities/dates).",
    },
    ClaimLabel.INSUFFICIENT.value: {
        "description": "Reference corpus lacks enough evidence to support or refute the claim.",
        "decision_rule": "Use when evidence is missing, irrelevant, ambiguous, or only weakly related.",
    },
}

class Modality(str, Enum):
    ASSERTED = "asserted"
    NEGATED = "negated"
    UNCERTAIN = "uncertain"
    CONDITIONAL = "conditional" 

class Timeframe(BaseModel):
    start: Optional[str] = Field(default=None, description="ISO date/datetime or coarse time string (e.g., '2020', 'Q1 2022').")
    end: Optional[str] = Field(default=None, description="ISO date/datetime or coarse time string.")

    def as_tuple(self) -> Tuple[Optional[str], Optional[str]]:
        return (self.start, self.end)

class AtomicClaim(BaseModel):
    claim_id: str = Field(description="Stable identifier for this atomic claim.")
    text: str = Field(description="Original claim surface form (as stated).")

    subject: str = Field(description="Entity/topic the claim is about.")
    predicate: str = Field(description="Relation/attribute being asserted.")
    object: str = Field(description="Value/target of the predicate (entity, quantity, or descriptor).")

    qualifiers: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional key/value qualifiers (e.g., location, population, unit, comparator, scope).",
    )
    timeframe: Optional[Timeframe] = Field(default=None, description="Optional temporal scope for the claim.")
    modality: Modality = Field(default=Modality.ASSERTED, description="Assertion mode (e.g., negated/uncertain).")

    normalization: Dict[str, Any] = Field(
        default_factory=dict,
        description="Normalization artifacts (e.g., canonical entities, units, numeric parsing, casing).",
    )

    def triple(self) -> Tuple[str, str, str]:
        return (self.subject, self.predicate, self.object)

    def key(self) -> str:
        import json

        tf = self.timeframe.as_tuple() if self.timeframe else (None, None)
        q = tuple(sorted((str(k), json.dumps(v, sort_keys=True)) for k, v in self.qualifiers.items()))
        n = tuple(sorted((str(k), json.dumps(v, sort_keys=True)) for k, v in self.normalization.items()))
        return json.dumps(
            {"s": self.subject, "p": self.predicate, "o": self.object, "q": q, "t": tf, "m": self.modality.value, "n": n},
            sort_keys=True,
        )

    @staticmethod
    def minimal(
        claim_id: str,
        text: str,
        subject: str,
        predicate: str,
        object: str,
        *,
        qualifiers: Optional[Dict[str, Any]] = None,
        timeframe: Optional[Timeframe] = None,
        modality: Modality = Modality.ASSERTED,
        normalization: Optional[Dict[str, Any]] = None,
    ) -> "AtomicClaim":
        return AtomicClaim(
            claim_id=claim_id,
            text=text,
            subject=subject,
            predicate=predicate,
            object=object,
            qualifiers=qualifiers or {},
            timeframe=timeframe,
            modality=modality,
            normalization=normalization or {},
        )

class ClaimAuditResult(BaseModel):
    claim_id: str = Field(description="AtomicClaim.claim_id")
    label: ClaimLabel = Field(description="supported/unsupported/insufficient")
    rationale: Optional[str] = Field(default=None, description="Short justification for the label.")
    evidence_doc_ids: List[str] = Field(default_factory=list, description="Reference document IDs used.")
    evidence_spans: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Machine-readable evidence spans (doc_id, start/end offsets, quote, metadata).",
    )
