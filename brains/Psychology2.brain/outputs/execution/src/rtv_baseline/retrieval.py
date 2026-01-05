from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import math
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
import os
os.chdir(r'/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')



_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", re.UNICODE)


def _tok(text: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text or "")]


def chunk_text(text: str, chunk_size: int = 220, overlap: int = 50) -> List[Tuple[int, int, str]]:
    toks = _tok(text)
    if not toks:
        return []
    chunk_size = max(32, int(chunk_size))
    overlap = max(0, min(int(overlap), chunk_size - 1))
    step = max(1, chunk_size - overlap)
    out = []
    i = 0
    while i < len(toks):
        j = min(len(toks), i + chunk_size)
        out.append((i, j, " ".join(toks[i:j])))
        if j == len(toks):
            break
        i += step
    return out


@dataclass(frozen=True)
class EvidenceChunk:
    doc_id: str
    chunk_id: str
    text: str
    meta: Dict[str, str]


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    topk: List[Tuple[EvidenceChunk, float]]


class LocalRetriever:
    def __init__(self, chunks: Sequence[EvidenceChunk], k1: float = 1.2, b: float = 0.75):
        self.k1, self.b = float(k1), float(b)
        self.chunks = list(chunks)
        self._tf: List[Dict[str, int]] = []
        self._dl: List[int] = []
        self._df: Dict[str, int] = {}
        for ch in self.chunks:
            toks = ch.text.split()
            tf: Dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            self._tf.append(tf)
            dl = len(toks)
            self._dl.append(dl)
            for t in tf.keys():
                self._df[t] = self._df.get(t, 0) + 1
        self._n = len(self.chunks)
        self._avgdl = (sum(self._dl) / self._n) if self._n else 0.0
        self._idf: Dict[str, float] = {}
        for t, df in self._df.items():
            self._idf[t] = math.log(1.0 + (self._n - df + 0.5) / (df + 0.5)) if self._n else 0.0

    @classmethod
    def from_corpus(
        cls,
        corpus: Sequence[dict],
        text_key: str = "text",
        id_key: str = "id",
        chunk_size: int = 220,
        overlap: int = 50,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> "LocalRetriever":
        chunks: List[EvidenceChunk] = []
        for i, doc in enumerate(corpus):
            doc_id = str(doc.get(id_key, f"doc_{i}"))
            raw = str(doc.get(text_key, "") or "")
            meta = {k: str(v) for k, v in doc.items() if k not in {text_key}}
            for ci, (a, z, ctext) in enumerate(chunk_text(raw, chunk_size=chunk_size, overlap=overlap)):
                ch_id = f"{doc_id}::c{ci}:{a}-{z}"
                chunks.append(EvidenceChunk(doc_id=doc_id, chunk_id=ch_id, text=ctext, meta=meta))
        return cls(chunks=chunks, k1=k1, b=b)

    @classmethod
    def from_jsonl(
        cls,
        path: str | Path,
        text_key: str = "text",
        id_key: str = "id",
        chunk_size: int = 220,
        overlap: int = 50,
        k1: float = 1.2,
        b: float = 0.75,
        limit: Optional[int] = None,
    ) -> "LocalRetriever":
        p = Path(path)
        corpus = []
        with p.open("r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                corpus.append(json.loads(ln))
                if limit is not None and len(corpus) >= limit:
                    break
        return cls.from_corpus(corpus, text_key=text_key, id_key=id_key, chunk_size=chunk_size, overlap=overlap, k1=k1, b=b)

    def _bm25_scores(self, q_toks: List[str]) -> List[float]:
        scores = [0.0] * self._n
        if not self._n or not q_toks:
            return scores
        for qi in q_toks:
            idf = self._idf.get(qi)
            if idf is None:
                continue
            for i, tf in enumerate(self._tf):
                f = tf.get(qi, 0)
                if not f:
                    continue
                dl = self._dl[i] or 1
                denom = f + self.k1 * (1.0 - self.b + self.b * (dl / (self._avgdl or 1.0)))
                scores[i] += idf * (f * (self.k1 + 1.0) / denom)
        return scores

    def _tfidf_scores(self, q_toks: List[str]) -> List[float]:
        scores = [0.0] * self._n
        if not self._n or not q_toks:
            return scores
        qtf: Dict[str, int] = {}
        for t in q_toks:
            qtf[t] = qtf.get(t, 0) + 1
        q_vec: Dict[str, float] = {}
        for t, f in qtf.items():
            if t in self._df:
                q_vec[t] = (1.0 + math.log(f)) * (self._idf.get(t, 0.0) or 0.0)
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        for i, tf in enumerate(self._tf):
            dot = 0.0
            d_norm = 0.0
            for t, f in tf.items():
                w = (1.0 + math.log(f)) * (self._idf.get(t, 0.0) or 0.0)
                d_norm += w * w
                if t in q_vec:
                    dot += w * q_vec[t]
            d_norm = math.sqrt(d_norm) or 1.0
            scores[i] = dot / (d_norm * q_norm) if dot else 0.0
        return scores

    def retrieve(self, query: str, top_k: int = 5, use_tfidf_fallback: bool = True) -> RetrievalResult:
        q_toks = _tok(query)
        scores = self._bm25_scores(q_toks)
        if use_tfidf_fallback and (not any(s > 0 for s in scores)):
            scores = self._tfidf_scores(q_toks)
        k = max(1, int(top_k))
        idxs = sorted(range(self._n), key=lambda i: scores[i], reverse=True)[:k]
        top = [(self.chunks[i], float(scores[i])) for i in idxs if scores[i] > 0 or self._n <= k]
        return RetrievalResult(query=query, topk=top)
