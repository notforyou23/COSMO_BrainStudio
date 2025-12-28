# PsyPrim Preregistration (One‑page) — Standardized Primary‑Source Workflow Evaluation

**Title:**  
**Authors/roles (incl. audit coders):**  
**Date / version:**  
**Repository (OSF/Git/Zenodo) + DOI (if available):**  
**Contact:**
## 1) Intervention & workflow being evaluated
**Intervention condition (PsyPrim workflow + lightweight tooling):**  
- Protocol checklists used: (Selection / Capture / Transcription / Citation / QC)  
- Metadata schema enforced: PsyPrim Primary‑Source Record (see §2)  
- Tool features enabled: provenance flags; variant numbering; repository citation linking

**Control condition (baseline practice):** describe typical sourcing/citation workflow and tools.

**Unit of work:** a “primary‑source item” (e.g., article, book chapter, archival document) producing (a) a citation and (b) a traceable research object (scan/text/notes/metadata).
## 2) Protocol elements to be implemented (what “compliance” means)

### 2.1 Checklist requirements (minimum passing criteria)
**A. Selection & acquisition**
- Identify source type (journal/book/archival/web) and access route (library/database/archive).
- Record retrieval date and access constraints (paywall, archive rules, digitization limits).

**B. Capture & preservation**
- Create stable local copy (PDF/images) when lawful; otherwise record access path and page/folio spans.
- Record file checksums (sha256) and file roles (scan/transcript/notes).
- Record page images coverage (all pages vs excerpt) and omissions rationale.

**C. Transcription / text extraction (if applicable)**
- Specify method (manual, OCR, hybrid) and error‑correction procedure.
- Mark uncertain readings and editorial interventions.

**D. Citation & locator fidelity**
- Ensure citation includes author, year, title, container, volume/issue, pages, publisher, and persistent IDs when available.
- Provide *repository citation link* that resolves to the exact research object used.

**E. Quality control**
- Independent check: another person verifies key fields and page/quote locators against the captured object.
- Record discrepancies and resolution.

### 2.2 Metadata schema (minimal fields required per item)
**Core identifiers**
- `item_id` (unique within project)  
- `source_type` (journal_article, book, chapter, archival_item, web, other)  
- `canonical_citation` (full formatted reference)  
- `persistent_ids` (DOI/ISBN/ISSN/Handle/ARK/etc., if any)  
- `repository_url` (canonical landing page) and `repository_release` (tag/commit/DOI)

**Provenance**
- `accessed_at` (ISO date)  
- `acquisition_method` (scan/download/photo/request)  
- `rights_status` (public_domain/licensed/fair_use/unknown)  
- `capture_files[]` with `path`, `sha256`, `role`, `page_span`

**Variant control**
- `variant_of` (item_id of parent, if derived)  
- `variant_no` (integer, starting at 1)  
- `variant_reason` (e.g., different edition, corrected OCR, re-scan, redaction)  
- `provenance_flags[]` (see below)

**Locator & excerpt integrity**
- `quoted_passages[]` with `page`/`folio`, `start_end`, and `verbatim` or `checksum` reference to excerpt file.

**Provenance flags (controlled vocabulary)**
- `UNVERIFIED_LOCATOR` (page/folio not independently confirmed)  
- `PARTIAL_CAPTURE` (not all pages captured)  
- `DERIVED_TEXT` (OCR/transcription used)  
- `EDITION_MISMATCH_RISK` (citation may not match consulted edition)  
- `ACCESS_RESTRICTED` (cannot redistribute capture)
## 3) Evaluation questions, outcomes, and hypotheses
**Primary outcomes**
1) **Citation accuracy** (field correctness + locator correctness): % correct vs gold standard.  
2) **Reproducibility of retrieval**: ability of an independent auditor to locate the same item/edition and verify quoted/used content.  
3) **Researcher effort**: time per item + perceived workload.

**Secondary outcomes**
- Completeness of metadata; frequency of provenance flags; rate of edition/variant ambiguity; number of QC discrepancies caught.

