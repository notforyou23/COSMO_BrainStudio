"""uncertainty_signals.py

Per-claim uncertainty signals with a unified interface.

Signals are designed to be model-agnostic and robust to missing metadata.
Returned values are plain Python primitives for easy JSON serialization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import math
import re


_HEDGE_RE = re.compile(r"\b(maybe|might|could|possibly|probably|likely|unclear|unsure|i\s*(am|'m)\s*not\s*sure|cannot\s*confirm|can't\s*confirm|no\s*evidence|not\s*enough\s*information)\b", re.I)
_REFUSAL_RE = re.compile(r"\b(i\s*(can('|’)t|cannot)\s*(help|comply|do\s*that)|i\s*won't|unable\s*to|not\s*able\s*to|as\s*an\s*ai)\b", re.I)
_CITATION_RE = re.compile(r"\b(source|sources|citation|cite|reference|refs?)\b", re.I)


def _safe_mean(xs: Sequence[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None and isinstance(x, (int, float)) and math.isfinite(float(x))]
    return (sum(xs) / len(xs)) if xs else None


def _safe_min(xs: Sequence[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None and isinstance(x, (int, float)) and math.isfinite(float(x))]
    return min(xs) if xs else None


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _contains_number(text: str) -> bool:
    return bool(re.search(r"\b\d+(?:[\.,]\d+)?\b", text or ""))


def _ends_question(text: str) -> bool:
    t = (text or "").strip()
    return t.endswith("?")


def _text_length(text: str) -> int:
    return len((text or "").strip())


def _hedge_rate(text: str) -> float:
    toks = _tokenize(text)
    if not toks:
        return 0.0
    matches = len(_HEDGE_RE.findall(text or ""))
    return min(1.0, matches / max(1, len(toks) / 20.0))


def _refusal_flag(text: str) -> float:
    return 1.0 if _REFUSAL_RE.search(text or "") else 0.0


def _citation_request_flag(text: str) -> float:
    return 1.0 if _CITATION_RE.search(text or "") else 0.0


def self_consistency_divergence(samples: Sequence[str]) -> Optional[float]:
    """Divergence proxy from multiple generations.

    Returns 0 when samples are very similar and approaches 1 when diverse.
    """
    ss = [s for s in (samples or []) if isinstance(s, str) and s.strip()]
    if len(ss) < 2:
        return None
    toks = [_tokenize(s) for s in ss]
    sims: List[float] = []
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            sims.append(_jaccard(toks[i], toks[j]))
    mean_sim = sum(sims) / len(sims) if sims else 1.0
    return float(max(0.0, min(1.0, 1.0 - mean_sim)))


def logprob_surrogates(token_logprobs: Optional[Sequence[float]]) -> Dict[str, Optional[float]]:
    """Compute simple logprob-based surrogates from per-token logprobs.

    Inputs are expected to be natural-log logprobs (<= 0), but any finite floats work.
    """
    lps = [float(x) for x in (token_logprobs or []) if x is not None and isinstance(x, (int, float)) and math.isfinite(float(x))]
    mean_lp = _safe_mean(lps)
    min_lp = _safe_min(lps)
    # map mean logprob to a [0,1] "risk" using a squashed transform:
    # higher logprob (less negative) -> lower risk
    risk_from_mean = None
    if mean_lp is not None:
        risk_from_mean = float(max(0.0, min(1.0, 1.0 - _sigmoid((mean_lp + 2.0) / 2.0))))
    risk_from_min = None
    if min_lp is not None:
        risk_from_min = float(max(0.0, min(1.0, 1.0 - _sigmoid((min_lp + 6.0) / 2.0))))
    return {
        "mean_token_logprob": mean_lp,
        "min_token_logprob": min_lp,
        "risk_from_mean_logprob": risk_from_mean,
        "risk_from_min_logprob": risk_from_min,
        "n_token_logprobs": len(lps),
    }


@dataclass(frozen=True)
class ClaimSignals:
    claim_id: Optional[str]
    claim_text: str
    signals: Dict[str, Any]


class UncertaintySignalComputer:
    """Unified interface to compute per-claim uncertainty signals.

    model_outputs may include:
      - "answer": str (final answer)
      - "samples": list[str] (multiple generations for self-consistency)
      - "token_logprobs": list[float] (per-token logprobs for the chosen answer)
    """

    def compute(
        self,
        claim_text: str,
        *,
        claim_id: Optional[str] = None,
        model_outputs: Optional[Mapping[str, Any]] = None,
    ) -> ClaimSignals:
        mo = dict(model_outputs or {})
        answer = mo.get("answer") if isinstance(mo.get("answer"), str) else ""
        samples = mo.get("samples") if isinstance(mo.get("samples"), list) else None
        token_logprobs = mo.get("token_logprobs")
        if isinstance(token_logprobs, list):
            token_logprobs = [x for x in token_logprobs]
        else:
            token_logprobs = None

        sig: Dict[str, Any] = {}
        sig["claim_length_chars"] = _text_length(claim_text)
        sig["claim_has_number"] = float(_contains_number(claim_text))
        sig["claim_is_question"] = float(_ends_question(claim_text))

        if answer:
            sig["answer_length_chars"] = _text_length(answer)
            sig["answer_hedge_rate"] = float(_hedge_rate(answer))
            sig["answer_refusal_flag"] = float(_refusal_flag(answer))
            sig["answer_citation_request_flag"] = float(_citation_request_flag(answer))
        else:
            sig["answer_length_chars"] = 0
            sig["answer_hedge_rate"] = 0.0
            sig["answer_refusal_flag"] = 0.0
            sig["answer_citation_request_flag"] = 0.0

        div = self_consistency_divergence(samples or [])
        sig["self_consistency_divergence"] = div

        sig.update(logprob_surrogates(token_logprobs))

        # Simple aggregate risk score in [0,1] (heuristic; downstream may override).
        parts: List[Tuple[Optional[float], float]] = [
            (sig.get("risk_from_mean_logprob"), 0.45),
            (sig.get("risk_from_min_logprob"), 0.25),
            (div, 0.20),
            (sig.get("answer_hedge_rate"), 0.10),
        ]
        num = 0.0
        den = 0.0
        for v, w in parts:
            if v is None:
                continue
            num += float(v) * w
            den += w
        base_risk = (num / den) if den > 0 else 0.0
        # Penalize refusal-like answers.
        base_risk = max(base_risk, float(sig.get("answer_refusal_flag", 0.0)))
        sig["aggregate_risk"] = float(max(0.0, min(1.0, base_risk)))

        return ClaimSignals(claim_id=claim_id, claim_text=claim_text or "", signals=sig)


def compute_uncertainty_signals(
    claim_text: str,
    *,
    claim_id: Optional[str] = None,
    model_outputs: Optional[Mapping[str, Any]] = None,
) -> ClaimSignals:
    """Convenience functional API."""
    return UncertaintySignalComputer().compute(claim_text, claim_id=claim_id, model_outputs=model_outputs)
