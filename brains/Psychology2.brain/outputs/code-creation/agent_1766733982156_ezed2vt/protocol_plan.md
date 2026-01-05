# Provenance-Aware Primary-Source Psychology Protocols

_Generated: 2025-12-26_

## Mission summary

Community-endorsed protocols (checklists, metadata schemas) and lightweight software/plugins to detect and annotate edition/translation provenance, variant pagination/paragraph markers, and public-domain repository citations for primary-source psychology scholarship.

## 1) Stakeholder engagement plan

### 1.1 Stakeholders in scope

- Primary-source psychology scholars (historians, methodologists, translators)
- Librarians/archivists and special collections
- Repository operators / digital scholarship staff
- Publishers/editors for critical editions
- Tooling maintainers (Zotero, Pandoc/Quarto, JATS/TEI communities)
- Research integrity and reproducibility advocates

### 1.2 Governance and decision-making

- Create a Steering Group (6–10 people) with balanced representation across stakeholder groups.
- Create two Working Groups: (A) Protocols & Schemas, (B) Tools & Integrations.
- Define a lightweight RFC process: proposal → review → pilot → endorsement → versioned release.
- Adopt a code of conduct and conflict-of-interest disclosure for endorsers.

- [AC-001] Steering Group roster published with roles, terms, and COI statements.
- [AC-002] RFC process documented with timelines and voting/consensus rules.
- [AC-003] Endorsement criteria explicitly require pilot evidence and audit results.

### 1.3 Engagement activities (deliverables-driven)

1. Discovery interviews (n=20–30) to map current citation/provenance practices and pain points.
2. Protocol design workshops (3 sessions) to co-author checklists and schema fields.
3. Tooling design sprints (2 sprints) to align detection/annotation outputs with workflows.
4. Public comment period (30–45 days) on draft protocol package (v0.9).
5. Endorsement roundtable to finalize v1.0 with sign-on statements.

- [AC-004] Interview guide + anonymized thematic summary published; requirements trace to themes.
- [AC-005] Workshop outputs include edited checklist and schema diffs with rationale.
- [AC-006] Public comment log with dispositions (accept/reject/defer) is published.

## 2) Protocol package (checklists + metadata schemas)

### 2.1 Protocols to produce (community-endorsed)

- **Edition/Translation Provenance Checklist**: minimum fields and verification steps.
- **Variant Marker Checklist**: pagination, paragraph/section markers, and alignment rules.
- **Repository Citation Checklist**: durable identifiers, access dates, and rights/public-domain signals.

- [AC-007] Each checklist has: purpose, applicability, required/optional items, examples, and failure modes.
- [AC-008] Each checklist includes a ‘minimum-compliance’ profile for low-burden adoption.

### 2.2 Metadata schema requirements

Target outputs:
- JSON Schema (machine validation)
- YAML profile (human-authored frontmatter)
- Crosswalks: CSL, BibTeX, TEI, JATS, and Zotero Extra fields mapping

| Field/Concept | Normative requirement |
| --- | --- |
| edition.provenance | Publisher, year, edition statement, printings; verify from title page/colophon |
| translation.provenance | Translator(s), source language, basis edition, notes on modernization |
| source.identifiers | DOI/Handle/ARK/IA ID/Hathi ID; OCLC/ISBN when available |
| repository.citation | Repository name, stable URL, access date, file checksum if captured |
| variant.markers | Page mapping strategy; paragraph/section anchor scheme; alignment confidence |
| rights.pd_signal | Public-domain basis (jurisdiction/date/notice) and repository rights statement |
| extraction.pipeline | OCR source, version, post-correction steps; segmentation method |

- [AC-009] Provide JSON Schema with examples that validate under CI.
- [AC-010] Publish crosswalk tables with at least CSL + TEI + JATS coverage for core fields.
- [AC-011] Define required vs optional fields and acceptable value formats (IDs, dates, languages).

## 3) Lightweight software/plugins (detect + annotate)

### 3.1 Functional requirements

- Detect edition/translation signals from PDFs/EPUBs: title page patterns, imprint lines, translator credits.
- Extract and normalize stable repository identifiers and URLs; recommend canonical citation strings.
- Generate variant anchors: page-image → logical page mapping; paragraph/section IDs; alignment hints.
- Emit provenance annotations as: (a) YAML/JSON sidecar, (b) embedded TEI/JATS fragments, (c) CSL JSON notes.
- Support round-trip editing (human corrections) with deterministic merges.

