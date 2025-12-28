from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import hashlib
import json
import math
import re
import urllib.request
from html.parser import HTMLParser


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")
_WS_RE = re.compile(r"\s+")


def _norm_ws(s: str) -> str:
    return _WS_RE.sub(" ", s).strip()


def _tokens(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _stable_id(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", "ignore"))
        h.update(b"\0")
    return h.hexdigest()[:16]


@dataclass(frozen=True)
class Passage:
    passage_id: str
    text: str
    score: float
    provenance: Dict[str, Any]  # e.g., {"source":"local|web","doc_id":..., "url":..., "doi":..., "span":[start,end]}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._buf: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            s = _norm_ws(data)
            if s:
                self._buf.append(s)

    def text(self) -> str:
        return " ".join(self._buf)


def _split_passages(text: str, max_chars: int = 900, overlap: int = 120) -> List[Tuple[int, int, str]]:
    t = _norm_ws(text)
    if not t:
        return []
    out: List[Tuple[int, int, str]] = []
    i = 0
    n = len(t)
    while i < n:
        j = min(n, i + max_chars)
        if j < n:
            k = t.rfind(". ", i + max(200, max_chars // 2), j)
            if k != -1:
                j = k + 1
        span = t[i:j].strip()
        if span:
            out.append((i, j, span))
        i = max(i + 1, j - overlap)
    return out


def fetch_url_text(url: str, timeout: float = 10.0, max_bytes: int = 2_000_000) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "borderline-qa-retriever/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(max_bytes)
    try:
        html = raw.decode("utf-8")
    except UnicodeDecodeError:
        html = raw.decode("latin-1", "ignore")
    p = _TextExtractor()
    p.feed(html)
    return p.text()
class TfidfIndex:
    def __init__(self, docs: Sequence[Dict[str, Any]]) -> None:
        self.docs = list(docs)
        self.doc_tokens: List[List[str]] = []
        self.df: Dict[str, int] = {}
        for d in self.docs:
            toks = _tokens(d.get("text", "") or "")
            self.doc_tokens.append(toks)
            seen = set(toks)
            for t in seen:
                self.df[t] = self.df.get(t, 0) + 1
        self.N = max(1, len(self.docs))
        self.idf: Dict[str, float] = {t: math.log((self.N + 1) / (df + 1)) + 1.0 for t, df in self.df.items()}

    def score(self, query: str, k: int = 8) -> List[Tuple[int, float]]:
        q = _tokens(query)
        if not q:
            return []
        qtf: Dict[str, int] = {}
        for t in q:
            qtf[t] = qtf.get(t, 0) + 1
        qv: Dict[str, float] = {t: qtf[t] * self.idf.get(t, 0.0) for t in qtf}
        qnorm = math.sqrt(sum(v * v for v in qv.values())) or 1.0
        out: List[Tuple[int, float]] = []
        for i, toks in enumerate(self.doc_tokens):
            tf: Dict[str, int] = {}
            for t in toks:
                if t in qv:
                    tf[t] = tf.get(t, 0) + 1
            if not tf:
                continue
            dv = {t: tf[t] * self.idf.get(t, 0.0) for t in tf}
            dnorm = math.sqrt(sum(v * v for v in dv.values())) or 1.0
            dot = sum(qv[t] * dv.get(t, 0.0) for t in qv)
            out.append((i, dot / (qnorm * dnorm)))
        out.sort(key=lambda x: x[1], reverse=True)
        return out[:k]


def load_local_corpus(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for p in paths:
        if p.is_dir():
            for fp in sorted(p.glob("**/*")):
                if fp.is_file():
                    docs.extend(load_local_corpus([fp]))
            continue
        suf = p.suffix.lower()
        if suf in {".jsonl", ".json"}:
            txt = p.read_text(encoding="utf-8", errors="ignore").strip()
            if not txt:
                continue
            if suf == ".json":
                obj = json.loads(txt)
                items = obj if isinstance(obj, list) else [obj]
            else:
                items = [json.loads(line) for line in txt.splitlines() if line.strip()]
            for it in items:
                if isinstance(it, dict) and it.get("text"):
                    it = dict(it)
                    it.setdefault("doc_id", it.get("id") or it.get("doc_id") or _stable_id(str(p), it.get("title", ""), it.get("url", "")))
                    it.setdefault("source", "local")
                    docs.append(it)
        else:
            text = p.read_text(encoding="utf-8", errors="ignore")
            doc_id = _stable_id(str(p))
            docs.append({"doc_id": doc_id, "text": text, "url": None, "doi": None, "title": p.name, "source": "local"})
    return docs
class Retriever:
    def __init__(
        self,
        corpus_paths: Optional[Sequence[str | Path]] = None,
        default_urls: Optional[Sequence[str]] = None,
        passage_chars: int = 900,
        passage_overlap: int = 120,
    ) -> None:
        self.passage_chars = int(passage_chars)
        self.passage_overlap = int(passage_overlap)
        self.default_urls = list(default_urls or [])
        self.docs: List[Dict[str, Any]] = []
        if corpus_paths:
            paths = [Path(p) for p in corpus_paths]
            self.docs = load_local_corpus(paths)
        self.index = TfidfIndex(self.docs) if self.docs else None

    def _doc_passages(self, doc: Dict[str, Any], base_score: float, limit: int) -> List[Passage]:
        text = doc.get("text", "") or ""
        spans = _split_passages(text, max_chars=self.passage_chars, overlap=self.passage_overlap)
        out: List[Passage] = []
        for (a, b, seg) in spans[: max(1, limit)]:
            url = doc.get("url") or doc.get("source_url")
            doi = doc.get("doi")
            pid = _stable_id(doc.get("doc_id", ""), url or "", doi or "", str(a), str(b), seg[:40])
            prov = {
                "source": doc.get("source", "local"),
                "doc_id": doc.get("doc_id"),
                "title": doc.get("title"),
                "url": url,
                "doi": doi,
                "span": [int(a), int(b)],
                "char_start": int(a),
                "char_end": int(b),
            }
            out.append(Passage(passage_id=pid, text=seg, score=float(base_score), provenance=prov))
        return out

    def retrieve(
        self,
        query: str,
        k: int = 8,
        urls: Optional[Sequence[str]] = None,
        per_doc_passages: int = 2,
        fetch_web: bool = False,
        timeout: float = 10.0,
    ) -> List[Passage]:
        out: List[Passage] = []
        if self.index:
            ranked = self.index.score(query, k=max(8, k))
            for i, s in ranked:
                out.extend(self._doc_passages(self.docs[i], base_score=s, limit=per_doc_passages))
        if fetch_web:
            for u in list(urls or self.default_urls)[: max(0, k)]:
                try:
                    txt = fetch_url_text(u, timeout=timeout)
                except Exception:
                    continue
                doc = {"doc_id": _stable_id("web", u), "text": txt, "url": u, "doi": None, "title": None, "source": "web"}
                out.extend(self._doc_passages(doc, base_score=0.0, limit=per_doc_passages))
        # re-rank passages by query overlap (cheap) + base score
        qt = set(_tokens(query))
        rescored: List[Tuple[float, Passage]] = []
        for p in out:
            pt = _tokens(p.text)
            overlap = sum(1 for t in pt if t in qt)
            score = p.score + (overlap / max(20.0, len(pt) or 1.0))
            rescored.append((score, Passage(p.passage_id, p.text, float(score), p.provenance)))
        rescored.sort(key=lambda x: x[0], reverse=True)
        seen: set[str] = set()
        final: List[Passage] = []
        for _, p in rescored:
            if p.passage_id in seen:
                continue
            seen.add(p.passage_id)
            final.append(p)
            if len(final) >= k:
                break
        return final
