from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


class GoldLabel(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class EvidenceSpan:
    doc_id: str
    start: int
    end: int
    text: Optional[str] = None

    def as_tuple(self) -> Tuple[str, int, int]:
        return (self.doc_id, self.start, self.end)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"doc_id": self.doc_id, "start": self.start, "end": self.end}
        if self.text is not None:
            d["text"] = self.text
        return d

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "EvidenceSpan":
        return EvidenceSpan(
            doc_id=str(d["doc_id"]),
            start=int(d["start"]),
            end=int(d["end"]),
            text=None if d.get("text") is None else str(d.get("text")),
        )

    def validate(self, doc_text: Optional[str] = None) -> None:
        if self.start < 0 or self.end < 0:
            raise ValueError("EvidenceSpan offsets must be non-negative")
        if self.end <= self.start:
            raise ValueError("EvidenceSpan end must be > start")
        if doc_text is not None:
            if self.end > len(doc_text):
                raise ValueError("EvidenceSpan end exceeds document length")
            if self.text is not None:
                extracted = doc_text[self.start : self.end]
                if extracted != self.text:
                    raise ValueError("EvidenceSpan text does not match provided document text at offsets")


@dataclass
class GoldAnnotation:
    claim_id: str
    label: GoldLabel
    evidence: List[EvidenceSpan] = field(default_factory=list)
    confidence: Optional[float] = None  # annotator confidence in [0,1]
    rationale: Optional[str] = None
    schema_version: str = "gold.v1"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "claim_id": self.claim_id,
            "label": self.label.value,
            "evidence": [e.to_dict() for e in self.evidence],
        }
        if self.confidence is not None:
            d["confidence"] = float(self.confidence)
        if self.rationale is not None:
            d["rationale"] = str(self.rationale)
        return d

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "GoldAnnotation":
        ev = [EvidenceSpan.from_dict(x) for x in (d.get("evidence") or [])]
        return GoldAnnotation(
            schema_version=str(d.get("schema_version") or "gold.v1"),
            claim_id=str(d["claim_id"]),
            label=GoldLabel(str(d["label"])),
            evidence=ev,
            confidence=None if d.get("confidence") is None else float(d["confidence"]),
            rationale=None if d.get("rationale") is None else str(d.get("rationale")),
        )

    def validate(
        self,
        doc_texts: Optional[Mapping[str, str]] = None,
        allow_insufficient_with_evidence: bool = False,
    ) -> None:
        if not self.claim_id:
            raise ValueError("claim_id is required")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")
        if self.label in (GoldLabel.SUPPORTED, GoldLabel.CONTRADICTED) and not self.evidence:
            raise ValueError(f"{self.label.value} annotations must include at least one evidence span")
        if self.label == GoldLabel.INSUFFICIENT and self.evidence and not allow_insufficient_with_evidence:
            raise ValueError("insufficient annotations must not include evidence spans")
        seen = set()
        for e in self.evidence:
            if e.as_tuple() in seen:
                raise ValueError("duplicate evidence span detected")
            seen.add(e.as_tuple())
            e.validate(None if doc_texts is None else doc_texts.get(e.doc_id))


@dataclass(frozen=True)
class BorderlineSliceConstraints:
    min_confidence: float = 0.4
    max_confidence: float = 0.7
    require_confidence: bool = True
    max_evidence_spans: int = 2
    require_single_document: bool = True
    max_span_chars: int = 400
    allow_insufficient_with_evidence: bool = False

    def validate(self, ann: GoldAnnotation, doc_texts: Optional[Mapping[str, str]] = None) -> None:
        ann.validate(doc_texts=doc_texts, allow_insufficient_with_evidence=self.allow_insufficient_with_evidence)
        if self.require_confidence:
            if ann.confidence is None:
                raise ValueError("borderline slice requires confidence")
            if not (self.min_confidence <= ann.confidence <= self.max_confidence):
                raise ValueError("confidence outside borderline range")
        if len(ann.evidence) > self.max_evidence_spans:
            raise ValueError("too many evidence spans for borderline slice")
        if self.require_single_document and ann.evidence:
            doc_ids = {e.doc_id for e in ann.evidence}
            if len(doc_ids) != 1:
                raise ValueError("borderline slice requires evidence from a single document")
        for e in ann.evidence:
            span_len = e.end - e.start
            if span_len > self.max_span_chars:
                raise ValueError("evidence span too long for borderline slice")


def validate_gold_set(
    anns: Sequence[GoldAnnotation],
    *,
    doc_texts: Optional[Mapping[str, str]] = None,
    constraints: Optional[BorderlineSliceConstraints] = None,
) -> None:
    seen_claims = set()
    for ann in anns:
        if ann.claim_id in seen_claims:
            raise ValueError(f"duplicate claim_id: {ann.claim_id}")
        seen_claims.add(ann.claim_id)
        if constraints is None:
            ann.validate(doc_texts=doc_texts)
        else:
            constraints.validate(ann, doc_texts=doc_texts)


def dumps_jsonl(anns: Iterable[GoldAnnotation]) -> str:
    return "\n".join(json.dumps(a.to_dict(), ensure_ascii=False, sort_keys=True) for a in anns) + ("\n" if True else "")


def loads_jsonl(text: str) -> List[GoldAnnotation]:
    out: List[GoldAnnotation] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(GoldAnnotation.from_dict(json.loads(line)))
    return out
