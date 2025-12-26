# End-to-End (E2E) Documentation

This document is the **entry point** for running and validating the project end-to-end. It is intentionally thin and **composes reusable sections** from `docs/e2e/README_e2e_sections/` so the same guidance can be referenced by CI docs, developer docs, and release notes without duplication.

## How this README is structured (modular sections)

- Overview: [`README_e2e_sections/00_overview.md`](README_e2e_sections/00_overview.md)
- Prerequisites: [`README_e2e_sections/10_prerequisites.md`](README_e2e_sections/10_prerequisites.md)
- Configuration: [`README_e2e_sections/20_configuration.md`](README_e2e_sections/20_configuration.md)
- Running locally: [`README_e2e_sections/30_running_locally.md`](README_e2e_sections/30_running_locally.md)

> If you need the “full narrative” start-to-finish, read those sections in order; this file only provides the glue, pointers, and shared conventions.
## Quick start (links-first)

1. Read the scope and expected outputs: **Overview** → `00_overview.md`  
2. Ensure your environment matches expectations: **Prerequisites** → `10_prerequisites.md`  
3. Confirm your config is valid and complete: **Configuration** → `20_configuration.md`  
4. Execute the E2E run and interpret results: **Running locally** → `30_running_locally.md`

## Shared artifacts and workflows (project-wide references)

These references are used across E2E docs and are the “single source of truth” locations you should update when behavior changes:

- **E2E orchestrators / entrypoints**
  - Prefer a single top-level runner script when provided (for example, a `scripts/run_all.sh`-style entrypoint) and keep per-step commands documented in `30_running_locally.md`.
- **CI requirements / pinned deps**
  - When a CI requirements file exists (for example, `docs/e2e/requirements-ci.txt`), treat it as the canonical minimal set for deterministic runs; local environments may add extras but should not remove pins required by CI.
- **Prompts, exports, and introspection logs**
  - If the project writes “introspection” or “export prompt” artifacts, keep them in their designated docs area and reference them from the relevant section file (overview/prereqs/config/run) rather than duplicating content here.

## Conventions

- **Reusability rule:** actionable guidance lives in the section files; this README only links and summarizes.
- **Stability rule:** section file names are stable (so external links don’t break); add new sections as `NN_topic.md` where `NN` keeps ordering consistent.
- **Change rule:** if you change E2E behavior (flags, outputs, required env vars), update the relevant section file and ensure this README still accurately points to it.

## Troubleshooting escalation

If you cannot complete an E2E run after following the section docs, capture and share:
- the exact command(s) run,
- the config file(s) used (with secrets removed),
- the first error trace and the final summary output,
- OS/Python version and any container/runtime details.

Then iterate by tightening the relevant reusable section so the next person can follow it without tribal knowledge.
