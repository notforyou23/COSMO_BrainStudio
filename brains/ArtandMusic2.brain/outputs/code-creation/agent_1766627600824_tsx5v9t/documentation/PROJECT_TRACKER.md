# PROJECT_TRACKER: single source-of-truth progress ledger

Purpose: eliminate cross-cycle inconsistencies (e.g., “ACTUALLY PURSUED: 0”) by recording goal definitions and per-cycle activity in one deterministic ledger file that all agents/tools read and update.

## Files
- `outputs/PROJECT_TRACKER.json` (authoritative): tracker reads/writes this file only.
- `outputs/PROJECT_TRACKER.csv` (optional export): derived view for humans/spreadsheets.
- Script: `scripts/project_tracker.py` (CLI) maintains the ledger.

## Ledger schema (JSON)
Top-level object:
- `version` (int): schema version.
- `created_utc` (str): ISO-8601 timestamp.
- `active_cycle_id` (str|null): current cycle key.
- `goals` (object): map of `goal_id -> goal`.
- `cycles` (object): map of `cycle_id -> cycle`.
- `events` (array): append-only audit log.

Goal object (`goals[goal_id]`):
- `goal_id` (str): stable identifier (e.g., `G001` or slug).
- `title` (str)
- `status` (str): `active|paused|done|canceled`
- `created_utc` (str)
- `tags` (array[str], optional)
- `counts` (object): aggregate counters derived from events (single source-of-truth):
  - `pursued_cycles` (int): number of cycles where goal had any activity.
  - `units_done` (number): total completed units (if used).
  - `last_cycle_id` (str|null)

Cycle object (`cycles[cycle_id]`):
- `cycle_id` (str): e.g., `2025-12-24T22-26Z` or `C0007`
- `started_utc` (str)
- `ended_utc` (str|null)
- `notes` (str, optional)
- `active_goals` (array[str]): snapshot list at cycle start (for reporting).
- `activity` (object): map `goal_id -> activity`
  - Activity fields are flexible but should include:
    - `pursued` (bool): did any work happen this cycle?
    - `delta_units_done` (number, optional)
    - `comment` (str, optional)

Event object (`events[]`): minimal audit trail to rebuild counts deterministically:
- `ts_utc` (str)
- `type` (str): `init|goal_add|goal_update|cycle_start|cycle_end|activity_update|export`
- `cycle_id` (str|null)
- `goal_id` (str|null)
- `data` (object): payload (deltas/fields changed).

## Determinism rule (prevents “ACTUALLY PURSUED: 0”)
Never compute “pursued” from free-form text. Instead:
1) Each cycle has explicit `activity[goal_id].pursued = true/false`.
2) Aggregates in `goals[goal_id].counts` are computed from recorded per-cycle activity (or from events).
3) Reports pull from the ledger only (no secondary trackers).

## CLI commands (scripts/project_tracker.py)
All commands accept `--ledger outputs/PROJECT_TRACKER.json` (default) and operate idempotently.

### `init`
Creates a new ledger if missing.
- Example: `python scripts/project_tracker.py init`

### `goal add`
Adds a goal definition.
- Required: `--goal-id`, `--title`
- Optional: `--tags a,b,c`
- Example: `... goal add --goal-id G001 --title "Ship tracker"`

### `goal update`
Edits fields (e.g., status/title/tags).
- Example: `... goal update --goal-id G001 --status paused`

### `cycle start`
Starts a new cycle and snapshots current active goals.
- Optional: `--cycle-id` (else auto)
- Example: `... cycle start --cycle-id C0008`

### `cycle end`
Closes current cycle (sets `ended_utc`) without altering activity.
- Example: `... cycle end`

### `update` (activity update)
Records per-goal activity for the active cycle and updates derived counts.
- Required: `--goal-id`, `--pursued true|false`
- Optional: `--delta-units-done N`, `--comment "..."`.
- Example: `... update --goal-id G001 --pursued true --delta-units-done 1 --comment "Wrote docs"`

### `status`
Prints:
- active cycle id
- active goals (snapshot) + per-goal pursued flag for the cycle
- aggregate counts per goal (especially `pursued_cycles`)
- Example: `... status`

### `export`
Writes `outputs/PROJECT_TRACKER.csv` from the JSON ledger.
- One row per (cycle_id, goal_id) with: goal title, goal status, pursued, delta units, cycle dates, and computed totals.
- Example: `... export --csv outputs/PROJECT_TRACKER.csv`

## Intended workflow integration (minimum)
Per cycle:
1) `cycle start` at the beginning of the run (locks active goals list).
2) For each goal touched, call `update --pursued true` (and record deltas/comments).
3) Before generating any “cycle summary” artifact, run `status` and use its numbers for “ACTUALLY PURSUED”.
4) `cycle end` when done; optionally `export` for review.

Policy: the cycle summary must reference tracker outputs, not ad-hoc counts. This ensures “pursued” is explicitly recorded and totals are reproducible.
