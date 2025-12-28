from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union
import json

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


@dataclass(frozen=True)
class Document:
    """Curated reference document."""
    doc_id: str
    title: str = ""
    text: str = ""
    source: str = ""
    url: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def search_text(self) -> str:
        parts = [self.title.strip(), self.text.strip()]
        return "\n\n".join([p for p in parts if p])


@dataclass(frozen=True)
class EvidenceSpan:
    """Evidence span anchored to a document by character offsets."""
    ev_id: str
    doc_id: str
    start: int
    end: int
    quote: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def slice_from(self, doc_text: str) -> str:
        if self.start < 0 or self.end < 0 or self.start > self.end:
            raise ValueError(f"Invalid span offsets for {self.ev_id}: {self.start}:{self.end}")
        if self.end > len(doc_text):
            raise ValueError(f"Span {self.ev_id} end offset beyond doc length: {self.end} > {len(doc_text)}")
        return doc_text[self.start:self.end]


@dataclass
class Corpus:
    """Small curated corpus with validation + search-ready text views."""
    documents: Dict[str, Document]
    evidence: Dict[str, EvidenceSpan]

    def validate(self) -> None:
        if len(self.documents) != len(set(self.documents)):
            raise ValueError("Duplicate document IDs detected")
        if len(self.evidence) != len(set(self.evidence)):
            raise ValueError("Duplicate evidence IDs detected")
        for ev in self.evidence.values():
            if ev.doc_id not in self.documents:
                raise ValueError(f"Evidence {ev.ev_id} references missing doc_id={ev.doc_id}")
            doc = self.documents[ev.doc_id]
            extracted = ev.slice_from(doc.text)
            if ev.quote:
                q = _norm_ws(ev.quote)
                ex = _norm_ws(extracted)
                if q and q not in ex and ex not in q:
                    raise ValueError(
                        f"Evidence {ev.ev_id} quote mismatch vs extracted span (doc_id={ev.doc_id})"
                    )

    def get_document(self, doc_id: str) -> Document:
        return self.documents[doc_id]

    def get_evidence(self, ev_id: str) -> EvidenceSpan:
        return self.evidence[ev_id]

    def evidence_text(self, ev_id: str) -> str:
        ev = self.get_evidence(ev_id)
        doc = self.get_document(ev.doc_id)
        return ev.slice_from(doc.text)

    def iter_search_items(self, include_documents: bool = True, include_evidence: bool = True) -> Iterator[Dict[str, Any]]:
        """Yields search-ready text rows: {kind,id,doc_id?,title?,text,meta}."""
        if include_documents:
            for d in self.documents.values():
                yield {
                    "kind": "document",
                    "id": d.doc_id,
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "text": d.search_text(),
                    "meta": {**d.meta, **{k: v for k, v in {"source": d.source, "url": d.url}.items() if v}},
                }
        if include_evidence:
            for ev in self.evidence.values():
                doc = self.documents[ev.doc_id]
                yield {
                    "kind": "evidence",
                    "id": ev.ev_id,
                    "doc_id": ev.doc_id,
                    "title": doc.title,
                    "text": ev.slice_from(doc.text),
                    "meta": {**ev.meta, "start": ev.start, "end": ev.end, "quote": ev.quote},
                }


