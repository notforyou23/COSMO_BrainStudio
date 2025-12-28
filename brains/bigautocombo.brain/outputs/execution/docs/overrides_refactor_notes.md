# Overrides refactor notes (Stage 1)

This document consolidates Stage 1 notes for refactoring the overrides subsystem into small reusable modules with clear boundaries: schema/validation, YAML I/O, example generation, and application/merge.
## Goals

- Make override behavior deterministic, testable, and reusable across CLI/scripts.
- Separate concerns so YAML parsing, schema validation, example YAML generation, and override application do not depend on each other cyclically.
- Improve error messages (path-aware) and avoid ambiguous implicit conversions.
- Keep public API small and stable; keep implementation details private.
## Module boundaries (new structure)

### `src/overrides/schema.py`
**Responsibilities**
- Define the override configuration schema (types, required/optional fields, defaults).
- Provide validation utilities that:
  - verify structure and types,
  - apply defaults deterministically,
  - produce readable, path-addressed errors.

**Non-responsibilities**
- No YAML loading/dumping.
- No filesystem I/O.
- No merge/application logic beyond validating and normalizing the overrides object.

**Outputs**
- A normalized (validated) overrides object suitable for application.
- Error types/messages that can be surfaced by YAML loaders and the CLI.
### `src/overrides/yaml_support.py`
**Responsibilities**
- Provide YAML load/dump helpers with consistent options:
  - stable formatting where feasible,
  - round-trip-friendly behavior when supported by the YAML library,
  - clear syntax/parse errors including filename and line/column if available.
- Centralize YAML dependency choices and configuration so other modules do not set loader options ad hoc.

**Non-responsibilities**
- No schema decisions.
- No validation rules; it may call `schema.validate(...)` only in higher-level orchestration, not inside low-level YAML utilities (to keep I/O pure and reusable).

**Guiding behavior**
- Loading returns Python objects only (dict/list/scalars).
- Dumping is deterministic to minimize noisy diffs for generated examples.
### `src/overrides/overrides_example_yaml.py`
**Responsibilities**
- Generate a canonical example overrides YAML document derived from the schema:
  - includes defaults,
  - includes comments explaining fields and common patterns,
  - shows representative entries for list/map sections.

**Non-responsibilities**
- No file writing; it returns a string.
- No application logic.

**Design notes**
- Example generation must stay aligned with `schema.py`; avoid hardcoding field names in multiple places.
- If comments are supported, they should be derived from schema field metadata (e.g., descriptions).
### `src/overrides/apply.py`
**Responsibilities**
- Implement the core override-application engine that merges validated overrides into target data structures deterministically.
- Provide a small, explicit API such as:
  - `apply_overrides(target, overrides) -> new_target` (preferred: pure function),
  - or `apply_overrides_inplace(target, overrides)` when performance/mutation is needed.

**Non-responsibilities**
- No YAML loading/dumping.
- No schema definition; assumes input overrides are already validated/normalized.

**Determinism rules**
- Map merges are key-based and stable.
- List operations (if supported) are explicit (e.g., replace/append/remove by selector) and never depend on incidental ordering unless the schema states order matters.
- Unknown keys should be rejected by validation, not silently ignored during apply.
## Data flow (recommended orchestration)

1. Load YAML: `yaml_support.load_yaml(path) -> raw_obj`
2. Validate/normalize: `schema.validate_and_normalize(raw_obj) -> overrides`
3. Apply: `apply.apply_overrides(target_obj, overrides) -> result`
4. Optional: dump results or write back files using `yaml_support.dump_yaml(...)`

This keeps each step independently testable and allows non-YAML inputs (e.g., JSON, dict literals) to reuse the same validation and apply stages.
## Error handling conventions

- Errors must include a logical path (e.g., `overrides.rules[2].match.key`) and, when coming from YAML, the source filename and location if available.
- Validation errors are “actionable”: they explain expected type/shape, allowed values, and show the offending value.
- Application errors are reserved for situations validation cannot catch (e.g., selector references a missing entity in the target).
## Public API surface (Stage 1 intent)

Keep imports simple for callers:

- `from overrides.schema import validate_and_normalize`
- `from overrides.yaml_support import load_yaml, dump_yaml`
- `from overrides.overrides_example_yaml import render_example_overrides_yaml`
- `from overrides.apply import apply_overrides`

Avoid re-exporting everything from `__init__` until the API stabilizes; prefer explicit imports in application code.
## Compatibility and migration notes

- Existing overrides files should continue to work if they conform to the schema; differences should fail fast with clear errors rather than produce silent behavior changes.
- When a legacy field is deprecated, normalization may support it temporarily (mapping to the new field) but must emit a clear warning path/message at a single point (preferably schema normalization).
## Testing strategy (what Stage 1 enables)

- Unit tests for `schema.py`: validation, defaults, rejection of unknown keys, path formatting.
- Unit tests for `yaml_support.py`: parse errors include filename, dump is stable.
- Golden-file tests for `overrides_example_yaml.py`: output stable across runs.
- Property-style tests for `apply.py`: idempotence where applicable, determinism, and “validate then apply” invariants.
