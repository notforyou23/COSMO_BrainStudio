"""Verification logic for retrieve-then-verify baseline.

Implements quote-attribution checks and a minimal support/contradict/insufficient
decision with an abstain rule driven by evidence quality and calibration thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from .types import VerificationDecision as _TDDecision  # type: ignore
except Exception:  # pragma: no cover
    _TDDecision = None  # type: ignore


@dataclass
class Decision:
    label: str
    confidence: float
    abstained: bool
    evidence_id: Optional[str] = None
    quote_ok: Optional[bool] = None
    rationale: str = ""


def _get(x: Any, k: str, default=None):
    if x is None:
        return default
    if isinstance(x, dict):
        return x.get(k, default)
    return getattr(x, k, default)


_WS = re.compile(r"\s+")
_PUN = re.compile(r"[^a-z0-9\s]+")


def normalize(s: str) -> str:
    s = (s or "").lower()
    s = _PUN.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def _tokens(s: str) -> List[str]:
    s = normalize(s)
    return [t for t in s.split(" ") if t]


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def _best_evidence_text(e: Any) -> Tuple[str, Optional[str]]:
    if e is None:
        return "", None
    return (_get(e, "text", "") or _get(e, "chunk", "") or _get(e, "content", "") or ""), (
        _get(e, "id", None) or _get(e, "chunk_id", None) or _get(e, "evidence_id", None)
    )


def quote_attribution_quality(claim: Any, evidence_text: str) -> Dict[str, float]:
    quote = (_get(claim, "quote", None) or _get(claim, "quoted_text", None) or "").strip()
    speaker = (_get(claim, "speaker", None) or _get(claim, "author", None) or "").strip()
    et = evidence_text or ""
    if not quote:
        return {"quote_match": 1.0, "attrib_match": 1.0, "quality": 1.0}
    nq, ne = normalize(quote), normalize(et)
    quote_match = 1.0 if (nq and nq in ne) else 0.0
    if not quote_match:
        qtoks = _tokens(quote)
        etoks = _tokens(et)
        quote_match = min(1.0, 2.0 * jaccard(qtoks, etoks)) if qtoks and etoks else 0.0
    attrib_match = 1.0
    if speaker:
        ns = normalize(speaker)
        if ns and ns in ne:
            attrib_match = 1.0
        else:
            stoks = set(_tokens(speaker))
            attrib_match = 1.0 if (stoks and stoks.issubset(set(_tokens(et)))) else 0.0
    quality = min(quote_match, attrib_match)
    return {"quote_match": float(quote_match), "attrib_match": float(attrib_match), "quality": float(quality)}


_NEG = {"not", "no", "never", "none", "neither", "without", "deny", "denies", "denied", "refute", "refutes", "refuted", "false", "incorrect"}


def proposition_overlap(claim: Any, evidence_text: str) -> float:
    fields = []
    for k in ("subject", "entity", "who", "topic", "object", "value", "where", "when", "relation", "predicate"):
        v = _get(claim, k, None)
        if isinstance(v, str) and v.strip():
            fields.append(v)
    text = " ".join(fields) if fields else (_get(claim, "text", "") or _get(claim, "claim", "") or "")
    ctoks = _tokens(text)
    etoks = _tokens(evidence_text)
    return jaccard(ctoks, etoks) if ctoks and etoks else 0.0


def contradiction_signal(claim: Any, evidence_text: str) -> float:
    ctext = _get(claim, "text", "") or _get(claim, "claim", "") or ""
    key = _tokens(_get(claim, "object", "") or _get(claim, "value", "") or ctext)
    if not key:
        key = _tokens(ctext)
    etoks = _tokens(evidence_text)
    if not key or not etoks:
        return 0.0
    has_key = bool(set(key) & set(etoks))
    has_neg = bool(_NEG & set(etoks))
    return 1.0 if (has_key and has_neg) else 0.0


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def score_evidence(claim: Any, evidence_text: str) -> Dict[str, float]:
    qa = quote_attribution_quality(claim, evidence_text)
    ov = proposition_overlap(claim, evidence_text)
    cs = contradiction_signal(claim, evidence_text)
    has_quote = bool((_get(claim, "quote", None) or _get(claim, "quoted_text", None) or "").strip())
    # Confidence blends proposition overlap with quote/attribution quality when relevant.
    q = qa["quality"] if has_quote else 1.0
    raw = 2.2 * ov + 1.6 * q - 1.0 * cs - 0.7
    conf = _sigmoid(raw)
    quality = min(1.0, 0.5 * ov + 0.5 * q)
    return {"overlap": float(ov), "contrad": float(cs), "quote_quality": float(q), "quality": float(quality), "confidence": float(conf)}


def decide_label(scores: Dict[str, float]) -> str:
    if scores["contrad"] >= 1.0 and scores["overlap"] >= 0.12:
        return "CONTRADICT"
    if scores["overlap"] >= 0.18 and scores["quote_quality"] >= 0.6:
        return "SUPPORT"
    return "INSUFFICIENT"


def verify_claim(
    claim: Any,
    evidences: List[Any],
    *,
    risk_tier: str = "medium",
    thresholds: Optional[Dict[str, float]] = None,
    min_evidence_quality: float = 0.45,
) -> Any:
    """Return a VerificationDecision-like object/dict with abstain rule.

    thresholds: per-tier minimum confidence required to accept SUPPORT/CONTRADICT.
    """
    thresholds = thresholds or {"low": 0.55, "medium": 0.7, "high": 0.82}
    thr = float(thresholds.get(risk_tier, thresholds.get("medium", 0.7)))
    best = None
    best_eid = None
    best_text = ""
    for e in (evidences or []):
        txt, eid = _best_evidence_text(e)
        sc = score_evidence(claim, txt)
        if best is None or sc["confidence"] > best["confidence"]:
            best, best_eid, best_text = sc, eid, txt
    if best is None:
        best = {"overlap": 0.0, "contrad": 0.0, "quote_quality": 0.0, "quality": 0.0, "confidence": 0.0}
    label = decide_label(best)
    has_quote = bool((_get(claim, "quote", None) or _get(claim, "quoted_text", None) or "").strip())
    quote_ok = None if not has_quote else (best["quote_quality"] >= 0.6)
    abstain = (best["quality"] < float(min_evidence_quality)) or (best["confidence"] < thr) or (has_quote and not quote_ok)
    out_label = "ABSTAIN" if abstain else label
    rationale = f"label={label} conf={best['confidence']:.3f} quality={best['quality']:.3f} overlap={best['overlap']:.3f} quoteQ={best['quote_quality']:.3f} contrad={best['contrad']:.1f} thr={thr:.2f}"
    dec = Decision(out_label, float(best["confidence"]), bool(abstain), best_eid, quote_ok, rationale)
    if _TDDecision is not None:  # type: ignore
        try:
            return _TDDecision(  # type: ignore
                label=dec.label,
                confidence=dec.confidence,
                abstained=dec.abstained,
                evidence_id=dec.evidence_id,
                quote_ok=dec.quote_ok,
                rationale=dec.rationale,
            )
        except Exception:
            pass
    return {
        "label": dec.label,
        "confidence": dec.confidence,
        "abstained": dec.abstained,
        "evidence_id": dec.evidence_id,
        "quote_ok": dec.quote_ok,
        "rationale": dec.rationale,
        "best_evidence_text": best_text,
    }
