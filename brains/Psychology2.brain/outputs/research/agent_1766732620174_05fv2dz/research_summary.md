# Research Summary

**Agent:** agent_1766732620174_05fv2dz
**Mission:** Survey the scholarly landscape to identify existing metadata standards, citation best practices, edition/translation provenance conventions, and relevant digital tools and plugins used in historical and primary-source scholarship in psychology. Compile a prioritized list of candidate metadata fields, checklist items, public-domain repositories (e.g., PsychClassics, Project Gutenberg, Internet Archive), and exemplar papers or audits that document citation errors or reproducibility issues.
**Completed:** 2025-12-26T07:05:33.968Z

## Summary

Across psychology primary-source scholarship (empirical articles, datasets, instruments, interviews, lab notes), the core metadata challenge is practical interoperability: making materials findable, citable, and reusable across library catalogs, repositories, and lab workflows. The research indicates a complementary “stack” of standards: Dublin Core for cross-domain discovery metadata, TEI for richly structured document-level encoding and provenance (especially for textual/historical sources), and CRediT for transparent attribution of contributor roles across articles and associated outputs (data/code/materials).

For public-domain historical psychology texts, the most actionable infrastructure insight is that page-level, stable citation anchors depend heavily on the hosting platform. HathiTrust and the Internet Archive provide workable page-addressing patterns (e.g., HathiTrust page sequence parameters; Internet Archive page viewer URLs and IIIF endpoints). However, licensing and reuse constraints can differ from underlying public-domain status—especially for Google-digitized scans in HathiTrust—so citation and reuse tooling needs to capture not just “PD” but scan provenance and terms.

Finally, the landscape of verification research is converging on measurable audits and scalable, machine-assisted checking. Citation/quotation error rates in historical scholarship are empirically nontrivial, and reproducibility audits in psychology show that open data alone often fails to guarantee analytic reproducibility. Emerging datasets and systems for citation verification and citation-context labeling suggest a path to linking claim–citation checking with reproducibility signals.

## Key Findings

1. Dublin Core (15-element Simple DC; expanded Qualified DC with terms like Provenance/RightsHolder/Audience) is a common cross-domain discovery metadata layer suitable for indexing psychology primary sources in repositories.

2. TEI’s required <teiHeader> (with mandatory <fileDesc>) provides structured document metadata plus encoding/provenance and revision history, making it particularly well-suited to encoded primary documents (e.g., transcripts, diaries, case notes) rather than only catalog records.

3. CRediT is an ANSI/NISO-standardized (2022) 14-role contributor taxonomy that supports transparent attribution for psychology outputs beyond the article (datasets, code, stimuli), aiding reuse and accountability.

4. For page-level stable citations in public-domain scanned books, HathiTrust supports page addressing via reader sequence parameters and applies rights codes (e.g., PD vs PDUS), while the Internet Archive supports stable page-specific viewer URLs and an official IIIF service enabling stable canvases/endpoints for annotation and linking.

5. Empirical audits show verification problems are measurable: a history-journal citation audit reported a 24.27% quotation-error rate, and psychology reproducibility checks of open-data-badged papers found frequent numerical discrepancies and that full reproduction often required author involvement—indicating that availability ≠ reproducibility.

## Research Queries

1. metadata standards TEI Dublin Core CRediT primary sources psychology
2. public domain repositories psychology texts page-level stable identifiers licensing
3. citation errors reproducibility audits historical scholarship psychology studies datasets

## Sources

Total sources consulted: 90

See `bibliography.bib` for citation-ready BibTeX entries.
