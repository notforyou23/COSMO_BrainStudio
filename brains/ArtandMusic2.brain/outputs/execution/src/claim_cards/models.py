from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _missing(path: str) -> str:
    return f"missing_or_empty:{path}"


@dataclass(frozen=True)
class ClaimContext:
    speaker: str
    date: str
    link: str

    def missing_fields(self) -> List[str]:
        m: List[str] = []
        if not _is_nonempty_str(self.speaker):
            m.append(_missing("context.speaker"))
        if not _is_nonempty_str(self.date):
            m.append(_missing("context.date"))
        if not _is_nonempty_str(self.link):
            m.append(_missing("context.link"))
        return m

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ClaimContext":
        if not isinstance(d, dict):
            raise TypeError("context must be an object")
        return cls(
            speaker=str(d.get("speaker", "") if d.get("speaker") is not None else ""),
            date=str(d.get("date", "") if d.get("date") is not None else ""),
            link=str(d.get("link", "") if d.get("link") is not None else ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"speaker": self.speaker, "date": self.date, "link": self.link}


AnchorKind = Literal["url", "doi", "file", "other"]


@dataclass(frozen=True)
class ProvenanceAnchor:
    kind: AnchorKind
    uri: str
    quote: str
    note: Optional[str] = None

    def missing_fields(self) -> List[str]:
        m: List[str] = []
        if self.kind not in ("url", "doi", "file", "other"):
            m.append("invalid:provenance.kind")
        if not _is_nonempty_str(self.uri):
            m.append(_missing("provenance.uri"))
        if not _is_nonempty_str(self.quote):
            m.append(_missing("provenance.quote"))
        return m

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProvenanceAnchor":
        if not isinstance(d, dict):
            raise TypeError("provenance must be an object")
        kind = d.get("kind", "other")
        if kind is None:
            kind = "other"
        return cls(
            kind=str(kind),  # type: ignore[arg-type]
            uri=str(d.get("uri", "") if d.get("uri") is not None else ""),
            quote=str(d.get("quote", "") if d.get("quote") is not None else ""),
            note=(None if d.get("note") in (None, "") else str(d.get("note"))),
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"kind": self.kind, "uri": self.uri, "quote": self.quote}
        if self.note:
            out["note"] = self.note
        return out


@dataclass(frozen=True)
class ClaimCard:
    claim_text: str
    context: ClaimContext
    provenance: ProvenanceAnchor
    claim_id: Optional[str] = None
    tags: Sequence[str] = field(default_factory=tuple)

    def missing_fields(self) -> List[str]:
        m: List[str] = []
        if not _is_nonempty_str(self.claim_text):
            m.append(_missing("claim_text"))
        m.extend(self.context.missing_fields())
        m.extend(self.provenance.missing_fields())
        if self.claim_id is not None and not _is_nonempty_str(self.claim_id):
            m.append(_missing("claim_id"))
        if not isinstance(self.tags, (list, tuple)):
            m.append("invalid:tags")
        else:
            for i, t in enumerate(self.tags):
                if not _is_nonempty_str(t):
                    m.append(f"invalid:tags[{i}]")
        return m

    def validate(self) -> None:
        missing = self.missing_fields()
        if missing:
            raise ValueError("abstain:required_fields_missing:" + ";".join(missing))

    def abstain_reasons(self) -> List[str]:
        return self.missing_fields()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ClaimCard":
        if not isinstance(d, dict):
            raise TypeError("claim card must be an object")
        context = ClaimContext.from_dict(d.get("context") or {})
        provenance = ProvenanceAnchor.from_dict(d.get("provenance") or {})
        tags = d.get("tags") or ()
        if isinstance(tags, str):
            tags = (tags,)
        elif isinstance(tags, list):
            tags = tuple(tags)
        elif isinstance(tags, tuple):
            pass
        else:
            tags = ()
        return cls(
            claim_text=str(d.get("claim_text", "") if d.get("claim_text") is not None else ""),
            context=context,
            provenance=provenance,
            claim_id=(None if d.get("claim_id") in (None, "") else str(d.get("claim_id"))),
            tags=tags,
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "claim_text": self.claim_text,
            "context": self.context.to_dict(),
            "provenance": self.provenance.to_dict(),
        }
        if self.claim_id:
            out["claim_id"] = self.claim_id
        if self.tags:
            out["tags"] = list(self.tags)
        return out
