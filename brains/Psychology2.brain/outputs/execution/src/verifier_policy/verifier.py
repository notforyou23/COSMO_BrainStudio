from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
import re

_WORD = re.compile(r"[A-Za-z0-9]+")
_NUM = re.compile(r"(?<!\w)(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\w)")

def _tok(s: str) -> List[str]:
    return [t.lower() for t in _WORD.findall(s or "")]

def _nums(s: str) -> List[str]:
    return [n.replace(",", "") for n in _NUM.findall(s or "")]

def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb: return 0.0
    return len(sa & sb) / float(len(sa | sb))

@dataclass
class Passage:
    source_id: str
    text: str
    meta: Dict[str, Any] = None

@dataclass
class Quote:
    passage_id: str
    text: str
    start: int
    end: int
    score: float

@dataclass
class ClaimDecision:
    claim: str
    supported: bool
    score: float
    threshold: float
    quotes: List[Quote]
    passages: List[Passage]
    failures: List[str]

@dataclass
class AuditEvent:
    claim: str
    event: str
    detail: Dict[str, Any]

def default_decompose(text: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"(?<=[\.\?\!])\s+", (text or "").strip()) if p.strip()]
    if not parts and (text or "").strip(): parts = [text.strip()]
    return parts

def default_retrieve(_: str, k: int = 5) -> List[Passage]:
    return []

def default_align(claim: str, passages: Sequence[Passage], max_quotes: int = 3) -> List[Quote]:
    ct = _tok(claim)
    out: List[Quote] = []
    for p in passages:
        pt = _tok(p.text)
        base = _jaccard(ct, pt)
        if base <= 0.0: continue
        start = 0
        end = min(len(p.text), 300)
        snippet = p.text[start:end]
        out.append(Quote(passage_id=p.source_id, text=snippet, start=start, end=end, score=base))
    out.sort(key=lambda q: q.score, reverse=True)
    return out[:max_quotes]

def constraint_numeric_preservation(claim: str, quote_text: str) -> Tuple[bool, str]:
    cn = _nums(claim)
    if not cn: return True, ""
    qn = set(_nums(quote_text))
    missing = [n for n in cn if n not in qn]
    if missing: return False, f"missing_numbers:{missing}"
    return True, ""
class VerifierPolicy:
    def __init__(
        self,
        retriever: Callable[[str, int], List[Passage]] = default_retrieve,
        decomposer: Callable[[str], List[str]] = default_decompose,
        aligner: Callable[[str, Sequence[Passage], int], List[Quote]] = default_align,
        constraints: Optional[List[Callable[[str, str], Tuple[bool, str]]]] = None,
        threshold: float = 0.22,
        top_k: int = 5,
        max_quotes: int = 3,
        min_passages: int = 1,
    ) -> None:
        self.retriever, self.decomposer, self.aligner = retriever, decomposer, aligner
        self.constraints = constraints or [constraint_numeric_preservation]
        self.threshold, self.top_k, self.max_quotes = float(threshold), int(top_k), int(max_quotes)
        self.min_passages = int(min_passages)

    def calibrate_threshold(
        self,
        heldout: Iterable[Dict[str, Any]],
        min_precision: float = 0.85,
        grid: Optional[Sequence[float]] = None,
    ) -> float:
        grid = list(grid) if grid is not None else [i / 100.0 for i in range(5, 91, 2)]
        best_t, best_f1 = self.threshold, -1.0
        for t in grid:
            tp = fp = fn = 0
            for ex in heldout:
                decs, _ = self.verify(ex["text"], threshold=t)
                pred = all(d.supported for d in decs)
                gold = bool(ex.get("supported", True))
                tp += int(pred and gold); fp += int(pred and not gold); fn += int((not pred) and gold)
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
            if prec >= min_precision and f1 > best_f1:
                best_t, best_f1 = t, f1
        self.threshold = float(best_t)
        return self.threshold

    def verify(self, text: str, threshold: Optional[float] = None) -> Tuple[List[ClaimDecision], List[AuditEvent]]:
        thr = self.threshold if threshold is None else float(threshold)
        claims = self.decomposer(text)
        decisions: List[ClaimDecision] = []
        audit: List[AuditEvent] = []
        for claim in claims:
            failures: List[str] = []
            passages = self.retriever(claim, self.top_k) or []
            if len(passages) < self.min_passages:
                failures.append("no_retrieved_passages")
                audit.append(AuditEvent(claim, "retrieval_failure", {"retrieved": len(passages)}))
            quotes = self.aligner(claim, passages, self.max_quotes) if passages else []
            if not quotes:
                failures.append("no_aligned_quotes")
                audit.append(AuditEvent(claim, "alignment_failure", {"retrieved": len(passages)}))
            kept: List[Quote] = []
            for q in quotes:
                ok = True
                for c in self.constraints:
                    passed, msg = c(claim, q.text)
                    if not passed:
                        ok = False
                        failures.append(f"constraint:{msg}")
                        audit.append(AuditEvent(claim, "constraint_failure", {"constraint": getattr(c, "__name__", "constraint"), "detail": msg, "quote_score": q.score, "passage_id": q.passage_id}))
                        break
                if ok: kept.append(q)
            score = max([q.score for q in kept], default=0.0)
            supported = bool(kept) and score >= thr and "no_retrieved_passages" not in failures and "no_aligned_quotes" not in failures
            if not supported:
                audit.append(AuditEvent(claim, "evidence_failure", {"threshold": thr, "best_score": score, "failures": sorted(set(failures))}))
            decisions.append(ClaimDecision(claim=claim, supported=supported, score=score, threshold=thr, quotes=kept, passages=passages, failures=sorted(set(failures))))
        return decisions, audit

    def verify_to_dict(self, text: str, threshold: Optional[float] = None) -> Dict[str, Any]:
        decisions, audit = self.verify(text, threshold=threshold)
        return {"decisions": [asdict(d) for d in decisions], "audit": [asdict(a) for a in audit], "threshold": self.threshold}

def verify_text(text: str, **kwargs: Any) -> Dict[str, Any]:
    return VerifierPolicy(**kwargs).verify_to_dict(text)
