You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Add scripts/run_pipeline.py as the single entrypoint, a minimal requirements.txt (or pyproject.toml), and one toy experiment module that runs in <1 minute and writes fixed outputs (JSON + plot) into ./outputs/; verify by running end-to-end locally.
Project: generated_library_1766550131007 (python library)

Target file details:
- Path: README.md
- Purpose: Documentation describing how to set up the environment, run scripts/run_pipeline.py, and find the generated artifacts in outputs/.
- Category: documentation

Other planned files (for context only):
- scripts/run_pipeline.py: Single CLI entrypoint that runs a deterministic toy experiment end-to-end in <1 minute and writes fixed JSON metrics and a plot into outputs/.
- src/toy_pipeline/__init__.py: Package initializer exposing the public API for the toy pipeline experiment and ensuring importable module structure.
- src/toy_pipeline/experiment.py: Toy experiment implementation that generates deterministic synthetic data, trains a tiny model, computes fixed metrics, and saves JSON + PNG artifacts to outputs/.
- src/toy_pipeline/plotting.py: Plotting utilities that create a reproducible matplotlib figure from experiment results and save it as a PNG.

Reference insights:
- [INTROSPECTION] 2025-12-24T01-29-38-707Z_scripts_run_pipeline_py_stage1_attempt1_prompt.txt from code-creation agent agent_1766539771836_cun
- [AGENT: agent_1766541933970_kpux1wi] {"agentId":"agent_1766541933970_kpux1wi","goalId":"goal_18","containerId":"cntr_694b4a714b208190ab6f0ee
- [AGENT: agent_1766538747481_xj9s0e3] Cycle 7 consistency review (divergence 0.98):
Summary judgment
All three branches are complementary per
- [AGENT: agent_1766543291642_15ryvxl] {"agentId":"agent_1766543291642_15ryvxl","goalId":"goal_43","containerId":"cntr_694b4fc317a48190a1321c4
- [CONSOLIDATED] Unify the three experiments into a single, fully reproducible Python 3.11+ workflow—centered on a Jupyter notebook with compa

Key requirements:
- ci cd

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Documentation describing how to set up the environment, run scripts/run_pipeline.py, and find the generated artifacts in outputs/.
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
