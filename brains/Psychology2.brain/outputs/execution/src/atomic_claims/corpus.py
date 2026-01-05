"""Small curated reference corpus + provenance utilities.

This module provides:
- In-memory curated documents and citation metadata (Stage-1 slice).
- Passage indexing (stable passage ids per document).
- Provenance pointer parsing and resolution (doc/passages + optional citation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union
import re
@dataclass(frozen=True)
class Citation:
    id: str
    title: str
    author: str
    year: int
    url: str = ""


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    text: str
    citation_id: str
@dataclass(frozen=True)
class Passage:
    doc_id: str
    pid: int
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Provenance:
    doc_id: str
    pid: int
    citation_id: str = 
class ReferenceCorpus:
    def __init__(self, documents: Sequence[Document], citations: Sequence[Citation]):
        self.documents: Dict[str, Document] = {d.id: d for d in documents}
        self.citations: Dict[str, Citation] = {c.id: c for c in citations}
        missing = [d.citation_id for d in documents if d.citation_id not in self.citations]
        if missing:
            raise ValueError(f"Documents reference missing citation ids: {sorted(set(missing))}")
        self._passages: Dict[str, List[Passage]] = {}

    def index_passages(self, doc_id: str, *, max_chars: int = 800) -> List[Passage]:
        if doc_id in self._passages:
            return self._passages[doc_id]
        doc = self.documents[doc_id]
        txt = doc.text
        paras = [p.strip() for p in re.split(r"\n\s*\n", txt) if p.strip()]
        passages: List[Passage] = []
        cursor = 0
        pid = 1

        def _add(chunk: str, start: int, end: int) -> None:
            nonlocal pid
            passages.append(Passage(doc_id=doc_id, pid=pid, text=chunk.strip(), start=start, end=end))
            pid += 1

        for p in paras:
            # find paragraph in remaining text to compute approximate offsets
            idx = txt.find(p, cursor)
            if idx < 0:
                idx = cursor
            p_start, p_end = idx, idx + len(p)
            cursor = p_end
            if len(p) <= max_chars:
                _add(p, p_start, p_end)
            else:
                s = 0
                while s < len(p):
                    e = min(len(p), s + max_chars)
                    # prefer split on sentence boundary
                    if e < len(p):
                        m = re.search(r"[\.\?\!]\s", p[s:e][::-1])
                        if m:
                            back = m.start()
                            e = max(s + 80, e - back)
                    _add(p[s:e], p_start + s, p_start + e)
                    s = e
        self._passages[doc_id] = passages
        return passages

    def all_passages(self) -> List[Passage]:
        out: List[Passage] = []
        for did in sorted(self.documents):
            out.extend(self.index_passages(did))
        return out
_PTR_RE = re.compile(
    r"^(?:(?P<cite>[A-Za-z0-9_\-]+)@)?(?P<doc>[A-Za-z0-9_\-]+)(?:#p(?P<pid>\d+)|:(?P<pid2>\d+))$"
)


def parse_provenance_pointer(ptr: Union[str, Dict[str, object]]) -> Provenance:
    if isinstance(ptr, dict):
        doc = str(ptr.get("doc") or ptr.get("doc_id") or "")
        pid = int(ptr.get("pid") or ptr.get("passage") or 0)
        cite = str(ptr.get("citation") or ptr.get("citation_id") or "")
        if not doc or pid <= 0:
            raise ValueError(f"Invalid provenance dict: {ptr}")
        return Provenance(doc_id=doc, pid=pid, citation_id=cite)

    m = _PTR_RE.match(ptr.strip())
    if not m:
        raise ValueError(f"Invalid provenance pointer: {ptr!r}")
    cite = m.group("cite") or ""
    doc = m.group("doc")
    pid = int(m.group("pid") or m.group("pid2"))
    return Provenance(doc_id=doc, pid=pid, citation_id=cite)


def format_provenance_pointer(p: Provenance) -> str:
    base = f"{p.doc_id}#p{p.pid}"
    return f"{p.citation_id}@{base}" if p.citation_id else base
def resolve_provenance(
    corpus: ReferenceCorpus, ptr: Union[str, Dict[str, object], Provenance]
) -> Dict[str, object]:
    prov = ptr if isinstance(ptr, Provenance) else parse_provenance_pointer(ptr)
    doc = corpus.documents.get(prov.doc_id)
    if not doc:
        raise KeyError(f"Unknown document id: {prov.doc_id}")
    passages = corpus.index_passages(doc.id)
    if prov.pid <= 0 or prov.pid > len(passages):
        raise IndexError(f"Passage id out of range: {prov.doc_id} p{prov.pid}")
    passage = passages[prov.pid - 1]
    cite_id = prov.citation_id or doc.citation_id
    cite = corpus.citations.get(cite_id)
    if not cite:
        raise KeyError(f"Unknown citation id: {cite_id}")
    return {
        "pointer": format_provenance_pointer(Provenance(doc.id, passage.pid, cite.id)),
        "doc_id": doc.id,
        "doc_title": doc.title,
        "pid": passage.pid,
        "text": passage.text,
        "start": passage.start,
        "end": passage.end,
        "citation": {
            "id": cite.id,
            "title": cite.title,
            "author": cite.author,
            "year": cite.year,
            "url": cite.url,
        },
    }
def build_curated_corpus() -> ReferenceCorpus:
    citations = [
        Citation(
            id="stanford_nudge_2023",
            title="Choice Architecture and Nudging (overview)",
            author="Stanford Encyclopedia of Philosophy (entry summary)",
            year=2023,
            url="https://plato.stanford.edu/",
        ),
        Citation(
            id="kahneman_2011",
            title="Thinking, Fast and Slow",
            author="Daniel Kahneman",
            year=2011,
            url="",
        ),
        Citation(
            id="nih_placebo_2021",
            title="Placebo Effect (overview)",
            author="National Institutes of Health",
            year=2021,
            url="https://www.nih.gov/",
        ),
    ]

    documents = [
        Document(
            id="doc_nudge",
            title="Nudges and defaults (curated excerpt)",
            citation_id="stanford_nudge_2023",
            text=(
                "A default option is the option that takes effect if a person does nothing.\n\n"
                "Changing the default can substantially change the choices people make.\n\n"
                "A nudge is an intervention that changes behavior in a predictable way without forbidding options or significantly changing incentives."
            ),
        ),
        Document(
            id="doc_cogload",
            title="Cognitive load and heuristics (curated excerpt)",
            citation_id="kahneman_2011",
            text=(
                "When people are under time pressure or cognitive load, they are more likely to rely on simple heuristics.\n\n"
                "Heuristics can be useful, but they can also lead to systematic biases.\n\n"
                "Slower, more deliberative reasoning requires attention and effort."
            ),
        ),
        Document(
            id="doc_placebo",
            title="Placebo effects (curated excerpt)",
            citation_id="nih_placebo_2021",
            text=(
                "A placebo is an inactive treatment that can sometimes improve a patient's condition.\n\n"
                "Placebo effects are thought to be related to expectations and conditioning.\n\n"
                "Placebo responses can occur even when people know they are receiving a placebo in some contexts."
            ),
        ),
    ]
    return ReferenceCorpus(documents=documents, citations=citations)
def corpus_manifest(corpus: ReferenceCorpus) -> Dict[str, object]:
    return {
        "documents": [
            {"id": d.id, "title": d.title, "citation_id": d.citation_id}
            for d in sorted(corpus.documents.values(), key=lambda x: x.id)
        ],
        "citations": [
            {"id": c.id, "title": c.title, "author": c.author, "year": c.year, "url": c.url}
            for c in sorted(corpus.citations.values(), key=lambda x: x.id)
        ],
        "passage_counts": {did: len(corpus.index_passages(did)) for did in sorted(corpus.documents)},
    }
