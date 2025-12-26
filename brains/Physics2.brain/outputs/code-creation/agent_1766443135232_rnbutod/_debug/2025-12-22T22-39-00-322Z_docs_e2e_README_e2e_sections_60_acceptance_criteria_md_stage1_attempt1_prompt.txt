You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Refactor and modularize reusable code artifacts: README_e2e.md
Project: generated_script_1766443139257 (python script)

Target file details:
- Path: docs/e2e/README_e2e_sections/60_acceptance_criteria.md
- Purpose: Reusable acceptance criteria section defining pass/fail conditions, required checks, and reporting expectations for E2E.
- Category: documentation

Other planned files (for context only):
- docs/e2e/README_e2e.md: Refactored end-to-end documentation with modular, reusable sections and clear references to shared artifacts and workflows.
- docs/e2e/README_e2e_sections/00_overview.md: Reusable overview section explaining the E2E scope, goals, and high-level architecture used by README_e2e.md.
- docs/e2e/README_e2e_sections/10_prerequisites.md: Reusable prerequisites section covering environment requirements, dependencies, and setup assumptions for E2E runs.
- docs/e2e/README_e2e_sections/20_configuration.md: Reusable configuration section describing config files, required keys, validation expectations, and examples.

Reference insights:
- [INTROSPECTION] 2025-12-22T22-13-32-823Z_docs_e2e_README_e2e_md_stage1_export_export_prompt.txt from code-creation agent agent_1766441606958
- [INTROSPECTION] 2025-12-22T22-13-32-823Z_docs_e2e_requirements-ci_txt_stage1_attempt1_prompt.txt from code-creation agent agent_176644160695
- [CONSOLIDATED] Develop a prioritized, project-mapped collaboration plan that names specific experimental/analogue and theory/compute partner
- [INTROSPECTION] 2025-12-22T21-52-07-285Z_scripts_run_all_sh_stage1_export_export_prompt.txt from code-creation agent agent_1766440311238_cpn
- [CONSOLIDATED] Complex, multi-stakeholder research roadmaps are best executed by first locking a clear document/acceptance architecture, the

Key requirements:
- documentation

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Reusable acceptance criteria section defining pass/fail conditions, required checks, and reporting expectations for E2E.
- Line budget for this stage: <= 150 new/changed lines.

Implementation tasks (execute using Python in this environment):
1. from pathlib import Path
2. import json
3. target_path = Path('/mnt/data').joinpath('docs/e2e/README_e2e_sections/60_acceptance_criteria.md')
4. target_path.parent.mkdir(parents=True, exist_ok=True)
5. Build the entire stage deliverable (<= 150 lines) as a list named chunks where each item is a multiline string representing a contiguous block of code without leading or trailing blank lines.
6. final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
7. target_path.write_text(final_text, encoding='utf-8')
8. print('FILE_WRITTEN:docs/e2e/README_e2e_sections/60_acceptance_criteria.md')
9. print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/mnt/data"))) for p in target_path.parent.glob('*') if p.is_file())))

Constraints:
- Ensure the new file fully satisfies the stage goal with no placeholders or TODO markers.
- Keep the newly written code within the stated line/character budget.
- Keep console output short (only FILE_WRITTEN / DIR_STATE plus essential status).
- Do not touch files outside docs/e2e/README_e2e_sections/60_acceptance_criteria.md.
- After writing the file, provide a one-sentence summary. Do not list the file contents in the final message.
