# Claim Card Workflow (Template + Schema + 3-Claim Pilot)

## Purpose
This document defines the end-to-end workflow to (1) author Claim Cards in Markdown with embedded YAML front matter, (2) validate them against a JSON Schema, (3) run the 3-claim pilot, and (4) log/resolve failure modes, including missing metadata, version ambiguity, and correction history issues.

## Canonical Artifacts (paths are project-relative)
- Schema: `config/claim_card.schema.json`
- Human template (Markdown + YAML front matter): `outputs/CLAIM_CARD_TEMPLATE.md`
- Parser (MD+YAML -> normalized JSON): `src/claim_card/parse_md.py`
- Validator CLI (schema validate + failure logs): `src/claim_card/validate.py`
- Pilot outputs (recommended):
  - Claim cards: `outputs/pilot/claims/*.md`
  - Parsed JSON: `outputs/pilot/parsed/*.json`
  - Validation + failure logs (JSONL): `outputs/pilot/logs/validation_failures.jsonl`
  - Run summary: `outputs/pilot/logs/pilot_summary.json`

## Terms
- **Claim Card**: A single, testable claim packaged with required metadata (provenance, scope, versioning) and an explicit correction history.
- **Normalized JSON**: The machine-readable representation produced from YAML/JSON or parsed from Markdown front matter.
- **Failure mode**: A structured, actionable validation or workflow error that blocks acceptance or requires correction.

## Required Content (authoring checklist)
A Claim Card MUST include, at minimum:
- Verbatim claim text (exact wording; not paraphrased).
- Claim type (e.g., empirical, causal, definitional, normative) and domain/topic tags.
- Source/provenance: where the claim came from, including enough detail to locate the exact version (URL/DOI, title, authors, publisher, and accessed/retrieved timestamp).
- Evidence pointers: citations/quotes/snippets sufficient to connect claim -> source.
- Scope & assumptions: population, geography, timeframe, boundary conditions, definitions.
- Measurement & methods notes (when relevant): operationalization, key variables, ambiguity flags.
- Versioning: a stable `claim_id`, a `card_version` (semver or monotonic), and a `created_at` + `updated_at`.
- Correction history: an array of changes with timestamps, reason, and what changed.

## Authoring Workflow (single card)
1. **Create**: Copy `outputs/CLAIM_CARD_TEMPLATE.md` to `outputs/pilot/claims/<claim_id>.md`.
2. **Fill YAML front matter first**:
   - Ensure all required fields are present and specific.
   - If a field is unknown, do NOT omit it; record an explicit null/unknown value only if allowed by schema and add an ambiguity note.
3. **Write the human section**:
   - Include a short rationale, key excerpts, and any quantification (units, denominators).
4. **Add correction history from the start**:
   - Initial entry should record creation as a change event (who/when/why).
5. **Save**: Keep filenames stable; changes should be tracked via `card_version` and `corrections[]`.

## Validation Workflow
1. **Parse** (if Markdown):
   - Input: `outputs/pilot/claims/*.md`
   - Output: `outputs/pilot/parsed/<claim_id>.json` (normalized JSON)
2. **Validate** (schema + workflow checks):
   - Validate JSON against `config/claim_card.schema.json`.
   - Run additional workflow checks:
     - Missing metadata (required fields empty/omitted).
     - Version ambiguity (conflicting versions, missing source version, unclear retrieval date).
     - Correction history issues (missing, non-monotonic timestamps, unclear change descriptions).
3. **Log failures**:
   - Append one JSON object per failure to `outputs/pilot/logs/validation_failures.jsonl`.
   - Each log entry SHOULD include:
     - `timestamp`, `claim_id`, `card_version`
     - `failure_mode` (enum-like string)
     - `severity` (blocker|major|minor)
     - `field_path` (JSON pointer-like path when applicable)
     - `message` (human-readable)
     - `evidence` (optional: snippets, schema errors, parser notes)
4. **Gate**:
   - A card is **accepted** for pilot analysis only if it passes schema validation and has no blocker-level workflow failures.

## 3-Claim Pilot Procedure
Goal: Validate the workflow end-to-end using three diverse claims (e.g., one quantitative empirical claim, one causal claim, one definitional/normative claim).
1. Select 3 claims with distinct source types (e.g., journal article, report, web page).
2. Create three cards using the template; ensure each has:
   - Explicit scope, definitions, and provenance.
   - At least one evidence pointer tied to a stable source location (page/section/quote).
3. Parse + validate all three.
4. Review failure logs; for each failure:
   - Classify into one of the failure modes below.
   - Apply corrections in the card (increment `card_version` and append to `corrections[]`).
5. Re-validate until all three pass or until remaining failures are documented as non-blocking with rationale.
6. Produce a pilot summary (counts by failure mode, time-to-fix, common root causes).

## Failure Modes (minimum required taxonomy)
### 1) Missing Metadata
Trigger examples:
- Missing/empty required fields (claim text, claim_id, source locator, timestamps, scope).
- Evidence pointers absent or not traceable.
Logging guidance:
- Use `failure_mode="missing_metadata"` and point to `field_path`.

### 2) Version Ambiguity
Trigger examples:
- Source has no version identifier (undated web page, dynamic content) and no retrieval timestamp/snapshot.
- Conflicting version fields (e.g., YAML says one date, citation says another).
- Claim card updated but `card_version` not incremented or `updated_at` not changed.
Logging guidance:
- Use `failure_mode="version_ambiguity"`; include what would disambiguate (snapshot URL, DOI version, archive link).

### 3) Correction History Problems
Trigger examples:
- `corrections[]` missing entirely or empty after edits.
- Corrections without timestamps, author/agent, or reason.
- Non-monotonic correction timestamps; unclear diffs (what changed).
Logging guidance:
- Use `failure_mode="correction_history_issue"` and include the expected structure.

## Correction & Re-validation Rules
- Any change that alters meaning, scope, evidence, or provenance MUST:
  1. Increment `card_version`.
  2. Update `updated_at`.
  3. Append a correction record describing the change, the reason, and who made it.
- Minor typos MAY be recorded as a correction if they affect interpretation; default to recording.
- Never delete correction history; append-only, with clarifying follow-up entries if needed.

## Acceptance Criteria (for pilot completion)
- Three Claim Cards exist and validate cleanly against the schema.
- Failure logs exist and document at least one observed issue category (even if resolved).
- A brief summary exists describing common failure modes and how the workflow addressed them.

## Operational Notes
- Prefer stable identifiers: DOI, report ID, archived URLs, or repository commit hashes.
- When a source is a web page, capture: access time, page title, publisher, and an archival snapshot link when possible.
- Keep YAML front matter strictly machine-readable; avoid freeform prose in required scalar fields.
