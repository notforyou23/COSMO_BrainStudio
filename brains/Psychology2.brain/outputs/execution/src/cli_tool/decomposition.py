from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


TraceT = Union[List[Dict[str, Any]], "DecisionTrace"]


@dataclass(frozen=True)
class DecompositionResult:
    enabled: bool
    input_claim: str
    claims: List[str]
    steps: List[Dict[str, Any]]


class DecisionTrace:
    """Minimal trace collector with stable, JSON-serializable event dictionaries."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def emit(self, event: Dict[str, Any]) -> None:
        self.events.append(event)

    def as_list(self) -> List[Dict[str, Any]]:
        return list(self.events)
_WS_RE = re.compile(r"\s+")
_SPLIT_RE = re.compile(
    r"\s*(?:;|\.|\n+|\band\b|\bthen\b|\bbut\b|\bwhich\b|\bthat\b)\s+",
    flags=re.IGNORECASE,
)


def _normalize_claim(text: str) -> str:
    t = text.strip()
    t = _WS_RE.sub(" ", t)
    t = t.strip(" \t\r\n\"'“”‘’`.,;:-")
    return t


def _stable_dedupe(items: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for it in items:
        k = it.casefold()
        if not it or k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def _emit(trace: Optional[TraceT], event: Dict[str, Any]) -> None:
    if trace is None:
        return
    if hasattr(trace, "emit") and callable(getattr(trace, "emit")):
        trace.emit(event)  # type: ignore[call-arg]
        return
    if isinstance(trace, list):
        trace.append(event)
        return
def decompose_claim(
    claim: str,
    *,
    enabled: bool,
    trace: Optional[TraceT] = None,
    max_parts: int = 8,
) -> DecompositionResult:
    """Deterministically decompose a claim into sub-claims for sweep comparability.

    Behavior:
    - Always emits a single 'claim_decomposition' event with steps (even if disabled).
    - If disabled, returns the normalized claim as a single-element list.
    - If enabled, splits claim into parts using a stable heuristic and emits split steps.
    """
    raw = "" if claim is None else str(claim)
    normalized = _normalize_claim(raw)

    steps: List[Dict[str, Any]] = []
    if not enabled:
        result = DecompositionResult(
            enabled=False,
            input_claim=raw,
            claims=[normalized] if normalized else [],
            steps=[{"op": "passthrough", "input": raw, "output": normalized}],
        )
        _emit(
            trace,
            {
                "type": "claim_decomposition",
                "enabled": False,
                "input_claim": raw,
                "normalized_claim": normalized,
                "steps": result.steps,
                "output_claims": result.claims,
            },
        )
        return result

    # Split with stable regex; cap parts deterministically and record each transformation.
    initial_parts = [p for p in _SPLIT_RE.split(normalized) if p and p.strip()]
    steps.append({"op": "split", "pattern": _SPLIT_RE.pattern, "parts": initial_parts})

    cleaned_parts = [_normalize_claim(p) for p in initial_parts]
    steps.append({"op": "normalize_parts", "parts": cleaned_parts})

    deduped_parts = _stable_dedupe(cleaned_parts)
    steps.append({"op": "dedupe", "parts": deduped_parts})

    capped = deduped_parts[: max(1, int(max_parts))] if deduped_parts else []
    if len(capped) != len(deduped_parts):
        steps.append({"op": "cap", "max_parts": int(max_parts), "parts": capped})

    result = DecompositionResult(
        enabled=True,
        input_claim=raw,
        claims=capped,
        steps=steps,
    )
    _emit(
        trace,
        {
            "type": "claim_decomposition",
            "enabled": True,
            "input_claim": raw,
            "normalized_claim": normalized,
            "steps": steps,
            "output_claims": capped,
        },
    )
    return result
def maybe_decompose_claim(
    claim: str,
    *,
    enable_decomposition: bool,
    decision_trace: Optional[TraceT] = None,
    max_parts: int = 8,
) -> List[str]:
    """Convenience wrapper returning only the decomposed claims list."""
    return decompose_claim(
        claim,
        enabled=bool(enable_decomposition),
        trace=decision_trace,
        max_parts=max_parts,
    ).claims