**Hypotheses (directional)**
- H1: Intervention improves citation accuracy vs control.  
- H2: Intervention improves reproducibility of retrieval/verification vs control.  
- H3: Intervention increases upfront time modestly but reduces rework time and lowers perceived ambiguity/uncertainty.
## 4) Study design (survey + audit study)
**Design type:** randomized assignment (preferred) or matched comparison across teams/items.  
**Participants:** historians of psychology (graduate students, postdocs, faculty) and/or trained RAs.  
**Materials/tasks:** each participant processes N primary‑source items (balanced by type/complexity).  
**Randomization unit:** participant or item; stratify by source type.  
**Blinding:** auditors blind to condition when scoring citations/locators.

### 4.1 Audit study (objective scoring)
**Gold standard creation:** an expert curator generates the correct citation + locators for each item.  
**Audit procedure:** independent auditors attempt to (a) retrieve the item using the provided citation/links and (b) verify specified locators/quotes.  
**Scoring rubric (predefined)**
- Citation field correctness: author/year/title/container/publisher/volume/issue/pages/ID.  
- Locator correctness: page/folio ranges and quote match.  
- Retrieval success: found exact item/edition within T minutes; repository link resolves; files/metadata present.

### 4.2 Surveys (subjective + process)
Administer after tasks (and optionally at baseline).
- Perceived effort/time pressure, clarity, confidence in citations, perceived reproducibility, satisfaction.
- Workload: short NASA‑TLX or 5–7 item Likert battery.
- Adoption intent and perceived barriers (rights, archives, tooling friction).
## 5) Sampling, exclusion, and data handling
**Planned sample size:** participants = ___ ; items per participant = ___ ; total items = ___.  
**Inclusion:** active researchers/students working with historical primary sources.  
**Exclusion (predefined):** incomplete task submissions; items with inaccessible sources due to unforeseen restrictions (record as `ACCESS_RESTRICTED`).  
**Missing data:** report extent; use transparent rules (e.g., treat missing fields as incorrect in accuracy metric).  
**Ethics:** consent; anonymize participant IDs; store raw logs in repository with access controls as needed.
## 6) Measures (operational definitions)
**Citation accuracy (item‑level):**
- Binary accuracy per field; compute composite score (mean of fields) and overall pass/fail threshold.
- Locator accuracy: exact match or acceptable tolerance rules (e.g., ±1 page only if justified by edition differences).

**Reproducibility (item‑level):**
- Retrieval success (0/1) within T minutes.
- Verification success (0/1) for each quoted/used passage.
- Repository link integrity (0/1) and presence of required metadata fields (0/1).

**Effort:**
- Objective time per item (tool logs or self‑timed with start/stop rules).
- Self‑report workload and perceived ambiguity.

**Process indicators:**
- Count/type of provenance flags; number of variants; QC discrepancy rate and resolution time.
## 7) Analysis plan (primary)
**Estimation approach:** compare conditions using mixed‑effects models (items nested in participants; random intercepts for participant and item).  
- Accuracy outcomes: logistic (binary) or beta/linear (scaled score).  
- Effort/time: log‑normal/linear mixed model; also compare medians.  
- Reproducibility outcomes: logistic mixed models.

**Covariates (if used):** source type, item length/complexity, participant experience.  
**Multiple comparisons:** control false discovery (Benjamini–Hochberg) across primary outcomes or pre‑specify one primary endpoint.

**Robustness checks:** analyze by source type; exclude `ACCESS_RESTRICTED`; sensitivity for edition ambiguity (items with `EDITION_MISMATCH_RISK`).  
**Decision criteria:** report effect sizes with CIs; do not dichotomize solely by p-values.
## 8) Implementation fidelity & reporting
**Fidelity checks:** proportion of items meeting checklist pass criteria; metadata completeness; presence of repository citation linking; QC performed.  
**Deviations:** record any departures from this prereg with timestamped rationale in the repository.  
**Deliverables:** anonymized dataset, code to compute metrics, scoring rubric, and a short report summarizing impacts on accuracy, reproducibility, and effort.

**Sign‑off:**  
PI: ____________________   Date: __________   Version tag/commit: __________
