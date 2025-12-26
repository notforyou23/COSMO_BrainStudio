# Modularization notes (Stage 1)

This document captures the refactor decisions used to turn the initial “single-file / coupled” CLI prototype into a small, reusable `dgpipe` package with clear module boundaries and an API suitable for extension.

## Goals of the refactor

- **Stability of public API**: expose a minimal, intentional surface from `dgpipe.__init__`.
- **Extensibility**: allow users to plug in new stages/runners without editing core files.
- **Testability**: move side-effectful CLI and IO to the edges; keep models/protocols pure.
- **Documentation as an artifact**: README and developer notes explain where to add code.

## Module boundaries (what goes where)

### `src/dgpipe/models.py` (domain dataclasses)
Holds “nouns” and durable structures shared across the codebase:

- Pipeline/spec/config objects (e.g., stage definitions, pipeline definition, run configuration).
- Result objects (e.g., per-stage result, pipeline run summary).
- Lightweight validation helpers that do not import CLI/FS/network.

**Why**: models are imported broadly; keeping them dependency-light avoids import cycles and allows reuse by CLI, plugins, and tests.

### `src/dgpipe/protocols.py` (interfaces / contracts)
Defines typed interfaces for extensibility:

- `Stage` protocol: “given inputs + context, produce output/result”.
- `Runner` protocol: “orchestrate execution of stages”.
- IO abstractions (if used): e.g., readers/writers, artifact stores.

**Why**: protocols decouple implementations from callers (CLI can depend on the contract, not concrete classes). This is the main seam for plugins.

### `src/dgpipe/__init__.py` (public package entrypoint)
Exports the intended public API and version, without side effects:

- `__version__`
- Convenience imports (selected models/protocols only).
- No CLI parsing, no reading environment variables, no logging configuration at import time.

**Why**: importing `dgpipe` should be safe in any environment (REPL, tests, plugin discovery).

### `README.md` (project-level guide)
Focuses on user-facing tasks:

- What dgpipe is, how to install, core CLI usage.
- Small examples and “extension points” pointing to `protocols.py` and `models.py`.
- Minimal internal implementation details (those live here in this file).

## CLI vs library separation

- **CLI layer** (e.g., `src/dgpipe/cli.py` or console entrypoint) should:
  - parse args, load config, call library functions/classes, format output.
- **Library layer** should:
  - accept explicit parameters; return structured results (models).
  - avoid printing; leave that to CLI.

This separation makes it possible to reuse `dgpipe` in notebooks/other apps and keeps the CLI thin.

## Import/cycle rules (practical guidance)

- `models.py` should not import from other `dgpipe` modules (except stdlib/typing).
- `protocols.py` may reference model types (via forward refs if needed) but should avoid importing implementations.
- CLI and concrete implementations may import both models and protocols.
- If two modules start importing each other, move shared types into `models.py` (data) or `protocols.py` (behavioral contracts).

## Migration guide: from exported prompt artifacts to real modules

The repository contains exported “stage1_export” prompt artifacts (e.g., `*_export_prompt.txt`). Treat these as **design snapshots**. The migration approach is:

1. **Extract stable definitions** into `models.py` / `protocols.py`.
   - If a type is referenced across multiple places → it belongs in `models.py` (data) or `protocols.py` (contract).
2. **Collapse duplicated logic** into single helpers close to the domain:
   - parsing/normalization of pipeline specs → `models.py` (or `dgpipe/spec.py` later).
   - orchestration logic → a runner implementation module (later stage).
3. **Keep CLI-specific behavior out of core**:
   - printing, exit codes, argparse/typer, filesystem layout decisions.
4. **Expose only what you want supported** via `dgpipe.__init__`.
   - internal helpers remain unexported to preserve refactor freedom.

## Rationale for “models + protocols first”

Starting with models/protocols provides a backbone that other modules can depend on without entanglement. It also enables incremental replacement: implementations can change without forcing changes in the CLI or downstream users as long as the contracts remain stable.

## Reuse patterns encouraged

- Define new stages by implementing the `Stage` protocol and returning standard result models.
- Introduce new runners by implementing the `Runner` protocol; keep execution policy (parallelism, retries) out of stage logic.
- Use dataclasses/immutable configs for reproducible runs (e.g., serialize configs, compare runs).

## What to change when adding features

- **New data fields / outputs**: extend `models.py` (with backward-compatible defaults when possible).
- **New extension point**: add a new Protocol in `protocols.py` and update README “Extension points”.
- **New CLI command**: add to CLI module; call into library APIs; do not add domain logic to CLI.
- **Breaking changes**: reflect in `__init__.py` exports and document in README; consider aliasing old names temporarily.
