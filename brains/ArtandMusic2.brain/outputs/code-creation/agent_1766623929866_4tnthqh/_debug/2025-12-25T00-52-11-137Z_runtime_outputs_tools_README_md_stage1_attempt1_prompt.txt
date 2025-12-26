You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Consolidate duplicate schemas/tools by selecting ONE authoritative case study schema (e.g., METADATA_SCHEMA.json) and ONE authoritative validator entrypoint. Deprecate or rename competing scripts/schemas and write runtime/outputs/tools/README.md describing the single blessed workflow (commands + expected outputs).
Project: generated_cli_tool_1766623930043 (json cli_tool)

Target file details:
- Path: runtime/outputs/tools/README.md
- Purpose: Describes the single blessed workflow (commands and expected outputs) for scaffolding and validating metadata using the authoritative schema and CLI.
- Category: documentation

Other planned files (for context only):
- schemas/METADATA_SCHEMA.json: Defines the single authoritative JSON Schema for case study metadata used across the repository.
- tools/metadata_cli.py: Implements the single blessed CLI entrypoint to scaffold, validate, and report on case study metadata against the authoritative schema.
- tools/__init__.py: Marks the tools directory as a Python package to support module execution and imports for the metadata CLI.
- tools/_schema_loader.py: Provides shared utilities to locate, load, and cache the authoritative METADATA_SCHEMA.json for runtime validation.

Reference insights:
- [CONSOLIDATED] Define a shared, machine-validated metadata standard (schemas + templates) and lightweight tooling (CLI/workflows) so case st
- [INTROSPECTION] 2025-12-25T00-21-55-842Z_qa_checks_py_stage1_attempt1_prompt.txt from code-creation agent agent_1766622114110_412seks: You a
- [AGENT INSIGHT: agent_1766614627655_4lrkb6s] Implication 1: Measurement design becomes a hidden equity lever (and risk). If “genius” persist
- [CONSOLIDATED] Establishing clear, machine-validated structure (schemas) and lightweight automation (scaffolding, indexing, path canonicaliz
- [INTROSPECTION] 2025-12-24T22-17-08-971Z_plan_attempt1_prompt.txt from code-creation agent agent_1766614627659_92j3x3t: You are planning a j

Key requirements:
- documentation

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Describes the single blessed workflow (commands and expected outputs) for scaffolding and validating metadata using the authoritative schema and CLI.
- Line budget for this stage: <= 150 new/changed lines.

Implementation tasks (execute using Python in this environment):
1. from pathlib import Path
2. import json
3. target_path = Path('/mnt/data').joinpath('runtime/outputs/tools/README.md')
4. target_path.parent.mkdir(parents=True, exist_ok=True)
5. Build the entire stage deliverable (<= 150 lines) as a list named chunks where each item is a multiline string representing a contiguous block of code without leading or trailing blank lines.
6. final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
7. target_path.write_text(final_text, encoding='utf-8')
8. print('FILE_WRITTEN:runtime/outputs/tools/README.md')
9. print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/mnt/data"))) for p in target_path.parent.glob('*') if p.is_file())))

Constraints:
- Ensure the new file fully satisfies the stage goal with no placeholders or TODO markers.
- Keep the newly written code within the stated line/character budget.
- Keep console output short (only FILE_WRITTEN / DIR_STATE plus essential status).
- Do not touch files outside runtime/outputs/tools/README.md.
- After writing the file, provide a one-sentence summary. Do not list the file contents in the final message.
