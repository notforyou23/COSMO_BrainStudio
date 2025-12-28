from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional, Union
import json
import re
def _clean(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s or None


def _today_iso() -> str:
    return date.today().isoformat()


def _iso_date(d: Optional[Union[str, date, datetime]]) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d.isoformat()
    if isinstance(d, datetime):
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.date().isoformat()
    s = _clean(str(d))
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date().isoformat() if fmt != "%Y" else f"{dt.year:04d}-01-01"
        except ValueError:
            pass
    return s
@dataclass(frozen=True)
class CitationRecord:
    title: str
    author: Optional[str] = None
    year: Optional[Union[int, str]] = None
    publisher: Optional[str] = None
    place: Optional[str] = None
    edition: Optional[str] = None
    translator: Optional[str] = None
    original_title: Optional[str] = None
    original_year: Optional[Union[int, str]] = None
    pages: Optional[str] = None  # supports variant pagination strings
    archive: Optional[str] = None
    archive_id: Optional[str] = None  # e.g., IA identifier, HathiTrust ID
    url: Optional[str] = None
    accessed: Optional[Union[str, date, datetime]] = None
    public_domain: Optional[bool] = None

    def normalized(self) -> "CitationRecord":
        d = {k: _clean(v) if isinstance(v, str) else v for k, v in asdict(self).items()}
        if isinstance(d.get("year"), str):
            d["year"] = _clean(d["year"])
        if isinstance(d.get("original_year"), str):
            d["original_year"] = _clean(d["original_year"])
        d["accessed"] = _iso_date(d.get("accessed")) or _today_iso()
        return CitationRecord(**d)

    def to_text(self, style: str = "psyprim") -> str:
        rec = self.normalized()
        y = f"{rec.year}" if rec.year is not None else "n.d."
        author = rec.author or "Unknown author"
        parts = [f"{author} ({y}).", f"{rec.title}."]
        if rec.edition:
            parts.append(f"{rec.edition}.")
        if rec.translator:
            parts.append(f"Trans. {rec.translator}.")
        pub_bits = [b for b in [rec.place, rec.publisher] if b]
        if pub_bits:
            parts.append(": ".join(pub_bits) + ".")
        if rec.original_title or rec.original_year:
            oy = f"{rec.original_year}" if rec.original_year is not None else "n.d."
            ot = rec.original_title or "Original"
            parts.append(f"[Original: {ot}, {oy}].")
        if rec.pages:
            parts.append(f"Pages: {rec.pages}.")
        loc_bits = []
        if rec.archive:
            loc_bits.append(rec.archive)
        if rec.archive_id:
            loc_bits.append(f"ID: {rec.archive_id}")
        if rec.url:
            loc_bits.append(rec.url)
        if loc_bits:
            parts.append("Retrieved from " + "; ".join(loc_bits) + f" (accessed {rec.accessed}).")
        else:
            parts.append(f"Accessed {rec.accessed}.")
        if rec.public_domain is True:
            parts.append("Public-domain source.")
        return " ".join(p.strip() for p in parts if p and p.strip())

    def to_csl_json(self, csl_id: Optional[str] = None) -> Dict[str, Any]:
        rec = self.normalized()
        y = None
        if rec.year is not None:
            try:
                y = int(str(rec.year).strip()[:4])
            except Exception:
                y = None
        issued = {"date-parts": [[y]]} if y else None
        item: Dict[str, Any] = {
            "id": csl_id or (rec.archive_id or rec.url or rec.title),
            "type": "book",
            "title": rec.title,
        }
        if rec.author:
            item["author"] = [{"literal": rec.author}]
        if issued:
            item["issued"] = issued
        if rec.publisher:
            item["publisher"] = rec.publisher
        if rec.place:
            item["publisher-place"] = rec.place
        if rec.edition:
            item["edition"] = rec.edition
        if rec.translator:
            item["translator"] = [{"literal": rec.translator}]
        if rec.pages:
            item["page"] = rec.pages
        if rec.url:
            item["URL"] = rec.url
        if rec.accessed:
            item["accessed"] = {"raw": str(rec.accessed)}
        extra = []
        if rec.archive:
            extra.append(f"archive: {rec.archive}")
        if rec.archive_id:
            extra.append(f"archive_id: {rec.archive_id}")
        if rec.public_domain is True:
            extra.append("public_domain: true")
        if rec.original_title:
            extra.append(f"original_title: {rec.original_title}")
        if rec.original_year is not None:
            extra.append(f"original_year: {rec.original_year}")
        if extra:
            item["note"] = "; ".join(extra)
        return item
def make_citation(data: Union[CitationRecord, Dict[str, Any]], style: str = "psyprim") -> str:
    rec = data if isinstance(data, CitationRecord) else CitationRecord(**data)
    return rec.to_text(style=style)


def export_citation(data: Union[CitationRecord, Dict[str, Any]], fmt: str = "csl-json") -> str:
    rec = data if isinstance(data, CitationRecord) else CitationRecord(**data)
    fmt = (fmt or "csl-json").lower().strip()
    if fmt in {"csl", "csl-json", "csljson"}:
        return json.dumps(rec.to_csl_json(), ensure_ascii=False, indent=2) + "\n"
    if fmt in {"text", "txt"}:
        return rec.to_text() + "\n"
    raise ValueError(f"Unsupported export format: {fmt}")
