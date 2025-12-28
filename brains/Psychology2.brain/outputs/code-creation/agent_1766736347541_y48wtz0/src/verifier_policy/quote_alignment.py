"""Quote-level alignment: map each claim to minimal supporting/refuting spans in passages.

Deterministic, dependency-light alignment for retrieve-then-verify pipelines.
Input passages may be dict-like with keys {'id','text'} or objects with attrs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import re

__all__ = [
    "QuoteSpan",
    "align_claim_to_passages",
    "align_claims_to_passages",
]

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?")
_NEG_RE = re.compile(r"\b(?:no|not|never|none|without|cannot|can't|won't|doesn't|isn't|aren't|wasn't|weren't|don't|didn't)\b", re.I)

_STOP = {
    "a","an","the","and","or","but","if","then","else","when","while",
    "to","of","in","on","at","by","for","from","as","with","without","into","over","under",
    "is","are","was","were","be","been","being","do","does","did","doing","have","has","had",
    "this","that","these","those","it","its","they","them","their","we","you","i","he","she",
}

@dataclass(frozen=True)
class QuoteSpan:
    claim: str
    passage_id: str
    start: int
    end: int
    text: str
    score: float
    polarity: str  # 'support' or 'refute'


def _get_field(p: Any, key: str, default: str = "") -> str:
    if isinstance(p, dict):
        v = p.get(key, default)
    else:
        v = getattr(p, key, default)
    return "" if v is None else str(v)


def _tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def _content_tokens(text: str) -> List[str]:
    return [t for t in _tokenize(text) if t not in _STOP and len(t) > 1]


def _negated(text: str) -> bool:
    return _NEG_RE.search(text or "") is not None


def _char_spans(text: str) -> List[Tuple[str, int, int]]:
    return [(m.group(0).lower(), m.start(), m.end()) for m in _WORD_RE.finditer(text)]


def _best_span(claim: str, passage_text: str) -> Optional[Tuple[int, int, float]]:
    c_toks = _content_tokens(claim)
    if not c_toks:
        return None
    spans = _char_spans(passage_text)
    if not spans:
        return None

    # Greedy minimal window covering as many claim tokens as possible.
    target = set(c_toks)
    positions: Dict[str, List[int]] = {}
    for idx, (tok, s, e) in enumerate(spans):
        if tok in target:
            positions.setdefault(tok, []).append(idx)

    if not positions:
        return None

    # Find minimal (i,j) window maximizing coverage and then minimizing length.
    best_i = best_j = 0
    best_cov = 0
    best_len = 10**18

    # Two-pointer over token indices, tracking counts for claim-token set.
    need = len(target)
    have = 0
    counts: Dict[str, int] = {}
    i = 0
    for j in range(len(spans)):
        tok = spans[j][0]
        if tok in target:
            counts[tok] = counts.get(tok, 0) + 1
            if counts[tok] == 1:
                have += 1
        # Try to shrink while maintaining current coverage.
        while i <= j:
            cov = have
            cur_len = spans[j][2] - spans[i][1]
            if cov > best_cov or (cov == best_cov and cur_len < best_len):
                best_cov, best_len, best_i, best_j = cov, cur_len, i, j
            tok_i = spans[i][0]
            if tok_i in target:
                counts[tok_i] -= 1
                if counts[tok_i] == 0:
                    have -= 1
                    i += 1
                    break
            i += 1

    start = spans[best_i][1]
    end = spans[best_j][2]
    score = best_cov / max(1, len(target))
    return start, end, float(score)


def _polarity_for_span(claim: str, span_text: str) -> str:
    # Lightweight deterministic heuristic: negation mismatch implies refutation.
    c_neg = _negated(claim)
    s_neg = _negated(span_text)
    return "refute" if (c_neg ^ s_neg) else "support"


def align_claim_to_passages(
    claim: str,
    passages: Sequence[Any],
    *,
    top_k: int = 3,
    min_score: float = 0.35,
    max_quote_chars: int = 600,
) -> List[QuoteSpan]:
    """Return up to top_k aligned quote spans from passages for a claim."""
    out: List[QuoteSpan] = []
    for p in passages or []:
        pid = _get_field(p, "id", "") or _get_field(p, "passage_id", "") or "passage"
        text = _get_field(p, "text", "")
        if not text:
            continue
        best = _best_span(claim, text)
        if not best:
            continue
        start, end, score = best
        if score < float(min_score):
            continue
        qtxt = text[start:end].strip()
        if len(qtxt) > max_quote_chars:
            qtxt = qtxt[:max_quote_chars].rstrip() + "…"
        pol = _polarity_for_span(claim, qtxt)
        out.append(QuoteSpan(claim=claim, passage_id=pid, start=start, end=end, text=qtxt, score=score, polarity=pol))

    out.sort(key=lambda q: (q.score, -len(q.text)), reverse=True)
    return out[: max(0, int(top_k))]


def align_claims_to_passages(
    claims: Sequence[str],
    passages_by_claim: Sequence[Sequence[Any]],
    *,
    top_k: int = 3,
    min_score: float = 0.35,
) -> List[List[QuoteSpan]]:
    """Batch align: claims[i] aligned against passages_by_claim[i]."""
    res: List[List[QuoteSpan]] = []
    for c, ps in zip(claims or [], passages_by_claim or []):
        res.append(align_claim_to_passages(c, ps, top_k=top_k, min_score=min_score))
    return res
