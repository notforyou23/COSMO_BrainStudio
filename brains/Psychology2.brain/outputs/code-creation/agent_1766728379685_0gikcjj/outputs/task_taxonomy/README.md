# /outputs/task_taxonomy

This folder stores the project’s **task taxonomy artifacts**: the authoritative definitions of tasks, labels, dimensions, and mapping rules used to categorize work items, datasets, prompts, or evaluations.

Keep taxonomy artifacts **machine-readable** (preferred) and versioned so that downstream analyses can be reproduced exactly.

## What belongs here

- **Canonical taxonomy files** (preferred): `*.yaml`, `*.yml`, `*.json`
- **Human-facing docs** explaining the taxonomy and labeling rules: `README.md`, `guide.md`
- **Change logs** for taxonomy evolution (optional if managed elsewhere): `CHANGELOG.md`
- **Mappings/crosswalks** between taxonomies or between versions (e.g., `crosswalk_v1_to_v2.csv`)
- **Validation artifacts** (optional): schemas, test cases, or label examples used for QA

## Recommended file layout

A minimal, stable structure:

- `taxonomy.yaml` (or `taxonomy.json`) — current canonical taxonomy
- `taxonomy.schema.json` (optional) — JSON Schema for validation
- `examples/` (optional) — labeled examples demonstrating edge cases
- `history/` (optional) — archived prior versions and migration notes

Example tree:

outputs/task_taxonomy/
- README.md
- taxonomy_v1.0.0.yaml
- taxonomy_v1.1.0.yaml
- crosswalk_v1.0.0_to_v1.1.0.csv
- taxonomy.schema.json
- examples/
  - labeled_examples_v1.1.0.jsonl
- history/
  - notes_v1.0.0.md

## Canonical taxonomy file structure (suggested)

The taxonomy should be a single source of truth with explicit versioning and stable identifiers.

Suggested top-level keys:

- `name`: short taxonomy name
- `version`: semantic version string (see Versioning)
- `released`: ISO-8601 date (YYYY-MM-DD)
- `description`: brief purpose statement
- `dimensions`: list of classification dimensions (e.g., domain, task_type, modality)
- `labels`: label definitions, each with a stable ID and display name
- `rules` (optional): mapping rules, heuristics, or constraints
- `examples` (optional): small set of canonical examples (keep large example sets in `examples/`)

Suggested label shape:

- `id`: stable, never-reused identifier (e.g., `TASK.SUMMARIZATION.ABSTRACTIVE`)
- `name`: human-readable label
- `definition`: precise meaning
- `include`: positive criteria (bullet list)
- `exclude`: negative criteria / non-examples
- `parents` (optional): parent label IDs for hierarchy
- `aliases` (optional): alternative names used historically
- `notes` (optional): edge cases, clarifications

## Naming conventions

Use filenames that encode the taxonomy and version:

- `taxonomy_vMAJOR.MINOR.PATCH.yaml` (recommended)
- If multiple taxonomies exist, include the taxonomy name:
  - `taxonomy_<name>_vMAJOR.MINOR.PATCH.yaml`

Crosswalks/migrations:

- `crosswalk_vA_to_vB.csv` or `crosswalk_<name>_vA_to_vB.csv`

Examples:

- `labeled_examples_vMAJOR.MINOR.PATCH.jsonl`

## Versioning and update rules

Use **semantic versioning** for taxonomy artifacts:

- **MAJOR**: breaking changes (IDs removed/reused, dimension meaning changed, label semantics altered)
- **MINOR**: backward-compatible additions (new labels, new dimensions with defaults, added metadata)
- **PATCH**: clarifications and non-breaking edits (typos, wording improvements, added examples)

When updating:
1. Never reuse a retired `id`. If a label is replaced, deprecate the old ID and introduce a new one.
2. Record changes in `CHANGELOG.md` (or at minimum in commit messages) including:
   - added/removed/renamed labels
   - definition changes that affect labeling decisions
   - crosswalk guidance for migrations
3. Preserve old versions as immutable files (e.g., keep `taxonomy_v1.0.0.yaml`).
4. If changes affect downstream datasets, provide a crosswalk and/or migration notes.

## Reproducibility expectations

Any analysis or tool output referencing this taxonomy should record:
- taxonomy filename + version (e.g., `taxonomy_v1.1.0.yaml`)
- hash of the taxonomy file (optional but recommended)
- labeling policy details (manual vs automated, model/version, thresholds, annotator guidance)

## Common pitfalls to avoid

- Changing label meaning without a version bump
- Editing an existing versioned file in-place (breaks reproducibility)
- Using human-readable names as stable IDs (names change; IDs should not)
- Omitting include/exclude criteria (increases annotator/model disagreement)
