# Outputs (minimum v1)

This directory is the project’s **authoritative, versioned output set**. It is designed so that each research/pipeline cycle leaves a durable trace that can be reviewed without re-running code.

## Outputs policy (enforced)

**Rule:** *Every research cycle must add or update at least one file in `outputs/`.*

Why: it guarantees that each cycle produces tangible, reviewable progress (decisions, findings, datasets, logs, etc.), and prevents “silent” runs that only modify transient state.

### How enforcement works (conceptually)

A typical cycle does the following:

1. **Select an outputs directory** (prefer `./outputs`, but support a **portable fallback** when that path is unwritable—e.g., running in restricted environments). The selected directory is treated as the “effective outputs root” for the cycle.
2. **Snapshot** the pre-run state (file list + modification times and/or hashes).
3. Run the cycle’s work.
4. **Validate** that at least one file under the effective outputs root was created or changed.
5. If not, fail the cycle (or emit an explicit error) so the missing output is addressed immediately.

This project’s pipeline/utility code is expected to implement the above checks and to ensure the minimum v1 files exist.

## Minimum v1 required documents

These documents are required for the “minimum v1” output set:

- `outputs/README.md` (this file)  
  Index + policy explanation + how the per-cycle update rule is satisfied.

- `outputs/core_findings.md`  
  The consolidated, current “single source of truth” for findings and decisions.  
  **Recommended usage:** treat this as the default target to update every cycle (append a dated entry or revise sections), ensuring the policy is met even when no new artifacts are generated.

## Recommended per-cycle update pattern

To keep runs consistent and reviewable, each cycle should do at least one of:

- Append a brief entry to `core_findings.md` summarizing what changed (inputs, decisions, results).
- Add a new artifact (e.g., `experiment_YYYYMMDD.md`, `results.json`, `errors.log`) and reference it from `core_findings.md`.

## Notes on portability

Some environments may not allow writing to a fixed `/outputs` path. The enforcement logic should therefore:

- Prefer a repo-relative `outputs/` directory when possible.
- Fall back to an alternative writable location while still producing an “outputs-like” directory.
- Make the chosen effective outputs root discoverable (e.g., printed at runtime) so reviewers can find the generated artifacts.
