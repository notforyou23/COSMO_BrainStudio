You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Reproduce the failure with the smallest possible script, capture full stderr/stdout + environment metadata, identify the crash boundary (startup vs. filesystem vs. imports), implement a one-file smoke test that writes a timestamped log under /outputs/qa/logs/.
Project: generated_script_1766624644367 (python script)

Target file details:
- Path: scripts/qa/README.md
- Purpose: Usage documentation for running the smoke/repro script locally/CI, interpreting stage results, and locating timestamped logs under outputs/qa/logs/.
- Category: documentation

Other planned files (for context only):
- scripts/qa/smoke_repro.py: One-file smoke/repro script that captures full stdout/stderr and rich environment metadata, probes crash boundaries (startup vs filesystem vs imports), and writes a timestamped log under /outputs/qa/logs/ with clear stage demarcations and exit codes.

Reference insights:
- [INTROSPECTION] 2025-12-25T00-50-00-140Z_outputs_qa_RUN_INSTRUCTIONS_md_stage1_attempt1_prompt.txt from code-creation agent agent_1766623798
- [INTROSPECTION] 2025-12-25T00-21-55-842Z_scripts_qa_run_sh_stage1_attempt1_prompt.txt from code-creation agent agent_1766622114110_412seks: 
- [AGENT INSIGHT: agent_1766614627655_4lrkb6s] Implication 1: Measurement design becomes a hidden equity lever (and risk). If “genius” persist
- [CONSOLIDATED] Establishing clear, machine-validated structure (schemas) and lightweight automation (scaffolding, indexing, path canonicaliz
- [INTROSPECTION] 2025-12-24T23-35-50-952Z_scripts_validate_outputs_py_stage1_attempt2_prompt.txt from code-creation agent agent_1766619349563

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Usage documentation for running the smoke/repro script locally/CI, interpreting stage results, and locating timestamped logs under outputs/qa/logs/.
- Line budget for this stage: <= 150 new/changed lines.

Implementation tasks (execute using Python in this environment):
1. from pathlib import Path
2. import json
3. target_path = Path('/mnt/data').joinpath('scripts/qa/README.md')
4. target_path.parent.mkdir(parents=True, exist_ok=True)
5. Build the entire stage deliverable (<= 150 lines) as a list named chunks where each item is a multiline string representing a contiguous block of code without leading or trailing blank lines.
6. final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
7. target_path.write_text(final_text, encoding='utf-8')
8. print('FILE_WRITTEN:scripts/qa/README.md')
9. print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/mnt/data"))) for p in target_path.parent.glob('*') if p.is_file())))

Constraints:
- Ensure the new file fully satisfies the stage goal with no placeholders or TODO markers.
- Keep the newly written code within the stated line/character budget.
- Keep console output short (only FILE_WRITTEN / DIR_STATE plus essential status).
- Do not touch files outside scripts/qa/README.md.
- After writing the file, provide a one-sentence summary. Do not list the file contents in the final message.