def load_corpus(paths: Union[str, Path, Sequence[Union[str, Path]]]) -> Corpus:
    """Load corpus from one or more JSONL/YAML files.

    Accepted record types:
      - document: {type:'document', id/doc_id, title, text, source, url, meta}
      - evidence: {type:'evidence', id/ev_id, doc_id, start, end, quote, meta}
    YAML may contain either a list of records, or a dict with keys: documents/evidence.
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]
    docs: Dict[str, Document] = {}
    evs: Dict[str, EvidenceSpan] = {}
    for p in [Path(x) for x in paths]:
        _load_file_into(p, docs, evs)
    corpus = Corpus(documents=docs, evidence=evs)
    corpus.validate()
    return corpus


def _load_file_into(path: Path, docs: Dict[str, Document], evs: Dict[str, EvidenceSpan]) -> None:
    if not path.exists():
        raise FileNotFoundError(str(path))
    suf = path.suffix.lower()
    if suf in {".jsonl", ".ndjson"}:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                raise ValueError(f"Invalid JSON on {path.name}:{i}") from e
            _ingest_record(rec, docs, evs, src=str(path))
        return
    if suf in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML corpus files")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data is None:
            return
        if isinstance(data, dict) and ("documents" in data or "evidence" in data):
            for rec in (data.get("documents") or []):
                rec = {**rec, "type": rec.get("type", "document")}
                _ingest_record(rec, docs, evs, src=str(path))
            for rec in (data.get("evidence") or []):
                rec = {**rec, "type": rec.get("type", "evidence")}
                _ingest_record(rec, docs, evs, src=str(path))
            return
        if isinstance(data, list):
            for rec in data:
                _ingest_record(rec, docs, evs, src=str(path))
            return
        raise ValueError(f"Unsupported YAML top-level structure in {path}")
    if suf == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and ("documents" in data or "evidence" in data):
            for rec in (data.get("documents") or []):
                rec = {**rec, "type": rec.get("type", "document")}
                _ingest_record(rec, docs, evs, src=str(path))
            for rec in (data.get("evidence") or []):
                rec = {**rec, "type": rec.get("type", "evidence")}
                _ingest_record(rec, docs, evs, src=str(path))
            return
        if isinstance(data, list):
            for rec in data:
                _ingest_record(rec, docs, evs, src=str(path))
            return
        raise ValueError(f"Unsupported JSON top-level structure in {path}")
    raise ValueError(f"Unsupported corpus file extension: {path.suffix}")


def _ingest_record(rec: Any, docs: Dict[str, Document], evs: Dict[str, EvidenceSpan], src: str) -> None:
    if not isinstance(rec, dict):
        raise ValueError(f"Record must be an object (source={src})")
    rtype = (rec.get("type") or rec.get("kind") or "").strip().lower()
    if rtype == "document":
        doc_id = str(rec.get("doc_id") or rec.get("id") or "").strip()
        if not doc_id:
            raise ValueError(f"Document missing id/doc_id (source={src})")
        if doc_id in docs:
            raise ValueError(f"Duplicate document id={doc_id} (source={src})")
        docs[doc_id] = Document(
            doc_id=doc_id,
            title=str(rec.get("title") or ""),
            text=str(rec.get("text") or ""),
            source=str(rec.get("source") or ""),
            url=str(rec.get("url") or ""),
            meta=dict(rec.get("meta") or {}),
        )
        return
    if rtype == "evidence":
        ev_id = str(rec.get("ev_id") or rec.get("id") or "").strip()
        if not ev_id:
            raise ValueError(f"Evidence missing id/ev_id (source={src})")
        if ev_id in evs:
            raise ValueError(f"Duplicate evidence id={ev_id} (source={src})")
        doc_id = str(rec.get("doc_id") or "").strip()
        if not doc_id:
            raise ValueError(f"Evidence {ev_id} missing doc_id (source={src})")
        try:
            start = int(rec.get("start"))
            end = int(rec.get("end"))
        except Exception as e:
            raise ValueError(f"Evidence {ev_id} missing/invalid start/end (source={src})") from e
        evs[ev_id] = EvidenceSpan(
            ev_id=ev_id,
            doc_id=doc_id,
            start=start,
            end=end,
            quote=str(rec.get("quote") or ""),
            meta=dict(rec.get("meta") or {}),
        )
        return
    raise ValueError(f"Unknown record type={rtype!r} (source={src})")


def _norm_ws(s: str) -> str:
    return " ".join((s or "").split()).strip()
