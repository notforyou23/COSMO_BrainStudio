from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?", re.UNICODE)


def _tokens(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "")]


def normalize_provenance(meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    m = dict(meta or {})
    prov = {
        "source_id": str(m.get("source_id") or m.get("id") or m.get("doc_id") or "unknown"),
        "uri": m.get("uri") or m.get("url") or None,
        "title": m.get("title") or None,
        "section": m.get("section") or None,
        "published_at": m.get("published_at") or m.get("date") or None,
        "author": m.get("author") or None,
        "span": m.get("span") if isinstance(m.get("span"), dict) else None,
        "extra": m.get("extra") if isinstance(m.get("extra"), dict) else {},
    }
    if prov["span"] is None:
        start = m.get("start") if isinstance(m.get("start"), int) else None
        end = m.get("end") if isinstance(m.get("end"), int) else None
        if start is not None or end is not None:
            prov["span"] = {"start": start or 0, "end": end if end is not None else (start or 0)}
    if prov["uri"] is not None:
        prov["uri"] = str(prov["uri"])
    return prov


@dataclass(frozen=True)
class Passage:
    passage_id: int
    text: str
    provenance: Dict[str, Any]


class DeterministicRetriever:
    """Deterministic top-k lexical retriever with on-disk JSON caching."""

    def __init__(self, passages: Sequence[Dict[str, Any]], cache_dir: Optional[str | Path] = None):
        self._passages: List[Passage] = []
        for i, p in enumerate(passages):
            text = p.get("text") if isinstance(p, dict) else str(p)
            prov = normalize_provenance(p.get("provenance") if isinstance(p, dict) else None)
            if isinstance(p, dict):
                prov = normalize_provenance({**prov, **{k: v for k, v in p.items() if k != "text"}})
            self._passages.append(Passage(i, text or "", prov))
        self._N = len(self._passages)
        self._doc_len: List[int] = []
        self._avgdl = 0.0
        self._df: Dict[str, int] = {}
        self._postings: Dict[str, List[Tuple[int, int]]] = {}
        self._build_index()
        self._fingerprint = self._compute_fingerprint()
        self._cache_dir = Path(cache_dir) if cache_dir is not None else None
        if self._cache_dir is not None:
            self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _build_index(self) -> None:
        total_len = 0
        for ps in self._passages:
            toks = _tokens(ps.text)
            total_len += len(toks)
            self._doc_len.append(len(toks))
            tf: Dict[str, int] = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            for t, c in tf.items():
                self._df[t] = self._df.get(t, 0) + 1
                self._postings.setdefault(t, []).append((ps.passage_id, c))
        self._avgdl = (total_len / self._N) if self._N else 0.0
        for t in list(self._postings.keys()):
            self._postings[t].sort(key=lambda x: x[0])

    def _compute_fingerprint(self) -> str:
        h = sha256()
        h.update(str(self._N).encode("utf-8"))
        for ps in self._passages:
            sid = ps.provenance.get("source_id", "unknown")
            h.update(str(sid).encode("utf-8"))
            h.update(str(len(ps.text)).encode("utf-8"))
            h.update(ps.text[:64].encode("utf-8", errors="ignore"))
        return h.hexdigest()[:16]

    def _cache_key(self, query: str, k: int) -> str:
        q = " ".join(_tokens(query))
        s = f"bm25|k={k}|fp={self._fingerprint}|q={q}"
        return sha256(s.encode("utf-8")).hexdigest()

    def _bm25_scores(self, query: str, k1: float = 1.2, b: float = 0.75) -> Dict[int, float]:
        q_toks = _tokens(query)
        if not q_toks or self._N == 0:
            return {}
        scores: Dict[int, float] = {}
        for t in q_toks:
            df = self._df.get(t, 0)
            if df == 0:
                continue
            idf = math.log(1.0 + (self._N - df + 0.5) / (df + 0.5))
            for pid, tf in self._postings.get(t, []):
                dl = self._doc_len[pid]
                denom = tf + k1 * (1.0 - b + b * (dl / (self._avgdl or 1.0)))
                s = idf * (tf * (k1 + 1.0)) / (denom or 1.0)
                scores[pid] = scores.get(pid, 0.0) + s
        return scores

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        top_k = int(top_k)
        if top_k <= 0:
            return []
        if self._cache_dir is not None:
            key = self._cache_key(query, top_k)
            path = self._cache_dir / f"{key}.json"
            if path.exists():
                obj = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(obj, list):
                    return obj
        scores = self._bm25_scores(query)
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))[:top_k]
        out: List[Dict[str, Any]] = []
        for pid, score in ranked:
            ps = self._passages[pid]
            out.append(
                {
                    "text": ps.text,
                    "score": float(score),
                    "provenance": normalize_provenance(ps.provenance),
                }
            )
        if self._cache_dir is not None:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(out, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            tmp.replace(path)
        return out
