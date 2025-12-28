from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class IdentifierType(str, Enum):
    doi = "doi"
    isbn = "isbn"
    oclc = "oclc"
    ark = "ark"
    handle = "handle"
    url = "url"
    other = "other"


class RepositoryKind(str, Enum):
    public_domain = "public_domain"
    library = "library"
    publisher = "publisher"
    personal = "personal"
    other = "other"


class NormalizedIdentifier(BaseModel):
    type: IdentifierType = Field(..., description="Identifier namespace/type.")
    value: str = Field(..., min_length=1, description="Normalized identifier value.")
    note: Optional[str] = Field(None, description="Optional clarification/parse notes.")


class RepositoryCitation(BaseModel):
    kind: RepositoryKind = Field(..., description="Repository/source class.")
    name: str = Field(..., min_length=1, description="Repository name (e.g., Internet Archive).")
    item_title: Optional[str] = Field(None, description="Item title as hosted in repository.")
    url: Optional[HttpUrl] = Field(None, description="Canonical landing URL for the hosted item.")
    access_date: Optional[str] = Field(
        None, description="Access date in ISO 8601 (YYYY-MM-DD) if applicable."
    )
    identifiers: List[NormalizedIdentifier] = Field(
        default_factory=list, description="Repository/public identifiers for item."
    )
    license: Optional[str] = Field(
        None, description="Repository-reported license/public-domain statement."
    )
    checksum: Optional[str] = Field(
        None, description="Optional checksum for exact file version (e.g., sha256:...)."
    )


class EditionProvenance(BaseModel):
    work_title: str = Field(..., min_length=1, description="Canonical work title.")
    author: Optional[str] = Field(None, description="Work author(s) as cited.")
    original_publication_year: Optional[int] = Field(None, ge=1400, le=2100)
    edition_year: Optional[int] = Field(None, ge=1400, le=2100)
    edition_statement: Optional[str] = Field(
        None, description="Edition statement (e.g., 2nd ed., revised)."
    )
    publisher: Optional[str] = Field(None)
    place_of_publication: Optional[str] = Field(None)
    language: Optional[str] = Field(None, description="Language of the cited text (BCP-47 preferred).")
    translation: bool = Field(False, description="True if the cited text is a translation.")
    translator: Optional[str] = Field(None, description="Translator(s) if translation.")
    source_language: Optional[str] = Field(
        None, description="Source language of the translated work (BCP-47 preferred)."
    )
    identifiers: List[NormalizedIdentifier] = Field(default_factory=list)
    repository: Optional[RepositoryCitation] = Field(
        None, description="Public-domain repository citation when applicable."
    )
    notes: Optional[str] = Field(None, description="Free-text provenance clarifications.")


class PageLocator(BaseModel):
    kind: Literal["page"] = "page"
    page: Union[int, str] = Field(..., description="Printed page number or label (e.g., 'xii').")
    page_variant: Optional[str] = Field(
        None, description="Variant label when page numbering differs across editions/scans."
    )


class ParagraphLocator(BaseModel):
    kind: Literal["paragraph"] = "paragraph"
    paragraph: Union[int, str] = Field(..., description="Paragraph index/label within a section.")
    anchor_text: Optional[str] = Field(
        None, description="Short quote to anchor the paragraph when numbering varies."
    )


class SectionLocator(BaseModel):
    kind: Literal["section"] = "section"
    label: str = Field(..., description="Section label (e.g., chapter/heading) to disambiguate.")
    start: Optional[Union[PageLocator, ParagraphLocator]] = None
    end: Optional[Union[PageLocator, ParagraphLocator]] = None


LocationSpecifier = Union[PageLocator, ParagraphLocator, SectionLocator]


class CitationProvenance(BaseModel):
    in_text: Optional[str] = Field(None, description="Raw citation string as written in manuscript.")
    parsed_identifiers: List[NormalizedIdentifier] = Field(
        default_factory=list, description="Identifiers inferred or supplied for the citation."
    )
    location: Optional[LocationSpecifier] = Field(
        None, description="Where in the primary source the claim is supported."
    )
    location_alt: List[LocationSpecifier] = Field(
        default_factory=list, description="Known variant locators across editions/translations."
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Evidence strings (e.g., filename cues, OCR markers) supporting provenance.",
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in provenance inference.")


class PrimarySourceMetadata(BaseModel):
    provenance: EditionProvenance = Field(..., description="Edition/translation provenance record.")
    citation: Optional[CitationProvenance] = Field(
        None, description="How the primary source was cited/located in a manuscript."
    )
    public_domain_ok: Optional[bool] = Field(
        None, description="Whether the source is believed to be public domain in relevant jurisdiction."
    )
    rights_note: Optional[str] = Field(None, description="Optional legal/ethical handling note.")


def json_schema(model: type[BaseModel]) -> Dict[str, Any]:
    return model.model_json_schema()


def export_json_schema(path: str | Path, model: type[BaseModel]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(json_schema(model), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p
