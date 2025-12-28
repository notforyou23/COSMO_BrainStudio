from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class PsyPrimBase(BaseModel):
    model_config = dict(extra="forbid", populate_by_name=True)


class Agent(PsyPrimBase):
    name: str = Field(..., min_length=1, description="Person or organization name.")
    role: str | None = Field(None, description="Author/editor/translator/publisher/etc.")
    orcid: str | None = Field(None, description="ORCID iD, e.g., 0000-0002-1825-0097.")

    @field_validator("orcid")
    @classmethod
    def _orcid_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        s = v.strip()
        if len(s) != 19 or s[4] != "-" or s[9] != "-" or s[14] != "-":
            raise ValueError("Invalid ORCID format")
        return s


class Identifier(PsyPrimBase):
    scheme: Literal["doi", "isbn", "oclc", "lccn", "ark", "handle", "url", "other"]
    value: str = Field(..., min_length=1)
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def _url_for_url_scheme(self) -> "Identifier":
        if self.scheme == "url" and self.url is None:
            try:
                self.url = HttpUrl(self.value)  # type: ignore[arg-type]
            except Exception:
                raise ValueError("scheme=url requires a valid url or url-like value")
        return self


class DateSpan(PsyPrimBase):
    start: int | None = Field(None, ge=1, description="Inclusive year.")
    end: int | None = Field(None, ge=1, description="Inclusive year.")
    note: str | None = None

    @model_validator(mode="after")
    def _span_order(self) -> "DateSpan":
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("end must be >= start")
        return self


class EditionProvenance(PsyPrimBase):
    work_title: str = Field(..., min_length=1, description="Canonical work title.")
    edition_statement: str | None = Field(None, description="e.g., 2nd ed., revised.")
    publisher: str | None = None
    place: str | None = None
    year: int | None = Field(None, ge=1, le=date.today().year + 1)
    identifiers: list[Identifier] = Field(default_factory=list)
    source_url: HttpUrl | None = Field(None, description="Landing page for the edition.")
    notes: str | None = None


class TranslationProvenance(PsyPrimBase):
    source_language: str = Field(..., min_length=2, description="ISO-like language name/code.")
    target_language: str = Field(..., min_length=2)
    translator: list[Agent] = Field(default_factory=list)
    translation_title: str | None = None
    translation_year: int | None = Field(None, ge=1, le=date.today().year + 1)
    translation_publisher: str | None = None
    notes: str | None = None


class PaginationVariant(PsyPrimBase):
    label: str = Field(..., min_length=1, description="Human-friendly variant label.")
    system: Literal["page", "folio", "section", "paragraph", "chapter", "table", "other"] = "page"
    start: str | None = Field(None, description="Start locator, e.g., 'xv' or '1'.")
    end: str | None = Field(None, description="End locator.")
    note: str | None = None


class PublicDomainClaim(PsyPrimBase):
    jurisdiction: str = Field(..., min_length=2, description="e.g., US, EU, DE.")
    status: Literal["public_domain", "in_copyright", "unknown"] = "unknown"
    basis: Literal[
        "publication_year",
        "author_death_year",
        "government_work",
        "explicit_dedication",
        "license",
        "other",
    ] = "other"
    as_of: date | None = Field(None, description="Date the claim was assessed.")
    evidence_url: HttpUrl | None = None
    note: str | None = None


class Citation(PsyPrimBase):
    style: Literal["apa", "chicago", "mla", "bibtex", "ris", "csl-json", "other"] = "apa"
    full: str = Field(..., min_length=1, description="Rendered citation string.")
    in_text: str | None = Field(None, description="Optional in-text form.")
    accessed: date | None = None
    public_domain: list[PublicDomainClaim] = Field(default_factory=list)


class PrimarySourceRecord(PsyPrimBase):
    record_id: str = Field(..., min_length=1, description="Stable local ID/slug.")
    title: str = Field(..., min_length=1)
    creators: list[Agent] = Field(default_factory=list, description="Authors/creators.")
    contributors: list[Agent] = Field(default_factory=list, description="Editors, etc.")
    original_year: int | None = Field(None, ge=1, le=date.today().year + 1)
    edition: EditionProvenance | None = None
    translation: TranslationProvenance | None = None
    variant_pagination: list[PaginationVariant] = Field(default_factory=list)
    identifiers: list[Identifier] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    public_domain: list[PublicDomainClaim] = Field(default_factory=list, description="Work-level claims.")
    source_files: list[str] = Field(default_factory=list, description="Relative paths to scans/PDFs.")
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict, description="Extensible, non-normative fields.")

    @model_validator(mode="after")
    def _require_some_provenance(self) -> "PrimarySourceRecord":
        if not self.edition and not self.translation and not self.identifiers:
            raise ValueError("Provide at least one of: edition, translation, or identifiers")
        return self
