You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Create and commit the first two artifacts immediately: /outputs/README.md (artifact rules + naming conventions + 'ship every cycle' checklist) and one seed deliverable (e.g., /outputs/roadmap_v1.md or /outputs/bibliography_system.md) in the same cycle.
Project: and commit the first two artifacts immediately: /outputs/README.md (artifact rules + naming conventions + 'ship every cycle' checklist) and one seed deliverable (e.g., /outputs/roadmap_v1.md or /outputs/bibliography_system.md) in the same cycle. (python script)

Target file details:
- Path: outputs/README.md
- Purpose: Defines /outputs artifact rules, naming conventions, and a 'ship every cycle' checklist to ensure deterministic, auditable deliverables each iteration.
- Category: documentation

Other planned files (for context only):
- outputs/roadmap_v1.md: Provides the seed deliverable roadmap outlining planned /outputs artifacts, milestones, and acceptance criteria for the Python script implementation mission.

Reference insights:
- [AGENT: agent_1766538470010_nvdr7ld] Cycle 4 consistency review (divergence 0.96):
Summary judgement: the three branches are largely compati
- [AGENT: agent_1766538161484_b5yh91f] Cycle 1 consistency review (divergence 0.97):
Summary (high-level): The three branches are about differ
- [AGENT INSIGHT: agent_1766540049061_an5rb16] Computational Plan: ## Computational execution plan (focused on deterministic `/outputs/` artif
- [AGENT INSIGHT: agent_1766540049061_an5rb16] Computational Plan: ## Computational execution plan (focused on deterministic `/outputs/` artif
- [INTROSPECTION] 2025-12-24T01-29-38-707Z_scripts_run_pipeline_py_stage1_attempt1_prompt.txt from code-creation agent agent_1766539771836_cun

Key requirements:
- documentation

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Defines /outputs artifact rules, naming conventions, and a 'ship every cycle' checklist to ensure deterministic, auditable deliverables each iteration.
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
