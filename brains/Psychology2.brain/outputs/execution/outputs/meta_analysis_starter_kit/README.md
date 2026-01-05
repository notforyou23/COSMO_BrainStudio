# Meta-analysis starter kit (artifacts)

This folder stores a minimal, reusable set of artifacts that make a meta-analysis reproducible, auditable, and easy to rerun on new data. Keep contents *generic* (templates + examples), not tied to a single study unless clearly labeled as an example.

## What belongs here
- Protocol-level templates: eligibility criteria, screening rules, extraction schema, analysis plan.
- Data structure templates: CSV/TSV headers, codebook, variable definitions.
- Analysis templates: model specification notes, sensitivity/subgroup plan, reporting checklist.
- Reproducibility assets: environment capture template, run manifest format, provenance notes.
- Example artifacts (optional): small, clearly marked example datasets or filled-in templates.

## What does NOT belong here
- Large raw PDFs, full-text libraries, or copyrighted full texts.
- Study-specific private data or PII.
- One-off outputs from a single run that are not intended as a template (put those under outputs/tools or a project run directory).

## Recommended structure (lightweight)
- templates/            Canonical templates to copy into a new project
- examples/             Tiny illustrative examples (clearly labeled)
- schemas/              Data dictionaries / codebooks / JSON schemas
- checklists/           PRISMA-style or internal QA checklists
- methods/              Statistical approach notes and model conventions

You may add subfolders as needed, but keep names stable and descriptive.

## Naming & versioning
- Prefer kebab-case: `data-extraction-template_v1.0.md`
- Include a semantic version for templates: vMAJOR.MINOR (MAJOR = breaking change).
- Date-stamped iterations are acceptable for examples: `example-screening_2025-12-26.csv`
- Keep file extensions explicit: .md, .csv, .tsv, .json, .yaml, .txt, .R, .py

## Minimal starter-kit artifact checklist
Each new starter-kit artifact should include, either in the file header (for .md/.txt) or as a paired `*.meta.json` file:

1) Purpose: one sentence describing what the artifact is for.
2) Scope: what it covers and what it explicitly does not cover.
3) Inputs/Outputs (if applicable): expected columns/fields or file interfaces.
4) Version + date: semantic version and last-updated date.
5) Provenance: author/owner or source, and any upstream references.
6) Reproducibility notes: assumptions, required software, and deterministic settings.

## Minimal templates (copy/paste)

### A) Template header for Markdown artifacts
Paste at the top of any .md template:

Title:
Version:
Last updated (YYYY-MM-DD):
Owner:
Purpose:
Scope (includes / excludes):
Expected inputs:
Expected outputs:
Dependencies (software / packages):
Change notes:

### B) Paired metadata file format (JSON)
For a non-Markdown artifact (e.g., .csv), create a sidecar file:
`<artifact-name>.meta.json`

Suggested fields:
{
  "title": "",
  "version": "v1.0",
  "last_updated": "YYYY-MM-DD",
  "owner": "",
  "purpose": "",
  "scope": { "includes": [], "excludes": [] },
  "inputs": [],
  "outputs": [],
  "dependencies": [],
  "provenance": { "source": "", "notes": "" },
  "checks": { "schema_validated": false, "deterministic": true }
}

### C) Data extraction schema (minimum columns)
If you store a CSV/TSV extraction template, include at least:
- study_id (stable key)
- citation (short)
- design
- population
- intervention/exposure
- comparator
- outcome
- effect_measure (e.g., OR, RR, SMD)
- effect_estimate
- standard_error or ci_lower/ci_upper
- timepoint
- risk_of_bias (tool + judgment)
- notes
- extracted_by
- extracted_date (YYYY-MM-DD)

## Quality gates (recommended)
Before considering the starter kit “ready”:
- Templates are internally consistent (same field names across docs).
- Every example is clearly labeled and small enough to inspect manually.
- Any schema changes bump MAJOR if they break existing filled-in templates.
- No sensitive content is present.

## Relationship to other /outputs folders
- outputs/prereg: finalized preregistration documents (study-specific).
- outputs/task_taxonomy: classification/taxonomy definitions for tasks.
- outputs/tools: run logs, parameters, and tool-produced artifacts for traceability.
