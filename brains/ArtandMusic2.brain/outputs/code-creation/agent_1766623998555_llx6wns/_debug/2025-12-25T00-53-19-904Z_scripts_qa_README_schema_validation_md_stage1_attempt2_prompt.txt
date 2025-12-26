You are inside the OpenAI code interpreter environment with filesystem access to /mnt/data.

Mission summary: Run METADATA_SCHEMA.json validation on the pilot case study artifacts; emit /outputs/qa/schema_validation.json and a short markdown summary; add failure categories (missing required fields, invalid enums, citation formatting) to the pilot failure-modes log.
Project: generated_script_1766623998718 (json script)

Target file details:
- Path: scripts/qa/README_schema_validation.md
- Purpose: Documentation describing how to run the schema validation script, what inputs it expects, and the structure of the emitted JSON and markdown outputs including failure category definitions.
- Category: documentation

Other planned files (for context only):
- scripts/qa/run_schema_validation.py: CLI script that loads METADATA_SCHEMA.json, validates pilot case study artifact metadata files, emits /outputs/qa/schema_validation.json plus a short markdown summary, and appends categorized failure modes to the pilot failure-modes log.
- scripts/qa/_schema_validation_utils.py: Utility module providing JSON Schema validation helpers, enum checking, citation-format linting, and standardized error categorization for missing required fields, invalid enums, and citation formatting issues.

Reference insights:
- [AGENT: agent_1766620162691_lzfjfgq] Document Created: Generated report

I can’t actually implement or run schema validation across `/output
- [INTROSPECTION] 2025-12-25T00-21-55-842Z_scripts_qa_run_sh_stage1_attempt1_prompt.txt from code-creation agent agent_1766622114110_412seks: 
- [AGENT: agent_1766620015212_l8br3dc] Document Created: Generated report

# Generated report

*Auto-compiled from COSMO memory (GPT-5.2 unava
- [AGENT INSIGHT: agent_1766614627655_4lrkb6s] Implication 1: Measurement design becomes a hidden equity lever (and risk). If “genius” persist
- [CONSOLIDATED] Establishing clear, machine-validated structure (schemas) and lightweight automation (scaffolding, indexing, path canonicaliz

Stage details:
- Stage: Stage 1
- Mode: create
- Goal: Documentation describing how to run the schema validation script, what inputs it expects, and the structure of the emitted JSON and markdown outputs including failure category definitions.
- Line budget for this stage: <= 150 new/changed lines.

Implementation tasks (execute using Python in this environment):
1. from pathlib import Path
2. import json
3. target_path = Path('/mnt/data').joinpath('scripts/qa/README_schema_validation.md')
4. target_path.parent.mkdir(parents=True, exist_ok=True)
5. Build the entire stage deliverable (<= 150 lines) as a list named chunks where each item is a multiline string representing a contiguous block of code without leading or trailing blank lines.
6. final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
7. target_path.write_text(final_text, encoding='utf-8')
8. print('FILE_WRITTEN:scripts/qa/README_schema_validation.md')
9. print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/mnt/data"))) for p in target_path.parent.glob('*') if p.is_file())))

Constraints:
- Ensure the new file fully satisfies the stage goal with no placeholders or TODO markers.
- Keep the newly written code within the stated line/character budget.
- Keep console output short (only FILE_WRITTEN / DIR_STATE plus essential status).
- Do not touch files outside scripts/qa/README_schema_validation.md.
- After writing the file, provide a one-sentence summary. Do not list the file contents in the final message.
