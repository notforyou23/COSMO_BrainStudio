You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Initialize /outputs with a README (artifact rules, naming/versioning), plus folders: /outputs/meta_analysis_starter_kit, /outputs/task_taxonomy, /outputs/prereg, /outputs/tools; add a simple changelog file and a LICENSE.
Project: generated_cli_tool_1766728379901 (python cli_tool)

Target file details:
- Path: outputs/task_taxonomy/README.md
- Purpose: Describes the task taxonomy folder contents, recommended taxonomy file structure, and versioning for updates.
- Category: documentation

Other planned files (for context only):
- outputs/README.md: Documents artifact storage rules for /outputs including directory purpose, naming/versioning conventions, and reproducibility expectations.
- outputs/meta_analysis_starter_kit/README.md: Explains what belongs in the meta_analysis_starter_kit folder and provides a minimal template/checklist for adding starter-kit artifacts.
- outputs/prereg/README.md: Defines preregistration artifact expectations and naming/versioning rules for prereg documents stored under /outputs/prereg.
- outputs/tools/README.md: Documents the purpose of /outputs/tools and how to record tool outputs, parameters, and run metadata for traceability.

Reference insights:
- [INTROSPECTION] 2025-12-26T05-01-46-647Z_outputs_README_md_stage1_attempt1_prompt.txt from code-creation agent agent_1766725305310_fqd4vpt: 
- [INTROSPECTION] 2025-12-26T05-01-46-647Z_README_md_stage1_attempt2_prompt.txt from code-creation agent agent_1766725305310_fqd4vpt: You are 
- [INTROSPECTION] 2025-12-26T05-24-51-891Z_README_md_stage1_attempt1_prompt.txt from code-creation agent agent_1766726690398_unoowq2: You are 
- [AGENT: agent_1766727472302_lzscpmx] Cycle 39 consistency review (divergence 0.92):
Summary assessment (concise)

1) Areas of agreement
- Pe
- [INTROSPECTION] cli.py from code-creation agent agent_1766725784487_bkavju7: """psyprim CLI: standardized primary-source workflows + lightwe

Key requirements:
- documentation

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Describes the task taxonomy folder contents, recommended taxonomy file structure, and versioning for updates.
- Line budget for this stage: <= 150 new/changed lines.

Implementation tasks (execute using Python in this environment):
1. from pathlib import Path
2. import json
3. target_path = Path('/mnt/data').joinpath('outputs/task_taxonomy/README.md')
4. target_path.parent.mkdir(parents=True, exist_ok=True)
5. Build the entire stage deliverable (<= 150 lines) as a list named chunks where each item is a multiline string representing a contiguous block of code without leading or trailing blank lines.
6. final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
7. target_path.write_text(final_text, encoding='utf-8')
8. print('FILE_WRITTEN:outputs/task_taxonomy/README.md')
9. print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/mnt/data"))) for p in target_path.parent.glob('*') if p.is_file())))

Constraints:
- Ensure the new file fully satisfies the stage goal with no placeholders or TODO markers.
- Keep the newly written code within the stated line/character budget.
- Keep console output short (only FILE_WRITTEN / DIR_STATE plus essential status).
- Do not touch files outside outputs/task_taxonomy/README.md.
- After writing the file, provide a one-sentence summary. Do not list the file contents in the final message.
