# runtime/outputs Changelog

This changelog tracks versioned changes to the canonical artifacts stored under `runtime/outputs/` (templates, taxonomy, schemas, and examples) to preserve provenance and auditability.

Format: Keep a Changelog (https://keepachangelog.com/en/1.1.0/)  
Versioning: Semantic Versioning (https://semver.org/)
## How to use this log

- Add a new entry for every change that affects any canonical artifact under `runtime/outputs/`.
- Prefer “Added / Changed / Deprecated / Removed / Fixed / Security”.
- Record *what* changed and *why* (briefly), and include pointers to the exact file paths impacted.
- Keep entries human-auditable (avoid opaque hashes unless necessary).
## [Unreleased]

### Added
- N/A

### Changed
- N/A

### Fixed
- N/A
## [0.1.0] - 2025-12-26

### Added
- Established this changelog as the audit trail for canonical `runtime/outputs/` artifacts.
- Canonical scaffold intent (single source of truth) for the following artifacts and their future evolution:
  - `runtime/outputs/templates/prereg_template.md` (authoritative preregistration template)
  - `runtime/outputs/taxonomy/taxonomy.json` (canonical taxonomy definition)
  - `runtime/outputs/taxonomy/taxonomy.schema.json` (schema for validating taxonomy structure)
  - `runtime/outputs/taxonomy/example_annotation.json` (example annotation using the taxonomy, if present)

### Notes
- This version marks the point from which subsequent modifications to the above artifacts should be recorded here to maintain provenance across agent-created deliverables.
