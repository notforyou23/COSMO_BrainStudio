from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import json

import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception as e:  # pragma: no cover
    TfidfVectorizer = None


Label = str  # "supported" | "unsupported" | "insufficient"


@dataclass(frozen=True)
class EvidenceDoc:
    doc_id: str
    text: str
    source: Optional[str] = None
    supports: Tuple[str, ...] = ()
    refutes: Tuple[str, ...] = ()
    meta: Dict[str, Any] = None

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EvidenceDoc":
        return EvidenceDoc(
            doc_id=str(d.get("doc_id") or d.get("id") or ""),
            text=str(d.get("text") or ""),
            source=d.get("source"),
            supports=tuple(d.get("supports") or d.get("claims_supported") or ()),
            refutes=tuple(d.get("refutes") or d.get("claims_refuted") or ()),
            meta=dict(d.get("meta") or {}),
        )


@dataclass
class Retrieved:
    doc_id: str
    score: float
    text: str
    source: Optional[str] = None
    hit: Optional[str] = None  # "supports" | "refutes" | None


@dataclass
class ClaimAudit:
    claim_id: str
    label: Label
    rationale: str
    retrieved: List[Retrieved]
    trace: Dict[str, Any]


def _get_claim_id(claim: Any) -> str:
    if isinstance(claim, str):
        return claim
    if isinstance(claim, dict):
        return str(claim.get("id") or claim.get("claim_id") or claim.get("cid") or "")
    return str(getattr(claim, "id", "") or getattr(claim, "claim_id", "") or "")


def _get_claim_text(claim: Any) -> str:
    if isinstance(claim, str):
        return claim
    if isinstance(claim, dict):
        return str(claim.get("text") or claim.get("claim") or claim.get("normalized") or claim.get("verbatim") or "")
    for attr in ("text", "claim", "normalized", "verbatim"):
        v = getattr(claim, attr, None)
        if v:
            return str(v)
    return ""


class ReferenceCorpus:
    def __init__(self, docs: Sequence[EvidenceDoc]):
        self.docs = list(docs)
        self._by_id = {d.doc_id: d for d in self.docs}

    @staticmethod
    def load(path: str) -> "ReferenceCorpus":
        p = Path(path)
        if p.suffix.lower() in {".jsonl", ".ndjson"}:
            docs = []
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                docs.append(EvidenceDoc.from_dict(json.loads(line)))
            return ReferenceCorpus(docs)
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "docs" in data:
            data = data["docs"]
        return ReferenceCorpus([EvidenceDoc.from_dict(x) for x in data])

    def get(self, doc_id: str) -> Optional[EvidenceDoc]:
        return self._by_id.get(doc_id)
class Retriever:
    def __init__(self, corpus: ReferenceCorpus):
        if TfidfVectorizer is None:
            raise RuntimeError("scikit-learn is required for retrieval (TfidfVectorizer missing).")
        self.corpus = corpus
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=50000)
        texts = [d.text for d in corpus.docs]
        self.X = self.vectorizer.fit_transform(texts)

    def search(self, query: str, k: int = 5) -> List[Retrieved]:
        if not query.strip() or not self.corpus.docs:
            return []
        q = self.vectorizer.transform([query])
        scores = (self.X @ q.T).toarray().ravel()
        if scores.size == 0:
            return []
        k = min(int(k), scores.size)
        idx = np.argpartition(-scores, k - 1)[:k]
        idx = idx[np.argsort(-scores[idx])]
        out: List[Retrieved] = []
        for i in idx.tolist():
            d = self.corpus.docs[i]
            out.append(Retrieved(doc_id=d.doc_id, score=float(scores[i]), text=d.text, source=d.source))
        return out


