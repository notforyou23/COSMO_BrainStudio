from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol
import json, re, statistics

class LLMBackend(Protocol):
    def generate(self, prompt: str, **kwargs) -> str: ...

@dataclass
class PatternOutput:
    answer: str
    passed: bool
    score: float
    confidence: float
    meta: Dict[str, Any]

class VerifierPattern(Protocol):
    name: str
    def run(self, question: str, evidence: List[Dict[str, Any]], gen: LLMBackend, ver: LLMBackend, **kwargs) -> PatternOutput: ...

def _json_from_text(text: str) -> Dict[str, Any]:
    t = text.strip()
    m = re.search(r"\{[\s\S]*\}", t)
    if m:
        t = m.group(0)
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else {"value": obj}
    except Exception:
        return {"raw": text}

def _coerce_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _evidence_block(evidence: List[Dict[str, Any]], limit: int = 12) -> str:
    parts = []
    for i, ev in enumerate(evidence[:limit], 1):
        cid = ev.get("id") or ev.get("citation") or f"E{i}"
        txt = (ev.get("text") or ev.get("snippet") or "").strip()
        if not txt:
            continue
        parts.append(f"[{cid}] {txt}")
    return "\n".join(parts) if parts else "(no evidence provided)"
class BestOfNVerifierRerank:
    name = "best_of_n_rerank"
    def __init__(self, n: int = 4, gen_kwargs: Optional[Dict[str, Any]] = None, ver_kwargs: Optional[Dict[str, Any]] = None):
        self.n, self.gen_kwargs, self.ver_kwargs = n, (gen_kwargs or {}), (ver_kwargs or {})

    def run(self, question: str, evidence: List[Dict[str, Any]], gen: LLMBackend, ver: LLMBackend, **kwargs) -> PatternOutput:
        ev = _evidence_block(evidence)
        gkw = {**self.gen_kwargs, **kwargs.get("gen_kwargs", {})}
        vkw = {**self.ver_kwargs, **kwargs.get("ver_kwargs", {})}
        cand: List[Dict[str, Any]] = []
        for i in range(self.n):
            prompt = f"Answer the question using the evidence. Cite sources like [id].\n\nQuestion: {question}\n\nEvidence:\n{ev}\n\nAnswer:"
            ans = (gen.generate(prompt, **gkw) or "").strip()
            vprompt = (
                "You are a strict verifier. Grade the answer for factual support by the evidence. "
                "Return JSON ONLY with keys: score (0-1), passed (bool), confidence (0-1), rationale (string).\n\n"
                f"Question: {question}\n\nEvidence:\n{ev}\n\nAnswer:\n{ans}\n\nJSON:"
            )
            vtxt = ver.generate(vprompt, **vkw) or ""
            obj = _json_from_text(vtxt)
            score = _coerce_float(obj.get("score"), 0.0)
            conf = _coerce_float(obj.get("confidence"), min(1.0, max(0.0, score)))
            passed = bool(obj.get("passed")) if "passed" in obj else (score >= 0.5)
            cand.append({"answer": ans, "score": score, "confidence": conf, "passed": passed, "verdict": obj})
        best = max(cand, key=lambda x: (x["score"], x["confidence"])) if cand else {"answer": "", "score": 0.0, "confidence": 0.0, "passed": False, "verdict": {}}
        meta = {"candidates": cand, "pattern": self.name}
        return PatternOutput(answer=best["answer"], passed=bool(best["passed"]), score=float(best["score"]), confidence=float(best["confidence"]), meta=meta)
