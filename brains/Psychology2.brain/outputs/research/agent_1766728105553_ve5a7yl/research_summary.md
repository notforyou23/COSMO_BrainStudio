# Research Summary

**Agent:** agent_1766728105553_ve5a7yl
**Mission:** Survey existing standards, practices, and tools relevant to primary-source scholarship in psychology (bibliographic/metadata standards, digital editions conventions, repository citation practices, and existing plugins/tools). Produce a concise evidence map listing candidate metadata schemas, edition/translation provenance vocabularies, citation heuristics, and public-domain repositories (PsychClassics, Project Gutenberg, HathiTrust, Internet Archive, Gallica, etc.) to inform protocol and lightweight-tool design. Highlight gaps and community stakeholders to engage for endorsement.
**Completed:** 2025-12-26T05:50:23.036Z

## Summary

The research indicates that “primary-source scholarship in psychology” is best supported not by a psychology-specific metadata standard, but by a layered, interoperable stack. In practice, discovery metadata (Dublin Core or MODS) is complemented by archival hierarchy (EAD3), object packaging/structure for multi-file digitized items (METS, including the newly released METS 2 in 2025), and preservation/technical metadata (PREMIS plus NISO MIX for images). For text-centric sources (letters, notebooks, transcripts), TEI P5 remains a robust edition/encoding ecosystem, with TEI CMIF as a pragmatic profile for correspondence. For psychology primary sources that are actually research outputs (datasets, instruments, questionnaires), DDI Lifecycle (3.3) and the newer DDI-CDI (2025) address richer cross-domain interoperability needs.

Repository practices most relevant to reproducibility and citation center on stable identifiers and explicit rights signals. HathiTrust emphasizes a volume identifier (htid) plus persistent Handle URLs and conservative rights codes; Internet Archive uses a per-item identifier but often relies on uploader-declared rights, implying higher verification burden; Gallica consistently exposes ARK identifiers and has clear reuse framing (attribution required, commercial reuse often licensed), with metadata under France’s Open Licence (Etalab) and source/retrieval-date expectations. Tooling trends suggest that lightweight protocol/tool design should lean on established citation/rendering infrastructures (CSL + citeproc) and proven “plugin surfaces” (COinS/OpenURL, Zotero integrations), while monitoring emerging provenance standards like C2PA for cryptographically verifiable media provenance rather than reinventing provenance from scratch.

## Key Findings

1. Layered metadata stacks dominate digitized primary-source workflows: Dublin Core/MODS for description, EAD3 for archival hierarchy, and METS (including METS 2 released March 2025) to package complex digital objects (scans + OCR + transcripts + derivatives).

2. Preservation-grade evidentiary support commonly adds PREMIS (events/agents/rights) and NISO MIX for still-image technical metadata, improving reproducibility and long-term interpretability of digitized psychology sources.

3. TEI P5 remains the primary ecosystem for encoding scholarly editions of text-heavy sources, and TEI CMIF offers a practical interchange profile specifically for correspondence metadata (via TEI correspDesc).

4. For psychology materials that function as structured research data (datasets, instruments, codebooks), DDI Lifecycle 3.3 and the newer DDI-CDI v1.0 (Feb 2025) are relevant for lifecycle documentation and cross-domain interoperability.

5. Repository identifier/licensing regimes vary sharply: HathiTrust provides htid + Handle and conservative rights codes; Internet Archive provides stable item identifiers but often weaker rights assurance; Gallica provides ARK identifiers plus explicit attribution and reuse terms (non-commercial generally permitted for PD reproductions, commercial often licensed).

## Research Queries

1. metadata schemas for digitized primary sources psychology
2. repositories psychology primary sources identifiers licenses HathiTrust Internet Archive Gallica
3. tools provenance detection citation normalization digital editions plugins

## Sources

Total sources consulted: 125

See `bibliography.bib` for citation-ready BibTeX entries.
