# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows semantic versioning where applicable.
## [Unreleased]

### Changed
- Consolidated agent-produced artifacts that previously lived in agent-specific directories (e.g., `code-creation/**/outputs/*`) into the single canonical `outputs/` scaffold to prevent duplication and drift.
- Updated the artifact gate policy to validate **exact canonical paths under `outputs/`** (no agent-specific paths), ensuring downstream consumers read from one deterministic location.

### Added
- Canonical allowlist file `config/artifact_gate_paths.json` that enumerates required artifact paths under `outputs/` for gate enforcement.
- Standalone artifact gate checker script `scripts/check_artifact_gate.py` that validates the canonical allowlist and exits nonzero on missing/mismatched artifacts.
- Consolidation utility `scripts/consolidate_outputs.py` that discovers agent output artifacts, copies/merges them into `outputs/` deterministically, and can optionally update this changelog.
- Canonical consolidated artifact `outputs/task_taxonomy_codebook_v0.1.json` as the single source of truth for the task taxonomy codebook used by gating and downstream steps.

### Notes
- When the same artifact exists in multiple agent directories, consolidation preserves existing canonical files deterministically to avoid churn and keep gating stable.
- The artifact gate intentionally rejects non-canonical locations to enforce the single `outputs/` scaffold.