class EvidenceEntailmentAttributionCheck:
    name = "evidence_entailment_attribution"
    def __init__(self, ver_kwargs: Optional[Dict[str, Any]] = None):
        self.ver_kwargs = ver_kwargs or {}

    def run(self, question: str, evidence: List[Dict[str, Any]], gen: LLMBackend, ver: LLMBackend, **kwargs) -> PatternOutput:
        ev = _evidence_block(evidence)
        gkw = {**kwargs.get("gen_kwargs", {})}
        vkw = {**self.ver_kwargs, **kwargs.get("ver_kwargs", {})}
        aprompt = f"Answer the question using ONLY the evidence. Cite every key claim with [id].\n\nQuestion: {question}\n\nEvidence:\n{ev}\n\nAnswer:"
        ans = (gen.generate(aprompt, **gkw) or "").strip()
        vprompt = (
            "Check whether the answer is fully supported by the evidence and properly attributed with citations. "
            "Return JSON ONLY with keys: supported (bool), score (0-1), confidence (0-1), missing_citations (list of strings), contradictions (list of strings).\n\n"
            f"Question: {question}\n\nEvidence:\n{ev}\n\nAnswer:\n{ans}\n\nJSON:"
        )
        vtxt = ver.generate(vprompt, **vkw) or ""
        obj = _json_from_text(vtxt)
        score = _coerce_float(obj.get("score"), 0.0)
        conf = _coerce_float(obj.get("confidence"), min(1.0, max(0.0, score)))
        passed = bool(obj.get("supported")) if "supported" in obj else (score >= 0.5)
        meta = {"verdict": obj, "pattern": self.name}
        return PatternOutput(answer=ans, passed=passed, score=score, confidence=conf, meta=meta)
class SelfConsistencyCritiqueGate:
    name = "self_consistency_critique_gate"
    def __init__(self, k: int = 5, gen_kwargs: Optional[Dict[str, Any]] = None, ver_kwargs: Optional[Dict[str, Any]] = None):
        self.k, self.gen_kwargs, self.ver_kwargs = k, (gen_kwargs or {}), (ver_kwargs or {})

    def _normalize(self, s: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"\[[^\]]+\]", "", s or "").strip().lower())

    def run(self, question: str, evidence: List[Dict[str, Any]], gen: LLMBackend, ver: LLMBackend, **kwargs) -> PatternOutput:
        ev = _evidence_block(evidence)
        gkw = {**self.gen_kwargs, **kwargs.get("gen_kwargs", {})}
        vkw = {**self.ver_kwargs, **kwargs.get("ver_kwargs", {})}
        answers: List[str] = []
        for _ in range(self.k):
            prompt = f"Answer the question using the evidence. Cite sources like [id].\n\nQuestion: {question}\n\nEvidence:\n{ev}\n\nAnswer:"
            answers.append((gen.generate(prompt, **gkw) or "").strip())
        norms = [self._normalize(a) for a in answers]
        counts: Dict[str, int] = {}
        for n in norms: counts[n] = counts.get(n, 0) + 1
        best_norm = max(counts.items(), key=lambda kv: kv[1])[0] if counts else ""
        idx = norms.index(best_norm) if best_norm in norms else 0
        chosen = answers[idx] if answers else ""
        consistency = (counts.get(best_norm, 0) / max(1, len(answers))) if answers else 0.0
        cprompt = (
            "You are a critic/verifier. Identify unsupported claims or missing citations, then output JSON ONLY with keys: passed (bool), score (0-1), confidence (0-1), critique (string), revised_answer (string). "
            "If passed=false, provide a revised_answer that uses ONLY the evidence with citations.\n\n"
            f"Question: {question}\n\nEvidence:\n{ev}\n\nAnswer:\n{chosen}\n\nJSON:"
        )
        ctxt = ver.generate(cprompt, **vkw) or ""
        obj = _json_from_text(ctxt)
        score = _coerce_float(obj.get("score"), consistency)
        conf = _coerce_float(obj.get("confidence"), min(1.0, max(0.0, (score + consistency) / 2)))
        passed = bool(obj.get("passed")) if "passed" in obj else (score >= 0.5 and consistency >= 0.4)
        final_answer = (obj.get("revised_answer") or chosen).strip() if not passed else chosen
        meta = {"answers": answers, "consistency": consistency, "verdict": obj, "pattern": self.name}
        return PatternOutput(answer=final_answer, passed=passed, score=score, confidence=conf, meta=meta)

PATTERNS: Dict[str, Any] = {
    BestOfNVerifierRerank.name: BestOfNVerifierRerank,
    EvidenceEntailmentAttributionCheck.name: EvidenceEntailmentAttributionCheck,
    SelfConsistencyCritiqueGate.name: SelfConsistencyCritiqueGate,
}

def make_pattern(name: str, **kwargs) -> Any:
    if name not in PATTERNS:
        raise KeyError(f"Unknown pattern: {name}. Available: {sorted(PATTERNS)}")
    return PATTERNS[name](**kwargs)
