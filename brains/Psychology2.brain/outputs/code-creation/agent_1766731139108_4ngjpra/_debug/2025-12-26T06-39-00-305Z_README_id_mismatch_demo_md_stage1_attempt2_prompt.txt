You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Implement an ID system + mismatch checker that links (a) extraction rows, (b) taxonomy annotations (JSONL), and (c) prereg fields; include a demo that intentionally triggers an ID mismatch and outputs a human-readable report to runtime/outputs/_build/.
Project: generated_script_1766731139295 (python script)

Target file details:
- Path: README_id_mismatch_demo.md
- Purpose: Documentation explaining the ID scheme, file formats, how the checker works, and how to run the demo to generate the human-readable report under runtime/outputs/_build/.
- Category: documentation

Other planned files (for context only):
- scripts/id_mismatch_demo.py: Runnable demo script that builds IDs linking extraction rows, taxonomy JSONL annotations, and prereg fields, intentionally introduces an ID mismatch, runs the checker, and writes a human-readable report to runtime/outputs/_build/.
- src/id_system.py: Core ID system and mismatch-checking library that defines canonical ID construction, loads extraction/annotation/prereg inputs, validates cross-link integrity, and produces structured mismatch findings plus report text.
- src/io_formats.py: Input/output helpers for reading extraction CSV/TSV rows, taxonomy annotations in JSONL, and prereg fields in JSON/CSV while preserving stable identifiers and emitting normalized records for checking.
- runtime/fixtures/demo_extraction.csv: Example extraction table fixture containing a small set of rows with stable keys used to demonstrate ID linking and mismatch detection.

Reference insights:
- [INTROSPECTION] 2025-12-26T05-31-29-063Z_plan_attempt1_prompt.txt from code-creation agent agent_1766727087125_7ty4nyb: You are planning a p
- [AGENT: agent_1766728379667_fc10qed] {"agentId":"agent_1766728379667_fc10qed","timestamp":"2025-12-26T05:55:23.430Z","files":[{"filename":"c
- [AGENT: agent_1766727472302_lzscpmx] Cycle 39 consistency review (divergence 0.92):
Summary assessment (concise)

1) Areas of agreement
- Pe
- [AGENT: agent_1766729445747_n3o9cbv] {"agentId":"agent_1766729445747_n3o9cbv","timestamp":"2025-12-26T06:12:09.374Z","files":[{"filename":"v
- [FORK_RESULT:fork_11] Small, low-cost tweaks to choice architecture—like setting defaults, reordering options, adjusting framing, salience, 

Key requirements:
- examples

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Documentation explaining the ID scheme, file formats, how the checker works, and how to run the demo to generate the human-readable report under runtime/outputs/_build/.
- Line budget for this stage: <= 150 new/changed lines.

Implementation tasks (execute using Python in this environment):
1. from pathlib import Path
2. import json
3. target_path = Path('/mnt/data').joinpath('README_id_mismatch_demo.md')
4. target_path.parent.mkdir(parents=True, exist_ok=True)
5. Build the entire stage deliverable (<= 150 lines) as a list named chunks where each item is a multiline string representing a contiguous block of code without leading or trailing blank lines.
6. final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
7. target_path.write_text(final_text, encoding='utf-8')
8. print('FILE_WRITTEN:README_id_mismatch_demo.md')
9. print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/mnt/data"))) for p in target_path.parent.glob('*') if p.is_file())))

Constraints:
- Ensure the new file fully satisfies the stage goal with no placeholders or TODO markers.
- Keep the newly written code within the stated line/character budget.
- Keep console output short (only FILE_WRITTEN / DIR_STATE plus essential status).
- Do not touch files outside README_id_mismatch_demo.md.
- After writing the file, provide a one-sentence summary. Do not list the file contents in the final message.
