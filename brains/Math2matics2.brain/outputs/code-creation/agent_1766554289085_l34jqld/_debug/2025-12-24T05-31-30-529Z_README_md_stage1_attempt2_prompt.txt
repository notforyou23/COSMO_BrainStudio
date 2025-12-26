You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Add a README/roadmap link to the exact command (python scripts/run_pipeline.py), ensure dependencies are declared, and add a CI job that runs it on a clean checkout and uploads ./outputs as artifacts.
Project: generated_script_1766554289298 (python script)

Target file details:
- Path: README.md
- Purpose: Project overview with a direct roadmap link and the exact run command `python scripts/run_pipeline.py` plus brief setup instructions.
- Category: documentation

Other planned files (for context only):
- requirements.txt: Pinned or minimally specified Python dependencies required to run `python scripts/run_pipeline.py` on a clean checkout.
- .github/workflows/ci.yml: GitHub Actions CI workflow that installs dependencies, runs `python scripts/run_pipeline.py` on a clean checkout, and uploads `outputs/` as build artifacts.

Reference insights:
- [INTROSPECTION] roadmap_v1.md from code-creation agent agent_1766551798569_1jkxc0c: # Project Roadmap (v1)

This roadmap tracks delivery of 
- [AGENT: agent_1766541933970_kpux1wi] {"agentId":"agent_1766541933970_kpux1wi","goalId":"goal_18","containerId":"cntr_694b4a714b208190ab6f0ee
- [AGENT INSIGHT: agent_1766550864729_p9ds97q] Invest in infrastructure lemmas: compactness/tightness, decomposition (structured+pseudorandom)
- [AGENT: agent_1766550864729_p9ds97q] Across the implications-and-consequences, systems-thinking, and psychological perspectives, the dominan
- [AGENT INSIGHT: agent_1766550864729_t9or71v] Assumptions are design variables and integration dependencies: they must be explicitly chosen, 

Key requirements:
- documentation
- ci cd

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Project overview with a direct roadmap link and the exact run command `python scripts/run_pipeline.py` plus brief setup instructions.
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
