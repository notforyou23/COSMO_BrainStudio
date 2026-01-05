from __future__ import annotations
import os
os.chdir(r'/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')


from dataclasses import dataclass
from pathlib import Path
import json
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")


def _tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text or "")]


def load_corpus(path: Path) -> List[Dict[str, Any]]:
    path = Path(path)
    if path.is_dir():
        items: List[Dict[str, Any]] = []
        for p in sorted(path.glob("**/*")):
            if p.is_file() and p.suffix.lower() in {".jsonl", ".json"}:
                items.extend(load_corpus(p))
        return items
    if path.suffix.lower() == ".jsonl":
        out: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out
    if path.suffix.lower() == ".json":
        obj = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict) and "documents" in obj and isinstance(obj["documents"], list):
            return obj["documents"]
        raise ValueError(f"Unsupported JSON corpus shape in {path}")
    raise ValueError(f"Unsupported corpus format: {path}")


@dataclass(frozen=True)
class Evidence:
    doc_id: str
    score: float
    text: str
    meta: Dict[str, Any]


class RetrievalEngine:
    """
    Lightweight, deterministic retrieval over a small reference corpus.
    Supported methods: 'tfidf', 'bm25'
    Corpus item fields (recommended): {'id': str, 'text': str, 'meta': dict}
    """

    def __init__(self, method: str = "bm25"):
        self.method = (method or "bm25").lower()
        if self.method not in {"bm25", "tfidf"}:
            raise ValueError("method must be 'bm25' or 'tfidf'")
        self._docs: List[Dict[str, Any]] = []
        self._doc_ids: List[str] = []
        self._texts: List[str] = []
        self._metas: List[Dict[str, Any]] = []
        self._tfidf: Optional[TfidfVectorizer] = None
        self._tfidf_X = None
        self._bm25_vocab: Dict[str, int] = {}
        self._bm25_idf: Optional[np.ndarray] = None
        self._bm25_tf: Optional[List[Dict[int, int]]] = None
        self._bm25_dl: Optional[np.ndarray] = None
        self._bm25_avgdl: float = 0.0

    def build(self, documents: Sequence[Dict[str, Any]]) -> "RetrievalEngine":
        self._docs = list(documents)
        self._doc_ids, self._texts, self._metas = [], [], []
        for i, d in enumerate(self._docs):
            doc_id = str(d.get("id", f"doc_{i}"))
            text = str(d.get("text", ""))
            meta = d.get("meta") or {}
            self._doc_ids.append(doc_id)
            self._texts.append(text)
            self._metas.append(dict(meta))

        if self.method == "tfidf":
            self._tfidf = TfidfVectorizer(lowercase=True, token_pattern=r"(?u)\b\w+\b")
            self._tfidf_X = self._tfidf.fit_transform(self._texts)
        else:
            self._build_bm25()
        return self

    def _build_bm25(self, k1: float = 1.5, b: float = 0.75) -> None:
        toks = [_tokenize(t) for t in self._texts]
        vocab: Dict[str, int] = {}
        tf_list: List[Dict[int, int]] = []
        df: Dict[int, int] = {}
        dl = np.zeros(len(toks), dtype=np.int32)
        for i, ts in enumerate(toks):
            dl[i] = len(ts)
            tf: Dict[int, int] = {}
            seen: set[int] = set()
            for w in ts:
                j = vocab.setdefault(w, len(vocab))
                tf[j] = tf.get(j, 0) + 1
                if j not in seen:
                    df[j] = df.get(j, 0) + 1
                    seen.add(j)
            tf_list.append(tf)

        N = max(1, len(toks))
        idf = np.zeros(len(vocab), dtype=np.float64)
        for j, dfi in df.items():
            idf[j] = math.log(1.0 + (N - dfi + 0.5) / (dfi + 0.5))
        self._bm25_vocab = vocab
        self._bm25_idf = idf
        self._bm25_tf = tf_list
        self._bm25_dl = dl.astype(np.float64)
        self._bm25_avgdl = float(dl.mean()) if len(dl) else 0.0
        self._bm25_k1, self._bm25_b = float(k1), float(b)

    def query(self, text: str, top_k: int = 5) -> List[Evidence]:
        if not self._docs:
            return []
        top_k = max(1, int(top_k))
        if self.method == "tfidf":
            assert self._tfidf is not None and self._tfidf_X is not None
            q = self._tfidf.transform([text or ""])
            scores = (self._tfidf_X @ q.T).toarray().ravel()
        else:
            scores = self._score_bm25(text or "")
        order = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), self._doc_ids[i]))
        out: List[Evidence] = []
        for i in order[:top_k]:
            out.append(
                Evidence(
                    doc_id=self._doc_ids[i],
                    score=float(scores[i]),
                    text=self._texts[i],
                    meta=self._metas[i],
                )
            )
        return out

    def _score_bm25(self, query: str) -> np.ndarray:
        assert self._bm25_idf is not None and self._bm25_tf is not None and self._bm25_dl is not None
        q_terms = _tokenize(query)
        if not q_terms:
            return np.zeros(len(self._docs), dtype=np.float64)
        q_idx = [self._bm25_vocab.get(w) for w in q_terms]
        q_idx = [j for j in q_idx if j is not None]
        if not q_idx:
            return np.zeros(len(self._docs), dtype=np.float64)
        idf = self._bm25_idf
        k1, b = self._bm25_k1, self._bm25_b
        avgdl = self._bm25_avgdl or 1.0
        scores = np.zeros(len(self._docs), dtype=np.float64)
        for i, tf in enumerate(self._bm25_tf):
            dl = float(self._bm25_dl[i])
            denom_base = k1 * (1.0 - b + b * (dl / avgdl))
            s = 0.0
            for j in q_idx:
                f = tf.get(j, 0)
                if f:
                    s += float(idf[j]) * (f * (k1 + 1.0)) / (f + denom_base)
            scores[i] = s
        return scores


def build_engine_from_path(corpus_path: Path, method: str = "bm25") -> RetrievalEngine:
    docs = load_corpus(Path(corpus_path))
    return RetrievalEngine(method=method).build(docs)


if __name__ == "__main__":
    target_path = Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution").joinpath("src/claims_audit/retrieval.py")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    chunks = [
        Path(__file__).read_text(encoding="utf-8") if "__file__" in globals() else ""
    ]
    if chunks == [""]:
        raise SystemExit("Essential status: retrieval.py must be written by the generator script, not executed directly.")
    final_text = "\n".join(block.strip("\n") for block in chunks).strip() + "\n"
    target_path.write_text(final_text, encoding="utf-8")
    print("FILE_WRITTEN:src/claims_audit/retrieval.py")
    print(
        "DIR_STATE:"
        + json.dumps(
            sorted(
                str(p.relative_to(Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution")))
                for p in target_path.parent.glob("*")
                if p.is_file()
            )
        )
    )
    print("SUMMARY:Implemented deterministic BM25/TF-IDF retrieval with corpus loaders and top-k evidence selection.")
