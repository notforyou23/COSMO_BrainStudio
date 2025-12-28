# psyprov — Provenance-aware primary-source workflows for psychology

**Mission:** develop and validate community-endorsed workflows and lightweight software/plugins that (1) detect edition/translation provenance, (2) flag variant page/paragraph numbering, and (3) produce durable public-domain repository citations for primary-source scholarship in psychology.

This repo is a planning + validation toolkit: it generates a concrete task plan (developer/archivist/journal-ready) and defines schemas + heuristics used to audit provenance signals in citations, filenames, OCR text, and repository metadata.

## What this project supports

### Supported workflows (end-to-end)
1. **Ingest**: a PDF/EPUB scan and/or OCR text, plus repository metadata (e.g., IA, HathiTrust, Gallica, Gutenberg, Wikisource).
2. **Detect provenance**: infer edition/translation candidates and extraction of salient signals (translator, publisher, year, series, imprint, edition statement).
3. **Normalize references**: map page/paragraph references across variants; record evidence when the mapping is uncertain.
4. **Cite repositories**: produce a public-domain repository citation with durable identifiers and access date, and retain the exact item/version used.
5. **Report & export**: emit machine-readable metadata (JSON/JSON Schema) and human-facing checklists suitable for authors, editors, and archivists.
6. **Validate**: run empirical protocols (survey + audit study) to measure usability, accuracy, and reproducibility across communities.

### Outputs you should expect
- **Checklists/specs** for authors, copyeditors, and archivists (what to record; what to verify).
- **Metadata schema** for provenance, variant locators (page/para), and repository citations.
- **UI/UX requirements** for lightweight plugins (reference managers, journal submission systems, PDF/OCR viewers).
- **Automated heuristics** (deterministic, explainable) with confidence scores and evidence traces.
- **Evaluation protocol** with measurable success criteria, survey instruments, and audit-study sampling.

## Prioritized task breakdown (hand-off ready)

### P0 — Minimum viable standards (to agree on)
1. **Community “minimum fields” checklist** (author/journal-facing)
   - Required: work title, creator, edition/translation statement, translator/editor (if any), publication year, publisher/place, source repository, stable identifier (URL + item ID), access date, and locator method (page/para scheme).
   - Required evidence: where each field was found (citation string, title page OCR span, repository JSON field, filename token).
   - Decision rules: when multiple candidates exist, record chosen candidate + why; always retain alternatives in metadata.

2. **Provenance metadata schema (v1)**
   - Entities: Work, Manifestation (edition/translation), DigitalItem (repository copy), Evidence (snippets/fields), LocatorScheme (page/para mapping).
   - Required properties: `provenance.edition`, `provenance.translation`, `repository.source`, `repository.identifier`, `locators.scheme`, `evidence[]`.
   - Exports: JSON Schema for validation; compact JSON for embedding in submissions/supplements.

3. **Citation output format**
   - One-line citation for manuscripts + machine payload (JSON block) for supplements.
   - Must preserve: exact repository item used, stable link/ID, and versioning info if available.

### P1 — Lightweight detection heuristics (deterministic + auditable)
Heuristics should return: (a) extracted fields, (b) confidence, (c) evidence trace.
- **Citation-string parsing**: detect translator/editor phrases, edition markers (“2nd ed.”, “rev.”), date ranges, series/imprint.
- **Filename/token heuristics**: year, translator initials, publisher tokens, edition markers.
- **OCR/title-page cues**: “translated by”, “edited by”, “second edition”, imprint lines; robust to OCR noise.
- **Repository metadata cross-check**: compare extracted year/publisher/translator against repository fields; flag conflicts.
- **Variant locator detection**:
  - Identify if citations use page, paragraph, section, or mixed locators.
  - Detect reprints that reset pagination; flag likely mismatches.
  - Provide mapping hints (e.g., chapter+section anchors; paragraph numbering based on normalized text blocks).

### P2 — UI/UX requirements for plugins (reference managers + journals)
- **Evidence-first UI**: every inferred field shows the supporting snippet/field and source (OCR span, metadata key, citation substring).
- **Conflict handling**: side-by-side candidates with a “select & justify” step; never silently overwrite.
- **Locator helper**: choose locator scheme (page/para/section), show warnings if incompatible across editions.
- **Export modes**: (1) human citation, (2) JSON metadata attachment, (3) copy/paste checklist summary.
- **Journal integration**: submission-time validator that checks required fields and prompts for missing evidence.

### P3 — Empirical evaluation protocol (survey + audit study)

**Goals:** accuracy of provenance detection, usability of workflows, and reproducibility of primary-source citation.
- **Primary metrics**
  - Field-level accuracy (translator, year, publisher, edition statement, repository ID).
  - Conflict detection rate (did the tool flag discrepancies?).
  - Locator robustness (can a second researcher reach the same passage?).
  - Time-to-complete and perceived workload (e.g., NASA-TLX short form).
  - Inter-rater agreement on chosen manifestation (Cohen’s κ / Krippendorff’s α).

**Study A: Survey (community endorsement + usability)**
- Participants: authors, editors, archivists, librarians (target N≈40–120; stratify by role).
- Materials: 3–6 representative primary sources (translations, reprints, multi-edition classics).
- Procedure: participants perform provenance capture with/without tool support; then answer Likert + free-response.
- Outcomes: acceptability of minimum fields; clarity of evidence; perceived friction; policy recommendations for journals.

**Study B: Audit study (reproducibility + detection performance)**
- Sampling frame: published psychology articles citing public-domain primary sources (e.g., 50–200 citations).
- Audit steps:
  1) Extract original citation + claimed locator.
  2) Independently identify the likely repository item + manifestation.
  3) Attempt passage retrieval; record success/failure and ambiguity causes.
  4) Run heuristics on citation/metadata/OCR; compare against auditor ground truth.
- Analysis: error taxonomy (missing translator, wrong year, unstable URL, locator mismatch), effect sizes, and recommended policy thresholds.

## Quickstart

### Install (developer mode)
From the repo root:
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -e .`

### Run the planner (generate the hand-off plan)
- `python -m psyprov.plan --out plan.json`
- `python -m psyprov.plan --out plan.md --format markdown`

### Run schema export (for journal/archivist validation)
- `python -m psyprov.schemas --export-json-schema --out schemas/`

### Run heuristics on a citation set (local evaluation)
- `python -m psyprov.heuristics --citations citations.jsonl --out heuristic_results.jsonl`

### Run the validation protocol scaffolding
- `python -m psyprov.validate survey --out survey_packet/`
- `python -m psyprov.validate audit --citations citations.jsonl --out audit_results/`

## Data contracts (what developers/journals can rely on)
- All automated outputs include: extracted fields, confidence, and evidence pointers.
- No black-box ML requirement: heuristics are deterministic and explainable.
- Schema-first design: every record validates against exported JSON Schema.

## Governance and partner touchpoints
- **Archivists/librarians:** confirm repository identifier conventions, versioning, and preferred citation forms.
- **Journals:** adopt minimum fields; integrate submission-time checks; publish guidance for primary-source citations.
- **Researchers:** use checklists and attach JSON metadata alongside manuscripts to enable reproducible quotation/analysis.