- [AC-012] Tooling outputs are schema-valid and include provenance confidence scores + evidence snippets.
- [AC-013] At least one plugin path: Zotero translator/connector enhancement OR Pandoc/Quarto filter.
- [AC-014] Provide ‘dry-run’ mode that reports what would be annotated without modifying sources.

### 3.2 Non-functional requirements

- Privacy: no upload required by default; local-first processing with optional opt-in telemetry.
- Reproducibility: deterministic outputs given same inputs; record tool versions and hashes.
- Interoperability: stable IDs, UTF-8, language tags (BCP 47), and open licenses for protocols.
- Usability: defaults + progressive disclosure; explainable warnings and evidence display.
- Maintainability: modular parsers; test fixtures from multiple repositories and edition types.

- [AC-015] All outputs include tool/version metadata and input file hash in a standard block.
- [AC-016] A conformance test suite (fixtures + expected JSON) is published and runnable in CI.

## 4) Validation and evaluation studies

### 4.1 Survey study (perceived burden, clarity, and trust)

- Population: scholars, librarians, and digital scholarship practitioners (target n=150–250).
- Design: mixed Likert + scenario tasks comparing current practice vs protocol-driven practice.
- Outcomes: perceived clarity, time cost, willingness to adopt, trust in provenance claims, and tooling usability.
- Analysis: pre-registered hypotheses; subgroup comparisons by role and experience; open instrument release.

- [AC-017] Survey instrument and codebook are published; includes at least 3 realistic citation/provenance scenarios.
- [AC-018] Define adoption intent KPI (e.g., ≥60% ‘likely/very likely’ to use minimum profile within 6 months).

### 4.2 Audit study (accuracy and completeness of annotations)

- Sample: stratified corpus of 200 items across repositories, decades, and known multi-edition/translation cases.
- Gold standard: expert adjudication of edition/translation and marker correctness (double-coded, resolve disputes).
- Compare: baseline (manual typical practice) vs protocol + tooling assisted workflow.
- Metrics: precision/recall for detected provenance fields; marker alignment accuracy; citation completeness; time-on-task.
- Report: error taxonomy (OCR artifacts, ambiguous imprint, repository metadata conflicts) with mitigations.

- [AC-019] Audit achieves inter-rater reliability target (e.g., Cohen’s κ ≥ 0.75 on key fields).
- [AC-020] Tool-assisted workflow improves citation completeness and reduces critical provenance errors vs baseline.
- [AC-021] Publish anonymized audit dataset (where permissible) + full methods and analysis scripts.

## 5) Phased rollout plan with measurable milestones

| Phase | Goal | Exit artifacts |
| --- | --- | --- |
| Phase 0 (0–2 mo) | Set up governance, interview study, initial requirements | Roster, RFC process, interview synthesis |
| Phase 1 (2–5 mo) | Draft protocols + schema v0.9; prototype plugins/filters | Draft package, schema + examples, prototype |
| Phase 2 (5–8 mo) | Pilots with 3–5 labs/libraries; run survey | Pilot reports, revised v1.0 candidates |
| Phase 3 (8–12 mo) | Audit study + endorsement roundtable; release v1.0 | Validated v1.0, conformance suite, endorsements |
| Phase 4 (12–18 mo) | Scale adoption + integrations + maintenance | More connectors, training materials, v1.1 based on issues |

- [AC-022] At least 5 independent organizations sign the v1.0 endorsement statement.
- [AC-023] Adoption KPI: ≥500 protocol downloads OR ≥200 active plugin installs within 6 months of v1.0.
- [AC-024] Impact KPI: ≥30 published works cite the protocol package within 12 months.
- [AC-025] Maintenance KPI: <30 days median time-to-triage for reported issues; quarterly minor releases.

## 6) Traceability matrix (requirements → evidence)

| Category | Evidence artifact | Acceptance criteria coverage |
| --- | --- | --- |
| Engagement | Interview synthesis + comment log | AC-001..AC-006 |
| Protocols/Schemas | Checklists + JSON Schema + crosswalks | AC-007..AC-011 |
| Tooling | Plugin/filter + conformance tests + fixtures | AC-012..AC-016 |
| Validation | Survey prereg + audit dataset + analysis | AC-017..AC-021 |
| Rollout | Endorsements + adoption dashboard | AC-022..AC-025 |
