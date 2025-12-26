## Required QA Gate for Pilot Workflow (Claim Analysis Completion Criteria)

### Mission requirement (new hard gate)
In the pilot workflow, **no claim analysis is considered “complete” unless BOTH of the following are present under `/outputs/qa/` and they pass**:

1. **Schema validation report** (must show a passing result)
2. **`QA_REPORT.*` artifact(s)** (must be present and must show a passing result)

If either item is missing or failing, the claim analysis remains incomplete.

---

## Grounding in existing COSMO QA configuration (what we already know exists)

COSMO already has an explicit QA gating mechanism configured in `qa_gates.yaml` (from code-creation agent `agent_1766618407426_jbwdhcj`) with:

- `version: 1`
- `qa.fail_fast: true` (failure stops the process early)
- A defined artifact gate for `claim_card` including:
  - `template_path: outputs/templates/CLAIM_CARD.yaml`
  - `workflow_path: outputs/workflows/CLAIM_VERIFICATION_WORKFLOW.md`
  - `schema_path: config/claim_card.schema.yaml`
  - `artifact_globs` that define acceptable locations/formats for the Claim Card:
    - `outputs/**/CLAIM_CARD.yaml`
    - `outputs/**/CLAIM_CARD.yml`
    - `outputs/**/CLAIM_CARD.md`
  - `required_inputs: [v]`

This proves the system already treats QA as a **configurable, explicit gate** with:
- a schema (`config/claim_card.schema.yaml`) and
- known output artifact patterns (`outputs/**/CLAIM_CARD.*`),
and it is already set to **fail fast**.

The mission now adds an additional *completion criterion* specific to the pilot workflow: the QA artifacts must be located in `/outputs/qa/` and must pass.

---

## Definition of “complete” (updated acceptance criteria)

A pilot claim analysis is only complete when all of the following conditions are met:

### A) Claim Card exists (existing artifact expectations)
- A Claim Card artifact exists matching one of these patterns:
  - `outputs/**/CLAIM_CARD.yaml`
  - `outputs/**/CLAIM_CARD.yml`
  - `outputs/**/CLAIM_CARD.md`

### B) Schema validation passes and is documented (new required QA gate component)
- A **schema validation report** exists under:
  - `/outputs/qa/`
- The report must indicate a **passing** validation against the schema already identified in the QA config:
  - `config/claim_card.schema.yaml`

### C) QA report exists and passes (new required QA gate component)
- One or more QA report artifacts exist under:
  - `/outputs/qa/`
- The QA report filename(s) must match:
  - `QA_REPORT.*` (explicit wildcard requirement)
- The QA report(s) must indicate **pass**.

### D) Fail-fast behavior applies (already configured)
Because `qa.fail_fast: true` is already part of the QA system configuration, the intended behavior is consistent with the mission:
- if schema validation fails, stop;
- if `QA_REPORT.*` is missing or failing, stop;
- do not mark analysis complete.

---

## Required artifact location and naming (enforced by this mission)

### Required directory
All QA completion artifacts for the pilot workflow must be placed under:

- `/outputs/qa/`

### Required QA artifacts (must exist in that directory)
- **Schema validation report** (file present under `/outputs/qa/`)
- **`QA_REPORT.*`** (at least one file matching that glob under `/outputs/qa/`)

The mission’s language is explicit: completion requires that these artifacts are **present** and **pass** in `/outputs/qa/`.

---

## How this integrates with the existing workflow artifacts

The existing QA configuration already references a workflow document:

- `outputs/workflows/CLAIM_VERIFICATION_WORKFLOW.md`

To satisfy the mission, the pilot workflow described in that workflow document must include a required QA gate step at the end (or at the point where “complete” would otherwise be assigned), stating:

- Do not mark “complete” until:
  - schema validation report exists in `/outputs/qa/` and passes, and
  - `QA_REPORT.*` exists in `/outputs/qa/` and passes.

This also aligns with COSMO’s consolidated process principle that reliable research is produced by a repeatable process that **validates against explicit acceptance/QA criteria with transparent documentation** (summaries, sources, citations). The mission’s requirement is exactly such an explicit acceptance criterion with mandatory documentation artifacts.

---

## Operational rule for pilot runs (what must happen every time)

For each pilot claim analysis run:

1. Produce the Claim Card artifact (per existing globs and schema path).
2. Run schema validation against `config/claim_card.schema.yaml`.
3. Write the **schema validation report** into `/outputs/qa/`.
4. Produce a QA report file named `QA_REPORT.*` into `/outputs/qa/`.
5. Confirm both reports indicate **PASS**.
6. Only then can the claim analysis be labeled “complete”.

Because `qa.fail_fast: true`, any failure at steps 2–5 should halt the completion path.

---

## Conclusion

COSMO already has a structured QA gate system (`qa_gates.yaml`, `version: 1`) with fail-fast behavior and an explicit Claim Card schema (`config/claim_card.schema.yaml`). The mission adds a **hard completion gate** for the pilot workflow: **a claim analysis is not complete unless `/outputs/qa/` contains both (1) a passing schema validation report and (2) passing `QA_REPORT.*` artifact(s)**. This requirement is concrete (specific directory + specific artifact naming) and matches COSMO’s stated emphasis on repeatable validation against explicit QA criteria with transparent documentation.