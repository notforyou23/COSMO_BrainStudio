You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Create /outputs/README.md documenting artifact rules (naming, schemas, determinism, overwrite policy) and ensure the pipeline generates run_stamp.json + run.log + results.json + figure.png on every run.
Project: /outputs/README.md documenting artifact rules (naming, schemas, determinism, overwrite policy) and ensure the pipeline generates run_stamp.json + run.log + results.json + figure.png on every run. (json script)

Target file details:
- Path: outputs/README.md
- Purpose: Documents deterministic artifact rules for the /outputs directory including naming conventions, JSON schemas, overwrite policy, and required per-run files.
- Category: documentation

Other planned files (for context only):
- scripts/run.py: Implements a deterministic CLI pipeline that always writes outputs/run_stamp.json, outputs/run.log, outputs/results.json, and outputs/figure.png on every run with a consistent overwrite policy.
- src/pipeline.py: Provides the core deterministic computation and artifact-writing functions used by the CLI pipeline implementation.
- src/artifacts.py: Defines artifact schemas, validation, and deterministic serialization utilities for run_stamp.json, results.json, and run.log generation.
- src/plotting.py: Generates figure.png deterministically (fixed size, style, seed, and metadata handling) from computed results.

Reference insights:
- [AGENT: agent_1766538470010_nvdr7ld] Cycle 4 consistency review (divergence 0.96):
Summary judgement: the three branches are largely compati
- [AGENT INSIGHT: agent_1766540049061_an5rb16] Computational Plan: ## Computational execution plan (focused on deterministic `/outputs/` artif
- [AGENT INSIGHT: agent_1766540049061_an5rb16] Computational Plan: ## Computational execution plan (focused on deterministic `/outputs/` artif
- [AGENT: agent_1766538747481_xj9s0e3] Cycle 7 consistency review (divergence 0.98):
Summary judgment
All three branches are complementary per
- [AGENT: agent_1766539516432_lwvqffa] Cycle 13 consistency review (divergence 0.97):
Summary of agreement
- All branches aim to improve predi

Key requirements:
- documentation
- ci cd

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Documents deterministic artifact rules for the /outputs directory including naming conventions, JSON schemas, overwrite policy, and required per-run files.
- Line budget for this stage: <= 150 new/changed lines.

Implementation tasks (execute using Python in this environment):
1. from pathlib import Path
2. import json
3. target_path = Path('/mnt/data').joinpath('outputs/README.md')
4. target_path.parent.mkdir(parents=True, exist_ok=True)
5. Build the entire stage deliverable (<= 150 lines) as a list named chunks where each item is a multiline string representing a contiguous block of code without leading or trailing blank lines.
6. final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
7. target_path.write_text(final_text, encoding='utf-8')
8. print('FILE_WRITTEN:outputs/README.md')
9. print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/mnt/data"))) for p in target_path.parent.glob('*') if p.is_file())))

Constraints:
- Ensure the new file fully satisfies the stage goal with no placeholders or TODO markers.
- Keep the newly written code within the stated line/character budget.
- Keep console output short (only FILE_WRITTEN / DIR_STATE plus essential status).
- Do not touch files outside outputs/README.md.
- After writing the file, provide a one-sentence summary. Do not list the file contents in the final message.
