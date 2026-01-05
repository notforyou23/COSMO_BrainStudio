"""Curated registry of primary-source repositories + identifier patterns.

Used by lightweight detectors and roadmap outputs to recognize citations/links to
canonical sources across common scholarly repositories and identifier systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Pattern, Tuple
import re
@dataclass(frozen=True)
class IdentifierPattern:
    """A regex pattern for detecting an identifier or repository URL."""

    key: str
    regex: str
    kind: str  # "id" or "url"
    example: str = ""
    notes: str = ""

    def compile(self, flags: int = re.IGNORECASE) -> Pattern[str]:
        return re.compile(self.regex, flags)


@dataclass(frozen=True)
class Repository:
    key: str
    label: str
    domains: Tuple[str, ...]
    patterns: Tuple[IdentifierPattern, ...]
# Common identifier patterns (not repository-specific).
COMMON_PATTERNS: Tuple[IdentifierPattern, ...] = (
    IdentifierPattern(
        key="doi",
        kind="id",
        regex=r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b",
        example="10.1037/h0034574",
        notes="Case-insensitive; matches DOI core form (not necessarily URL).",
    ),
    IdentifierPattern(
        key="pmid",
        kind="id",
        regex=r"\bPMID\s*:\s*(\d{6,9})\b|\b(\d{6,9})\s*\(PMID\)\b",
        example="PMID: 12345678",
    ),
    IdentifierPattern(
        key="pmcid",
        kind="id",
        regex=r"\bPMCID\s*:\s*(PMC\d+)\b|\b(PMC\d+)\b",
        example="PMCID: PMC1234567",
    ),
    IdentifierPattern(
        key="isbn",
        kind="id",
        regex=r"\bISBN(?:-1[03])?\s*:\s*([0-9Xx][- 0-9Xx]{9,16})\b",
        example="ISBN: 978-0-1234-5678-9",
        notes="Loose ISBN-10/13 capture for books/editions.",
    ),
)
# Repository registry (curated, minimal, testable).
REPOSITORIES: Dict[str, Repository] = {
    "doi": Repository(
        key="doi",
        label="DOI resolver / publisher landing page",
        domains=("doi.org", "dx.doi.org"),
        patterns=(
            IdentifierPattern(
                key="doi_url",
                kind="url",
                regex=r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)",
                example="https://doi.org/10.1037/h0034574",
            ),
        ),
    ),
    "jstor": Repository(
        key="jstor",
        label="JSTOR",
        domains=("jstor.org", "www.jstor.org"),
        patterns=(
            IdentifierPattern(
                key="jstor_stable_url",
                kind="url",
                regex=r"https?://(?:www\.)?jstor\.org/stable/(\d+)",
                example="https://www.jstor.org/stable/1234567",
                notes="JSTOR stable URL.",
            ),
            IdentifierPattern(
                key="jstor_stable_id",
                kind="id",
                regex=r"\bstable\s*:?\s*(\d{5,})\b",
                example="stable: 1234567",
            ),
        ),
    ),
    "hathitrust": Repository(
        key="hathitrust",
        label="HathiTrust",
        domains=("hathitrust.org", "www.hathitrust.org"),
        patterns=(
            IdentifierPattern(
                key="hathi_pt_url",
                kind="url",
                regex=r"https?://(?:www\.)?hathitrust\.org/cgi/pt\?id=([^&#\s]+)",
                example="https://hathitrust.org/cgi/pt?id=mdp.39015012345678",
                notes="Common HathiTrust page-turner URL; captures volume id.",
            ),
            IdentifierPattern(
                key="hathi_catalog_url",
                kind="url",
                regex=r"https?://(?:www\.)?hathitrust\.org/Record/(\d{6,})",
                example="https://hathitrust.org/Record/123456789",
            ),
        ),
    ),
    "internet_archive": Repository(
        key="internet_archive",
        label="Internet Archive",
        domains=("archive.org", "www.archive.org"),
        patterns=(
            IdentifierPattern(
                key="ia_details_url",
                kind="url",
                regex=r"https?://(?:www\.)?archive\.org/details/([A-Za-z0-9._-]+)",
                example="https://archive.org/details/psychologicalrev00wund",
                notes="Captures item identifier for edition/provenance checks.",
            ),
            IdentifierPattern(
                key="ia_stream_url",
                kind="url",
                regex=r"https?://(?:www\.)?archive\.org/stream/([A-Za-z0-9._-]+)",
                example="https://archive.org/stream/psychologicalrev00wund",
            ),
        ),
    ),
    "pubmed": Repository(
        key="pubmed",
        label="PubMed",
        domains=("pubmed.ncbi.nlm.nih.gov",),
        patterns=(
            IdentifierPattern(
                key="pubmed_url",
                kind="url",
                regex=r"https?://pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})/?",
                example="https://pubmed.ncbi.nlm.nih.gov/12345678/",
            ),
        ),
    ),
    "pmc": Repository(
        key="pmc",
        label="PubMed Central (PMC)",
        domains=("pmc.ncbi.nlm.nih.gov",),
        patterns=(
            IdentifierPattern(
                key="pmc_url",
                kind="url",
                regex=r"https?://pmc\.ncbi\.nlm\.nih\.gov/articles/(PMC\d+)/?",
                example="https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/",
            ),
        ),
    ),
    "psycnet": Repository(
        key="psycnet",
        label="APA PsycNet (PsycINFO/PsycARTICLES landing)",
        domains=("psycnet.apa.org",),
        patterns=(
            IdentifierPattern(
                key="psycnet_record_url",
                kind="url",
                regex=r"https?://psycnet\.apa\.org/record/(\d{4}-\d{5}-\d{3})",
                example="https://psycnet.apa.org/record/2004-12345-001",
                notes="APA record identifier; often corresponds to PsycINFO accession.",
            ),
            IdentifierPattern(
                key="psycinfo_accession",
                kind="id",
                regex=r"\b(\d{4}-\d{5}-\d{3})\b",
                example="2004-12345-001",
                notes="PsycINFO-style accession number; may appear without URL.",
            ),
        ),
    ),
}
def iter_all_patterns(include_common: bool = True) -> Iterable[Tuple[str, IdentifierPattern]]:
    if include_common:
        for p in COMMON_PATTERNS:
            yield ("common", p)
    for repo_key, repo in REPOSITORIES.items():
        for p in repo.patterns:
            yield (repo_key, p)


def compile_patterns(include_common: bool = True) -> List[Tuple[str, str, Pattern[str]]]:
    """Return list of (repo_key, pattern_key, compiled_regex)."""
    out: List[Tuple[str, str, Pattern[str]]] = []
    for repo_key, p in iter_all_patterns(include_common=include_common):
        out.append((repo_key, p.key, p.compile()))
    return out


def detect_identifiers(text: str, include_common: bool = True) -> List[Dict[str, str]]:
    """Lightweight detection of repository URLs/IDs in text (no I/O)."""
    hits: List[Dict[str, str]] = []
    for repo_key, patt in iter_all_patterns(include_common=include_common):
        rx = patt.compile()
        for m in rx.finditer(text or ""):
            val = next((g for g in m.groups() if g), m.group(0))
            hits.append({"repository": repo_key, "pattern": patt.key, "value": val})
    return hits


def repository_for_url(url: str) -> Optional[str]:
    u = (url or "").lower()
    for k, r in REPOSITORIES.items():
        if any(d in u for d in r.domains):
            return k
    return None
