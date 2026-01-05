You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Add a minimal CI workflow that runs the canonical runner on a tiny fixture dataset, then validates presence + non-emptiness + schema of runtime/_build/{reports,tables,figures,logs} and uploads the entire runtime/_build/ directory as a downloadable artifact on every run.
Project: generated_script_1766738413937 (python script)

Target file details:
- Path: fixtures/tiny/README.md
- Purpose: Documentation describing the tiny fixture dataset and how CI uses it to exercise the canonical runner deterministically.
- Category: documentation

Other planned files (for context only):
- .github/workflows/ci.yml: GitHub Actions CI workflow that runs the canonical runner on a tiny fixture dataset, validates runtime/_build/{reports,tables,figures,logs} for presence/non-emptiness/schema, and uploads runtime/_build as an artifact on every run.
- scripts/ci_validate_build.py: Standalone Python validator invoked by CI that asserts required runtime/_build subdirectories exist, are non-empty, and that key outputs conform to lightweight file/schema checks (e.g., tables have parseable headers, logs are decodable, figures are valid images).
- fixtures/tiny/input.csv: Small deterministic CSV fixture input used by the CI run to generate minimal but complete pipeline outputs.
- fixtures/tiny/config.yml: Minimal runner configuration pointing the canonical runner at the tiny fixture dataset and directing outputs to runtime/_build for CI validation and artifact upload.

Reference insights:
- [INTROSPECTION] 2025-12-26T07-21-10-352Z__github_workflows_ci_yml_stage1_attempt1_prompt.txt from code-creation agent agent_1766733668659_my
- [AGENT: agent_1766731203226_m37bifk] {"agentId":"agent_1766731203226_m37bifk","timestamp":"2025-12-26T06:49:35.087Z","files":[{"filename":".
- [FORK:fork_35] Under cognitive load people rely more on simple heuristics and defaults, so designing choice architectures that surface helpf
- [AGENT INSIGHT: agent_1766733982156_n6bb5fc] Implication 3: UX and workflow become first-class safety components with measurable cost models
- [INTROSPECTION] record_versions.py from code-creation agent agent_1766731203226_m37bifk: """record_versions.py

Utility to capture Python/OS

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Documentation describing the tiny fixture dataset and how CI uses it to exercise the canonical runner deterministically.
- Line budget for this stage: <= 150 new/changed lines.

Implementation tasks (execute using Python in this environment):
1. from pathlib import Path
2. import json
3. target_path = Path('/mnt/data').joinpath('fixtures/tiny/README.md')
4. target_path.parent.mkdir(parents=True, exist_ok=True)
5. Build the entire stage deliverable (<= 150 lines) as a list named chunks where each item is a multiline string representing a contiguous block of code without leading or trailing blank lines.
6. final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
7. target_path.write_text(final_text, encoding='utf-8')
8. print('FILE_WRITTEN:fixtures/tiny/README.md')
9. print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/mnt/data"))) for p in target_path.parent.glob('*') if p.is_file())))

Constraints:
- Ensure the new file fully satisfies the stage goal with no placeholders or TODO markers.
- Keep the newly written code within the stated line/character budget.
- Keep console output short (only FILE_WRITTEN / DIR_STATE plus essential status).
- Do not touch files outside fixtures/tiny/README.md.
- After writing the file, provide a one-sentence summary. Do not list the file contents in the final message.