def _decide_label(claim_id: str, retrieved: List[Retrieved], corpus: ReferenceCorpus, min_score: float) -> Tuple[Label, str, List[Retrieved]]:
    supporting = []
    refuting = []
    enriched: List[Retrieved] = []
    for r in retrieved:
        d = corpus.get(r.doc_id)
        hit = None
        if d and claim_id:
            if claim_id in d.supports:
                hit = "supports"
            elif claim_id in d.refutes:
                hit = "refutes"
        rr = Retrieved(doc_id=r.doc_id, score=r.score, text=r.text, source=r.source, hit=hit)
        enriched.append(rr)
        if rr.score >= min_score:
            if hit == "supports":
                supporting.append(rr)
            elif hit == "refutes":
                refuting.append(rr)

    if supporting and refuting:
        best_s = max(supporting, key=lambda x: x.score)
        best_r = max(refuting, key=lambda x: x.score)
        if best_s.score >= best_r.score:
            return "supported", f"Retrieved evidence explicitly maps to supports (doc={best_s.doc_id}).", enriched
        return "unsupported", f"Retrieved evidence explicitly maps to refutes (doc={best_r.doc_id}).", enriched
    if supporting:
        best = max(supporting, key=lambda x: x.score)
        return "supported", f"Retrieved evidence explicitly maps to supports (doc={best.doc_id}).", enriched
    if refuting:
        best = max(refuting, key=lambda x: x.score)
        return "unsupported", f"Retrieved evidence explicitly maps to refutes (doc={best.doc_id}).", enriched
    return "insufficient", "No retrieved evidence explicitly mapped to support/refute this claim id at the configured threshold.", enriched


def audit_claims(
    claims: Sequence[Any],
    corpus: ReferenceCorpus,
    *,
    k: int = 5,
    min_score: float = 0.10,
    retriever: Optional[Retriever] = None,
) -> List[ClaimAudit]:
    r = retriever or Retriever(corpus)
    results: List[ClaimAudit] = []
    for c in claims:
        claim_id = _get_claim_id(c)
        text = _get_claim_text(c)
        query = text or claim_id
        retrieved = r.search(query=query, k=k)
        label, rationale, enriched = _decide_label(claim_id, retrieved, corpus, min_score=min_score)
        trace = {
            "query": query,
            "k": k,
            "min_score": min_score,
            "scoring": "tfidf_cosine_proxy(dot_product_on_l2_normed_tfidf)",
            "evidence_hits": [{"doc_id": x.doc_id, "score": x.score, "hit": x.hit} for x in enriched],
        }
        results.append(ClaimAudit(claim_id=claim_id, label=label, rationale=rationale, retrieved=enriched, trace=trace))
    return results


def audit_to_jsonable(audits: Sequence[ClaimAudit]) -> List[Dict[str, Any]]:
    out = []
    for a in audits:
        d = asdict(a)
        d["retrieved"] = [asdict(x) for x in a.retrieved]
        out.append(d)
    return out


def compute_tiered_metrics(
    audits: Sequence[ClaimAudit],
    gold: Dict[str, Label],
    *,
    abstain_label: Label = "insufficient",
) -> Dict[str, Any]:
    tiers = {}
    for min_score in (0.00, 0.10, 0.20, 0.30):
        preds = {}
        for a in audits:
            filt = [x for x in a.retrieved if x.score >= min_score]
            if not filt:
                preds[a.claim_id] = abstain_label
            else:
                supp = any(x.hit == "supports" for x in filt)
                refu = any(x.hit == "refutes" for x in filt)
                if supp and not refu:
                    preds[a.claim_id] = "supported"
                elif refu and not supp:
                    preds[a.claim_id] = "unsupported"
                else:
                    preds[a.claim_id] = abstain_label
        n = 0
        fa = 0
        abst = 0
        for cid, g in gold.items():
            if cid not in preds:
                continue
            n += 1
            p = preds[cid]
            if p == abstain_label:
                abst += 1
            elif p != g:
                fa += 1
        tiers[str(min_score)] = {
            "n_scored": n,
            "false_accept_rate": (fa / n) if n else None,
            "abstain_rate": (abst / n) if n else None,
        }
    return {"tiers": tiers, "gold_labels": sorted(set(gold.values()))}
