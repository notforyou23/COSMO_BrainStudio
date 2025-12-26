You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Add automated tests/CI configuration (e.g., pytest + GitHub Actions) to validate schema conformance and ensure example benchmark computations reproduce expected outputs; place all files in outputs and ensure they run end-to-end.
Project: generated_configuration_1766429804913 (python configuration)

Target file details:
- Path: outputs/README.md
- Purpose: Documents how to run the end-to-end benchmark generation and test suite locally and how outputs are organized under outputs/.
- Category: documentation

Other planned files (for context only):
- pyproject.toml: Defines the Python package metadata, dependencies (pytest, jsonschema), and test tooling configuration for reproducible CI runs.
- .github/workflows/ci.yml: GitHub Actions workflow that sets up Python, installs dependencies, runs pytest, and fails on schema or benchmark mismatches.
- outputs/schemas/benchmark.schema.json: JSON Schema defining the required structure and types for benchmark input/output artifacts validated by tests and CI.
- outputs/examples/benchmark_case_001.json: Example benchmark input conforming to the schema used by tests to verify end-to-end computation reproducibility.

Reference insights:
- [AGENT: agent_1766429554962_lz72do0] Foundations work (2019–2025) increasingly prioritizes operational/testable frameworks (causal modeling,
- [AGENT: agent_1766429554962_lz72do0] Foundations work (2019–2025) increasingly prioritizes operational/testable frameworks (causal modeling,
- [AGENT: agent_1766429554962_lz72do0] Causal set theory’s technical progress centers on making dynamics and QFT-on-causal-sets more predictiv
- [AGENT: agent_1766429554962_lz72do0] Causal set theory’s technical progress centers on making dynamics and QFT-on-causal-sets more predictiv
- [AGENT: agent_1766429554962_lz72do0] Causal set theory’s technical progress centers on making dynamics and QFT-on-causal-sets more predictiv

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Documents how to run the end-to-end benchmark generation and test suite locally and how outputs are organized under outputs/.
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
