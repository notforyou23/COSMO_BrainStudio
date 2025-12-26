You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Create a versioned repository skeleton in the outputs directory (README, LICENSE, CONTRIBUTING, folder structure, and initial placeholder files) because the deliverables audit shows 0 files created despite completed agent work.
Project: versioned repository skeleton in the outputs directory (README, LICENSE, CONTRIBUTING, folder structure, and initial placeholder files) because the deliverables audit shows 0 files created despite completed agent work. (python script)

Target file details:
- Path: README.md
- Purpose: Top-level project overview explaining the repository purpose, structure, and how to generate the skeleton with the provided script.
- Category: documentation

Other planned files (for context only):
- LICENSE: Open-source license text for the repository to enable versioned distribution and reuse.
- CONTRIBUTING.md: Contribution guidelines describing workflow, branching, formatting, and how to add deliverables into the outputs skeleton.
- docs/README.md: Documentation hub outlining where audit deliverables live and how to navigate and extend documentation pages.
- outputs/.gitkeep: Placeholder file ensuring the outputs directory is versioned even when initially empty.

Reference insights:
- [AGENT: agent_1766435369695_ff3n77o] {"agentId":"agent_1766435369695_ff3n77o","goalId":"goal_60","containerId":"cntr_6949aa2efc508190b33cc8a
- [AGENT: agent_1766435369695_ff3n77o] {"agentId":"agent_1766435369695_ff3n77o","goalId":"goal_60","containerId":"cntr_6949aa2efc508190b33cc8a
- [AGENT: agent_1766429800561_x1eq349] {"agentId":"agent_1766429800561_x1eq349","goalId":"goal_10","containerId":"cntr_6949946c70308190aa4b76e
- [AGENT: agent_1766429800561_x1eq349] {"agentId":"agent_1766429800561_x1eq349","goalId":"goal_10","containerId":"cntr_6949946c70308190aa4b76e
- [AGENT INSIGHT: agent_1766438119610_eb2aof4] Sub-goal 1/7: Define the roadmap structure and page-level outline (12 pages) with required sect

Key requirements:
- documentation

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Top-level project overview explaining the repository purpose, structure, and how to generate the skeleton with the provided script.
- Line budget for this stage: <= 150 new/changed lines.

Implementation tasks (execute using Python in this environment):
1. from pathlib import Path
2. import json
3. target_path = Path('/mnt/data').joinpath('README.md')
4. target_path.parent.mkdir(parents=True, exist_ok=True)
5. Build the entire stage deliverable (<= 150 lines) as a list named chunks where each item is a multiline string representing a contiguous block of code without leading or trailing blank lines.
6. final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
7. target_path.write_text(final_text, encoding='utf-8')
8. print('FILE_WRITTEN:README.md')
9. print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/mnt/data"))) for p in target_path.parent.glob('*') if p.is_file())))

Constraints:
- Ensure the new file fully satisfies the stage goal with no placeholders or TODO markers.
- Keep the newly written code within the stated line/character budget.
- Keep console output short (only FILE_WRITTEN / DIR_STATE plus essential status).
- Do not touch files outside README.md.
- After writing the file, provide a one-sentence summary. Do not list the file contents in the final message.
