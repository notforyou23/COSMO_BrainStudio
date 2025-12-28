"""atomic_claims.rubric

Defines the Supported / Contradicted / Insufficient (SCI) labeling rubric for atomic
claims and provides lightweight programmatic checks for label consistency.

Atomic claim (informal): a minimal, self-contained proposition with explicit scope
(e.g., time, jurisdiction, population, modality). Labels are assigned *relative to a
reference corpus* and the evidence provided for the claim.

Label meanings:
- supported: evidence clearly entails the claim within its stated scope.
- contradicted: evidence clearly entails the negation/incompatibility with the claim's scope.
- insufficient: evidence does not resolve the claim (missing, vague, out-of-scope, mixed/ambiguous).

Evidence expectations (minimal):
- Provide at least one evidence item with provenance (source identifier or quote/span).
- Evidence items should be marked with stance: support | contradict | neutral.

Decision rules (priority order):
1) If there is at least one in-scope, provenance-backed SUPPORT and no in-scope CONTRADICT => supported.
2) If there is at least one in-scope, provenance-backed CONTRADICT and no in-scope SUPPORT => contradicted.
3) Otherwise => insufficient (includes: no evidence, only neutral, out-of-scope, low-quality,
   or both support and contradict present, or only partial support for a quantified/absolute claim).

Edge-case guidance:
- Partial/hedged evidence vs absolute claim (e.g., "always", "all", "never") => insufficient unless evidence matches.
- Different scope (time/population/definition) => treat as out-of-scope; usually insufficient.
- Conflicting evidence (both support and contradict) => insufficient (borderline-confidence slice).
- Tautologies/opinions/normative statements => usually insufficient unless corpus defines an evaluative ground truth.
- Numerical claims: small rounding differences are not contradiction unless they make the propositions incompatible.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


class Label(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"

    @classmethod
    def coerce(cls, value: Union["Label", str]) -> "Label":
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError(f"label must be a str or Label, got {type(value).__name__}")
        v = value.strip().lower()
        for m in cls:
            if v == m.value:
                return m
        raise ValueError(f"unknown label: {value!r}")


_STANCES = {"support", "contradict", "neutral"}
@dataclass(frozen=True)
class EvidenceSignal:
    """A distilled evidence signal used for rubric checks.

    stance: support | contradict | neutral
    in_scope: whether the evidence matches the claim's scope as written
    has_provenance: whether the evidence is traceable (citation id, URL, quote/span, etc.)
    """

    stance: str
    in_scope: bool = True
    has_provenance: bool = True

    def __post_init__(self) -> None:
        st = (self.stance or "").strip().lower()
        if st not in _STANCES:
            raise ValueError(f"invalid stance: {self.stance!r} (expected one of {sorted(_STANCES)})")
        object.__setattr__(self, "stance", st)


def decide_label(signals: Sequence[EvidenceSignal]) -> Label:
    """Apply the rubric's decision rules to a set of evidence signals."""
    sup = any(s.in_scope and s.has_provenance and s.stance == "support" for s in signals)
    con = any(s.in_scope and s.has_provenance and s.stance == "contradict" for s in signals)
    if sup and not con:
        return Label.SUPPORTED
    if con and not sup:
        return Label.CONTRADICTED
    return Label.INSUFFICIENT


def check_label_consistency(
    label: Union[Label, str],
    signals: Sequence[EvidenceSignal],
    *,
    allow_empty_for_insufficient: bool = True,
) -> None:
    """Raise ValueError if (label, evidence) violates the rubric.

    This is a *consistency* check, not a full verifier of factual correctness.
    """
    lab = Label.coerce(label)
    inferred = decide_label(signals)

    if lab in (Label.SUPPORTED, Label.CONTRADICTED):
        if not signals:
            raise ValueError(f"{lab.value} requires evidence signals (got empty).")
        if any(not s.has_provenance for s in signals if s.stance in ("support", "contradict")):
            raise ValueError(f"{lab.value} requires provenance-backed support/contradict signals.")
        if all((s.stance == "neutral") or (not s.in_scope) for s in signals):
            raise ValueError(f"{lab.value} cannot be assigned with only neutral/out-of-scope evidence.")
        if inferred != lab:
            raise ValueError(f"label {lab.value!r} conflicts with inferred {inferred.value!r} from signals.")

    if lab == Label.INSUFFICIENT:
        if not allow_empty_for_insufficient and not signals:
            raise ValueError("insufficient label disallows empty evidence by configuration.")
        # If evidence cleanly implies support/contradict, 'insufficient' is inconsistent.
        if signals and inferred in (Label.SUPPORTED, Label.CONTRADICTED):
            raise ValueError(
                f"label 'insufficient' conflicts with inferred {inferred.value!r}; "
                "use supported/contradicted or mark evidence as out-of-scope/low-provenance."
            )


def signals_from_evidence_items(items: Iterable[Mapping[str, Any]]) -> List[EvidenceSignal]:
    """Convert a list of evidence dicts into EvidenceSignal objects.

    Expected keys (case-insensitive):
      - stance: 'support' | 'contradict' | 'neutral'
      - in_scope: bool (default True)
      - has_provenance: bool (default True)
    Extra keys are ignored.
    """
    out: List[EvidenceSignal] = []
    for it in items:
        if not isinstance(it, Mapping):
            raise TypeError(f"evidence item must be a mapping, got {type(it).__name__}")
        stance = it.get("stance", it.get("Stance", it.get("STANCe")))
        in_scope = bool(it.get("in_scope", it.get("inScope", True)))
        has_prov = bool(it.get("has_provenance", it.get("provenance", True)))
        out.append(EvidenceSignal(str(stance), in_scope=in_scope, has_provenance=has_prov))
    return out


def check_annotation_dict(annotation: Mapping[str, Any]) -> None:
    """Validate a minimal annotation dict.

    Required:
      - 'label': supported|contradicted|insufficient
      - 'evidence': list[dict] (may be empty only for insufficient)
    """
    if "label" not in annotation:
        raise ValueError("annotation missing required key: 'label'")
    if "evidence" not in annotation:
        raise ValueError("annotation missing required key: 'evidence'")
    evidence = annotation["evidence"]
    if not isinstance(evidence, list):
        raise TypeError(f"annotation['evidence'] must be a list, got {type(evidence).__name__}")
    sigs = signals_from_evidence_items(evidence)
    allow_empty = Label.coerce(annotation["label"]) == Label.INSUFFICIENT
    check_label_consistency(annotation["label"], sigs, allow_empty_for_insufficient=allow_empty)
