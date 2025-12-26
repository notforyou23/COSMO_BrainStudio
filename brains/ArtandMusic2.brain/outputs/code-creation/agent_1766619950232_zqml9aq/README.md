# Deterministic Plan/Outline/Draft Generator

This project generates three Markdown artifacts that are guaranteed to stay in lock-step (1:1 mapping) across re-runs:

- `runtime/outputs/plan_project_scope_and_outline.md`
- `runtime/outputs/REPORT_OUTLINE.md`
- `runtime/outputs/DRAFT_REPORT_v0.md`

The generator is deterministic: for the same source code and the same outline model, the outputs are byte-for-byte stable (normalized newlines), and the mapping between outline sections and draft skeleton sections is invariant.

## What “deterministic mapping” means

A single canonical outline data model is the source of truth (defined in `src/outline_schema.py`). All three Markdown files are rendered from that same model, using shared stable rendering helpers (`src/md_render.py`).

Mapping guarantees:

1. **Canonical section identity**: every section has a stable `section_id` derived deterministically from its canonical path within the outline (not from runtime order or timestamps).
2. **Single-source rendering**: `REPORT_OUTLINE.md` and the section skeleton inside `DRAFT_REPORT_v0.md` are rendered from the same section list in the same order.
3. **Anchored skeleton**: every section heading in `DRAFT_REPORT_v0.md` includes the corresponding `section_id` anchor so it can be matched back to the outline unambiguously.
4. **Deterministic I/O**: writes are atomic and newlines are normalized; optional content hashes can be computed to confirm identical outputs across runs.

If any internal consistency check fails (e.g., mismatched IDs, missing sections, or ordering drift), the generator should fail fast rather than produce partially-mapped artifacts.

## Generated files (roles)

- `plan_project_scope_and_outline.md`
  - Human-readable project scope and planning notes that explain *what* the report covers and *how* it will be produced.
- `REPORT_OUTLINE.md`
  - The canonical report outline (headings/sections) derived directly from the outline model.
- `DRAFT_REPORT_v0.md`
  - A “fill-in-the-blanks” report draft containing the same section structure as `REPORT_OUTLINE.md`, with stable anchors for every section.

## How to run

From the repository root, run one of the following:

- Module execution (preferred):
  - `python -m src.plan_project_scope_and_outline`
- Direct script execution:
  - `python src/plan_project_scope_and_outline.py`

The script writes the generated Markdown files into `runtime/outputs/` (creating directories as needed).

## Determinism checklist (how to verify)

Re-run the generator twice without changing any source files and confirm:

1. The three output files are identical between runs (no timestamp churn; normalized `\n` newlines).
2. Every section present in `REPORT_OUTLINE.md` appears exactly once in `DRAFT_REPORT_v0.md` in the same order.
3. Every section in the draft skeleton contains a stable anchor derived from the same `section_id` used by the outline model.

If your implementation includes content hashing (recommended), you can also verify by comparing the computed hashes before/after a re-run.

## Design notes (where the guarantees come from)

- `src/outline_schema.py`
  - Defines the canonical outline structure and section objects.
  - Implements deterministic section ID generation from canonical section paths.
  - Provides rendering entry points used by the main generator.
- `src/md_render.py`
  - Centralized Markdown formatting helpers to avoid accidental formatting drift.
  - Ensures stable heading formatting and anchor rendering.
- `src/io_utils.py`
  - Ensures directories exist, writes are atomic, and newlines are normalized.
  - Optional deterministic hashing utilities for integrity checks.
- `src/plan_project_scope_and_outline.py`
  - Orchestrates model creation, rendering, validation, and writes all three outputs.

## Expected developer workflow

1. Modify the canonical outline model (in `src/outline_schema.py`) when you need to change section structure.
2. Run the generator to update all three Markdown outputs together.
3. Treat the outputs as derived artifacts: if you need to change structure, change the model; if you need to change wording within the prefilled planning content, do so in the generator/model so it remains deterministic.

## Troubleshooting

- Output files change unexpectedly between runs:
  - Ensure no timestamps, random seeds, or unordered dict/set iteration is used in rendering.
  - Ensure IDs are derived from canonical paths, not display text that may be edited.
  - Ensure newline normalization is applied on write.
- Outline and draft sections don’t match:
  - Confirm both are rendered from the same section list and that IDs are computed once and reused, not recomputed with different inputs.
