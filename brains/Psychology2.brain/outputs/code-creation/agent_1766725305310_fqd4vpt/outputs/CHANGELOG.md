# Changelog

This file tracks changes to artifacts produced in `/outputs` across cycles.

## Format (stable for automated appends)

Each release block MUST follow this exact structure:

- `## [X.Y.Z] - YYYY-MM-DD`
- Optional short summary line(s).
- Zero or more of the following subsections (only include those with items):
  - `### Added`
  - `### Changed`
  - `### Fixed`
  - `### Removed`
- Bullet items must begin with `- ` and be single-line where possible.

Automated tooling may append by inserting a new release block at the top (below the Unreleased block), or by adding bullets under an existing block.

## [Unreleased]

### Added
- Initialized versioned changelog with a minimal, append-friendly structure.
