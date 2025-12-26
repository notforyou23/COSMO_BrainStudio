# Core findings (consolidated)

This document is the stable, per-cycle-updated record of key decisions for project **generated_script_1766542736630**. It is intentionally short and action-oriented.

## Current consolidated decisions

### Outputs policy (required per research cycle)
- **Rule:** every research cycle must add or update **at least one file** in the `outputs/` directory (the “outputs set”).
- **Purpose:** ensure each cycle leaves an auditable artifact (documentation, results, metrics, or other deliverables), rather than only code changes or ephemeral logs.
- **Minimum v1 outputs set:** at least:
  - `outputs/README.md` (index + policy explanation)
  - `outputs/core_findings.md` (this file; consolidated decisions)

### Portability of `/outputs`
- The preferred directory is `outputs/` at the project root, but it may be **unwritable** in some environments.
- The pipeline must therefore implement a **portable fallback** strategy:
  1. Try the preferred `outputs/` directory.
  2. If not writable, fall back to a writable alternative (e.g., a project-local temp directory) while still producing an “outputs set”.
- The enforcement logic should detect the effective writable outputs directory at runtime and report it clearly.

### Enforcement approach (expected implementation shape)
- At cycle start, snapshot the outputs directory state (file names + mtimes/hashes).
- At cycle end, validate that at least one file was added or changed compared to the snapshot.
- If validation fails, the cycle should be marked as failed (or should automatically update a designated output file, e.g., this one) to satisfy policy.

## Cycle update protocol (how this file should change)
Each research cycle should update **at minimum** one of:
- this `core_findings.md` with new decisions, resolved questions, or updated enforcement details, or
- `README.md` with new outputs inventory/policy clarifications, or
- a cycle-specific artifact (e.g., `cycle_YYYYMMDD_HHMM.md`, `results.json`, `metrics.csv`) that represents the cycle’s output.

This ensures a continuous, append-only trail of meaningful progress across cycles.

## Notes from prior reviews (high-level)
- Prior multi-branch consistency reviews indicated the branches are **largely compatible** with minimal divergence.
- A key insight to carry forward is the need for **portable outputs handling** (do not assume `/outputs` is writable).
