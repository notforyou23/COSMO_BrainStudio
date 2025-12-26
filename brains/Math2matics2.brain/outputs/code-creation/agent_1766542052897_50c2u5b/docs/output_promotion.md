# Output promotion and canonical indexing

This repository can contain artifacts produced by multiple autonomous agents. Those agents often write files inside their own working directories (for example `agent_*/`, `runs/`, or other job-specific folders). The **audit step** that reports the number of documents typically **only scans `outputs/`** (and sometimes a small allowlist of other canonical locations). If useful artifacts remain under agent directories, the audit will legitimately report **0 documents** even though the repository contains many files.

This document explains (1) why audits report 0 documents, (2) how the promotion tooling consolidates agent artifacts into `outputs/`, and (3) how `outputs/index.md` is generated and maintained.
## Why the audit reports 0 documents

Audits are designed to be deterministic and avoid noise. To achieve that, they generally:

- Look for deliverables in **one canonical directory**: `outputs/`
- Ignore agent scratch space to avoid:
  - transient logs and prompts (e.g., `*prompt*.txt`, `*introspection*`)
  - duplicated intermediate drafts across runs
  - non-deliverable caches, checkpoints, and binaries

If agents write deliverables to locations like `agent_*/README.md` or `agent_*/first_artifact.md`, the audit won't count them unless they are **promoted** into `outputs/`.
## What “promotion” means

**Promotion** is a controlled copy operation:

1. **Discover** candidate artifacts in agent-specific directories using configurable patterns.
2. **Filter** candidates using an allowlist/denylist (e.g., allow `*.md`, deny logs and hidden files).
3. **Copy** them into the canonical `outputs/` directory.
4. **Rename safely** on collisions so nothing is overwritten unintentionally.
5. **Regenerate** `outputs/index.md` so reviewers and audits can find everything in one place.

The source files are left intact; `outputs/` becomes the canonical “publication” surface.
## Promotion CLI (high-level behavior)

The promotion script (`tools/promote_artifacts.py`) is intended to be run locally or in CI. At a high level it:

- Scans for agent directories (configurable default patterns such as `agent_*`).
- Collects eligible files (for example: `README.md`, `*_artifact*.md`, `research_template.md`, and other Markdown deliverables).
- Copies them to `outputs/` with a stable, collision-safe naming policy.

### Collision-safe naming

If multiple agents produced a file with the same name (e.g., many `README.md` files), the promoter avoids overwriting by using a deterministic suffix, typically derived from the source path. Example strategies:

- `README.md` → `agent_1234__README.md`
- `first_artifact.md` → `agent_5678__first_artifact.md`

The exact policy is configured in `tools/output_promotion_config.py` and should be deterministic so repeated runs produce the same filenames.
## How `outputs/index.md` is generated and maintained

`outputs/index.md` is a **generated** Markdown index of everything currently present in `outputs/` (excluding the index itself). The promotion tool:

- Enumerates files in `outputs/`
- Sorts them (typically by filename for stable diffs)
- Writes a list of Markdown links such as:

  - [`agent_1234__README.md`](agent_1234__README.md)
  - [`agent_5678__first_artifact.md`](agent_5678__first_artifact.md)

Because this index is generated, it should be treated as **derived** from the contents of `outputs/`:

- If you add/remove/rename promoted files, re-run the promoter to refresh the index.
- Manual edits are discouraged because they will be overwritten on the next generation run.
## Configuration: what gets promoted (and what does not)

Default discovery and filtering rules live in `tools/output_promotion_config.py`. Typical knobs include:

- **Agent directory patterns**: which folders to search (e.g., `agent_*`)
- **Allowlist**: what file types/names count as deliverables (e.g., `*.md`)
- **Denylist**: what to exclude even if it matches the allowlist
  - prompt transcripts, introspection logs, build artifacts
  - hidden files and temporary files
- **Destination naming**: how to construct unique output filenames
- **Index formatting**: heading text, sorting, and link style

If the audit still reports 0 documents after running promotion, it usually means one of:
- No files matched the allowlist (e.g., artifacts are `*.txt` but only `*.md` is allowed)
- Files were all denied by denylist rules (e.g., named like prompt logs)
- The promoter was not run, or `outputs/` was not committed/preserved
## Recommended workflow

1. Let agents produce artifacts wherever they normally do (agent directories are fine).
2. Run the promotion CLI to publish deliverables into `outputs/`.
3. Ensure `outputs/index.md` is generated/updated by the same run.
4. The audit step should now find documents under `outputs/` and report a non-zero count.

The key idea: **agents can write anywhere; audits only count what is canonically published to `outputs/`.**
