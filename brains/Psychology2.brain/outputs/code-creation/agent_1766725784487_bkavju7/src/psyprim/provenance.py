from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
import hashlib
import re

ISO = "%Y-%m-%dT%H:%M:%SZ"

def utcnow() -> str:
    return datetime.now(timezone.utc).strftime(ISO)

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def content_fingerprint(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(_norm(p).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]

def next_variant(existing: Iterable[str] = ()) -> str:
    mx = 0
    for v in existing:
        m = re.fullmatch(r"v(\d{3,})", (v or "").strip())
        if m:
            mx = max(mx, int(m.group(1)))
    return f"v{mx+1:03d}"

@dataclass(frozen=True)
class ProvenanceFlag:
    code: str
    label: str
    severity: str = "info"  # info|warn|error
    details: str = ""

@dataclass
class AuditEvent:
    ts: str
    actor: str
    action: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProvenanceRecord:
    item_id: str
    variant: str = "v001"
    fingerprint: str = ""
    flags: List[ProvenanceFlag] = field(default_factory=list)
    audit: List[AuditEvent] = field(default_factory=list)

    def add_event(self, actor: str, action: str, **details: Any) -> None:
        self.audit.append(AuditEvent(ts=utcnow(), actor=_norm(actor) or "unknown", action=_norm(action), details=details))

    def add_flag(self, code: str, label: str, severity: str = "info", details: str = "") -> None:
        self.flags.append(ProvenanceFlag(code=code, label=_norm(label), severity=severity, details=_norm(details)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "variant": self.variant,
            "fingerprint": self.fingerprint,
            "flags": [f.__dict__ for f in self.flags],
            "audit": [a.__dict__ for a in self.audit],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProvenanceRecord":
        pr = cls(item_id=d["item_id"], variant=d.get("variant", "v001"), fingerprint=d.get("fingerprint", ""))
        pr.flags = [ProvenanceFlag(**f) for f in d.get("flags", [])]
        pr.audit = [AuditEvent(**a) for a in d.get("audit", [])]
        return pr

class RepositoryResolver:
    def __init__(self, rules: Optional[List[Tuple[str, str]]] = None):
        self.rules: List[Tuple[re.Pattern[str], str]] = []
        for pat, tmpl in (rules or self.default_rules()):
            self.rules.append((re.compile(pat, re.I), tmpl))

    @staticmethod
    def default_rules() -> List[Tuple[str, str]]:
        return [
            (r"^https?://(www\.)?doi\.org/(.+)$", "DOI:https://doi.org/\2"),
            (r"^doi:(.+)$", "DOI:https://doi.org/\1"),
            (r"^(?i)ia:([\w\-\.]+)$", "Internet Archive:https://archive.org/details/\1"),
            (r"^(?i)ht:([\w\.:/\-]+)$", "HathiTrust:https://hdl.handle.net/2027/\1"),
            (r"^(?i)jstor:(\d+)$", "JSTOR:https://www.jstor.org/stable/\1"),
            (r"^https?://", "URL:\g<0>"),
        ]

    def resolve(self, repo_id_or_url: str) -> Tuple[str, str]:
        s = _norm(repo_id_or_url)
        for pat, tmpl in self.rules:
            if pat.search(s):
                out = pat.sub(tmpl, s)
                label, url = out.split(":", 1)
                return _norm(label), _norm(url)
        return "Repository", s

def compute_flags(meta: Dict[str, Any]) -> List[ProvenanceFlag]:
    m = {k: (v if v is not None else "") for k, v in (meta or {}).items()}
    flags: List[ProvenanceFlag] = []
    if not _norm(str(m.get("source_type", ""))):
        flags.append(ProvenanceFlag("P001", "Missing source_type", "warn", "e.g., scan|typeset|transcript|note"))
    if not _norm(str(m.get("repository", ""))) and not _norm(str(m.get("repository_id", ""))) and not _norm(str(m.get("url", ""))):
        flags.append(ProvenanceFlag("P002", "Missing repository locator", "error", "provide repository_id or url"))
    if _norm(str(m.get("ocr", ""))).lower() in {"yes", "true", "1"} and not _norm(str(m.get("ocr_quality", ""))):
        flags.append(ProvenanceFlag("P003", "OCR used without quality note", "warn", "record confidence or error rate"))
    if _norm(str(m.get("transcribed", ""))).lower() in {"yes", "true", "1"} and not _norm(str(m.get("transcriber", ""))):
        flags.append(ProvenanceFlag("P004", "Transcription missing transcriber", "warn", "record who transcribed"))
    if not _norm(str(m.get("accessed", ""))):
        flags.append(ProvenanceFlag("P005", "Missing accessed date", "warn", "record YYYY-MM-DD"))
    return flags

def build_record(item_id: str, meta: Dict[str, Any], existing_variants: Iterable[str] = (), actor: str = "system") -> ProvenanceRecord:
    pr = ProvenanceRecord(item_id=_norm(item_id), variant=next_variant(existing_variants))
    pr.fingerprint = content_fingerprint(
        str(meta.get("title", "")), str(meta.get("author", "")), str(meta.get("year", "")), str(meta.get("repository_id", meta.get("url", "")))
    )
    pr.flags = compute_flags(meta)
    pr.add_event(actor, "record_created", item_id=pr.item_id, variant=pr.variant, fingerprint=pr.fingerprint)
    return pr

def citation_string(meta: Dict[str, Any], resolver: Optional[RepositoryResolver] = None) -> str:
    m = meta or {}
    author = _norm(str(m.get("author", ""))) or "Unknown"
    year = _norm(str(m.get("year", ""))) or "n.d."
    title = _norm(str(m.get("title", ""))) or "Untitled"
    accessed = _norm(str(m.get("accessed", "")))
    locator = _norm(str(m.get("repository_id", ""))) or _norm(str(m.get("url", ""))) or _norm(str(m.get("repository", "")))
    res = resolver or RepositoryResolver()
    repo_label, repo_url = res.resolve(locator) if locator else ("Repository", "")
    parts = [f"{author} ({year}). {title}."]
    if repo_url:
        parts.append(f"{repo_label} {repo_url}.")
    elif repo_label and locator:
        parts.append(f"{repo_label}: {locator}.")
    if accessed:
        parts.append(f"Accessed {accessed}.")
    if _norm(str(m.get('variant', ''))):
        parts.append(f"Variant {m.get('variant')}.")
    return " ".join([p for p in parts if p]).strip()
