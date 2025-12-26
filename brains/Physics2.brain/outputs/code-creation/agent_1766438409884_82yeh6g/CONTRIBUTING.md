# Contributing

Thanks for contributing! This repository is a **versioned skeleton** intended to make audit deliverables reproducible and easy to review.

## Quick start
1. Create a branch from `main`.
2. Make focused commits.
3. Open a Pull Request (PR) with a clear description and links to evidence.
4. Ensure outputs and docs follow the structure below.

## Workflow
- Use GitHub PRs for all changes (no direct pushes to `main`).
- Keep PRs small and scoped to one objective (e.g., “add Stage 1 outputs skeleton”).
- Prefer deterministic generation: if a script produces files, commit the script and the generated artifacts that are required for audit.

## Branching
- Base branch: `main`
- Branch naming:
  - `feat/<short-topic>` (new capability/content)
  - `fix/<short-topic>` (bugfix)
  - `docs/<short-topic>` (documentation-only)
  - `chore/<short-topic>` (maintenance)
- Rebase/merge policy: keep a clean history; squash merge is acceptable if it preserves an informative PR description.

## Commit messages
Use imperative, descriptive messages:
- Good: `Add repository skeleton to outputs/`
- Good: `Document deliverables layout and naming rules`
- Avoid: `update`, `changes`, `misc`

## Repository structure (expected)
- `README.md` — project overview and how to (re)generate the skeleton
- `LICENSE` — open-source license text
- `CONTRIBUTING.md` — this file
- `docs/` — documentation hub and pages
- `outputs/` — audit deliverables and generated artifacts
  - `.gitkeep` (or similar) may be used to ensure the directory is tracked

Keep additions consistent with this layout; if you introduce a new top-level directory, justify it in the PR.

## Adding deliverables to `outputs/`
Deliverables should be easy to locate, diff, and review.

### Naming and organization
- Use stable, human-readable names (no timestamps in filenames unless required by the artifact).
- Group by stage and artifact type when applicable, for example:
  - `outputs/stage-1/`
  - `outputs/stage-1/reports/`
  - `outputs/stage-1/data/`
- Prefer lowercase with hyphens for folders and files: `stage-1`, `audit-summary.md`.

### What to commit
- Commit final deliverables (the files an auditor/reviewer must see).
- If deliverables are generated, also commit the generator script and document how to run it.
- Do not commit secrets, credentials, API keys, or private data.

### Formatting and quality
- Text artifacts: UTF-8, LF line endings.
- Markdown: wrap lines sensibly (~80–120 chars where practical), use headings in logical order.
- Data artifacts: include a short `README.md` in the containing folder explaining provenance and schema when non-obvious.
- Binary files: only include when necessary; prefer PDF/PNG over proprietary formats when possible, and document how they were produced.

## Documentation conventions
- Put long-form documentation in `docs/`.
- Cross-link from `README.md` to the relevant `docs/` entry points.
- When adding a doc page, include:
  - Purpose/summary
  - Inputs/assumptions
  - Outputs (with paths under `outputs/` when relevant)
  - Reproduction steps (commands and expected results)

## Reviews and acceptance criteria
A change is ready to merge when:
- The diff is complete and understandable without external context.
- Paths and filenames match the repository structure rules above.
- New/changed outputs are documented (what they are and how to reproduce them).
- No sensitive information is introduced.
- CI/checks (if present) pass.

## Reporting issues
Use Issues for:
- Missing deliverables or unclear locations
- Broken generation steps
- Naming/layout inconsistencies
Include exact paths and, when possible, minimal reproduction steps.
