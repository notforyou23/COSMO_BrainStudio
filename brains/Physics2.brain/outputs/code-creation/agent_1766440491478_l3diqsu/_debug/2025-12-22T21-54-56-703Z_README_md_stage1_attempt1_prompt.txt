You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Define the exact acceptance criteria (tolerances, file paths, command invocation), then patch only the minimal set of failures until (a) `pytest` passes and (b) the benchmark diff is within tolerance; record the final command sequence in a README section called “Golden path”.
Project: generated_script_1766440494796 (python script)

Target file details:
- Path: README.md
- Purpose: Project documentation defining exact acceptance criteria (tolerances, file paths, command invocation) and a “Golden path” section capturing the final command sequence to run tests and benchmarks.
- Category: documentation

Other planned files (for context only):
- src/benchmark_contract.py: Defines the standardized benchmark contract schema/metadata, reference algorithm interface, tolerance rules, and helpers to validate benchmark artifacts for v0.1 tasks.
- src/run_benchmark.py: CLI entrypoint to execute the reference algorithm, write benchmark outputs to the contracted file paths, and compute diffs against golden references within tolerance.
- src/diff.py: Implements numeric and structured diff utilities (absolute/relative tolerances, summary reporting) used to decide benchmark acceptance.
- benchmarks/contracts/v0_1.json: Canonical benchmark contract file specifying required metadata, I/O paths, reference algorithm selection, and tolerance thresholds for v0.1 tasks.

Reference insights:
- [CONSOLIDATED] Establish a standardized, tool-supported “benchmark contract” for each v0.1 task—defining required metadata, a reference algo
- [AGENT: agent_1766432552135_37yovma] {"agentId":"agent_1766432552135_37yovma","goalId":"goal_guided_code_creation_1766429554815","containerI
- [AGENT: agent_1766430411939_w8zvs5v] {"agentId":"agent_1766430411939_w8zvs5v","goalId":"goal_guided_code_creation_1766429554815","containerI
- [AGENT: agent_1766438283976_puyw9gc] {"agentId":"agent_1766438283976_puyw9gc","goalId":"routing_code_1766438283975_nh5nje8","containerId":"c
- [AGENT: agent_1766438409884_82yeh6g] {"agentId":"agent_1766438409884_82yeh6g","goalId":"goal_7","containerId":"cntr_6949b60f62d4819083834ab5

Key requirements:
- documentation

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Project documentation defining exact acceptance criteria (tolerances, file paths, command invocation) and a “Golden path” section capturing the final command sequence to run tests and benchmarks.
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
