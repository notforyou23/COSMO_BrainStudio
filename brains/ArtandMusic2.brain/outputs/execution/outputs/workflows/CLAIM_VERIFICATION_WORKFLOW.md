# Claim Verification Workflow (QA Gate Spec)

## Purpose
Define required inputs, validation rules, and the claim status lifecycle used by the QA gate for any CLAIM_CARD artifact.

## Required Inputs (MUST be captured verbatim)
1. **Verbatim claim**: the exact sentence(s) being asserted (no paraphrase).
2. **Source / context**: where the claim appears (doc title, section, paragraph/quote, link or file path).
3. **Provenance anchor**: an immutable pointer that lets a reviewer re-locate the evidence (e.g., URL + accessed timestamp, commit hash + path, dataset id + row key, or excerpt hash).

## Claim Card Format Expectations
A claim MUST be represented as a CLAIM_CARD (YAML file or Markdown with YAML frontmatter) containing at minimum:
- `claim.id` (stable identifier)
- `claim.text` (verbatim claim)
- `source.type` + `source.ref` + `source.context`
- `provenance.anchor.type` + `provenance.anchor.value` (+ `provenance.anchor.created_at` when applicable)
- `status.state` (one of the lifecycle states below)
- `status.history[]` entries for any state change (timestamp, actor, from, to, reason)

## Validation Rules (QA Gate MUST enforce)
### R1: Non-empty / exactness
- `claim.text` MUST be non-empty and MUST match the claimed statement exactly as it appears in the source.
- `source.context` MUST include sufficient surrounding text to confirm exact match (e.g., quoted sentence + neighboring clause, or paragraph id).

### R2: Source resolvability
- `source.ref` MUST be resolvable by a reviewer (URL reachable, file path exists in repo, or document id accessible).
- If the source is dynamic (web page, living doc), `provenance.anchor` MUST include a stabilizer (archive URL, snapshot id, commit hash, or captured excerpt hash).

### R3: Provenance anchor integrity
- `provenance.anchor.type` MUST be one of: `url`, `archive_url`, `commit`, `file_hash`, `dataset_key`, `excerpt_hash`.
- `provenance.anchor.value` MUST be present and syntactically valid for the chosen type.
- If `excerpt_hash` is used, the excerpt text used to compute it MUST be stored in the card (or as an inline block) so the hash can be recomputed.

### R4: Evidence sufficiency (for verification states)
- To enter `verified_true` or `verified_false`, the card MUST include at least one evidence item that:
  - directly supports or refutes the verbatim claim,
  - is linked to the provenance anchor, and
  - is specific enough to reproduce the check.

### R5: Ambiguity and scope control
- Claims with undefined terms, missing units, unclear population/timeframe, or mixed multiple assertions MUST be split or marked `needs_revision`.
- Any numeric/statistical claim MUST include units, scope, and timeframe in either `claim.text` (preferred) or explicitly in `source.context`.

### R6: Status history and monotonicity
- Every state change MUST append a `status.history` record.
- The current `status.state` MUST equal the latest history entry `to`.
- Transitions MUST follow the lifecycle rules below (no skipping from `draft` directly to `verified_*`).

## Step-by-Step Verification Procedure
1. **Capture**: Create/locate CLAIM_CARD; populate the three required inputs verbatim.
2. **Normalize**: Ensure the claim is atomic (single assertion). If not, split or set `needs_revision`.
3. **Resolve source**: Open `source.ref`; confirm `source.context` contains the claim verbatim.
4. **Anchor provenance**: Record a stable anchor; if source is mutable, create a snapshot/anchor that will remain valid.
5. **Collect evidence**: Add evidence excerpts/records tied to the anchor(s); record where each comes from.
6. **Evaluate**: Decide whether evidence supports/refutes/insufficient; document reasoning concisely.
7. **Set status**: Update `status.state` per lifecycle; append history record with reason and actor.
8. **QA gate check**: Run schema + workflow validations (R1–R6). Block merge/release if failing.

## Claim Status Lifecycle (used by QA gate)
### States (enum)
- `draft`: captured but not yet checked.
- `needs_revision`: not verifiable as written (ambiguity, mixed claims, missing scope/units, or missing anchors).
- `in_review`: verification in progress; evidence being gathered.
- `verified_true`: evidence supports the claim as written.
- `verified_false`: evidence contradicts the claim as written.
- `insufficient_evidence`: could not verify either way with available sources.
- `deprecated`: superseded/withdrawn; kept for traceability (must include reason).

### Allowed Transitions
- `draft` -> `in_review` | `needs_revision`
- `needs_revision` -> `draft` (after rewrite) | `deprecated`
- `in_review` -> `verified_true` | `verified_false` | `insufficient_evidence` | `needs_revision`
- `verified_true` -> `deprecated`
- `verified_false` -> `deprecated`
- `insufficient_evidence` -> `in_review` | `deprecated`
- `deprecated` -> (no transitions)

### QA Gate Decisions
- PASS if: card validates R1–R6 AND `status.state` in {`verified_true`,`verified_false`,`insufficient_evidence`,`deprecated`} (with required evidence/history).
- WARN if: card validates R1–R3 but `status.state` in {`draft`,`in_review`,`needs_revision`}.
- FAIL if: missing any required inputs, invalid provenance anchor, invalid transition/history, or unverifiable source.

## Reviewer Checklist (minimum)
- Claim text matches source exactly.
- Source is reachable and context shows the claim.
- Provenance anchor is stable and sufficient to reproduce.
- Evidence is attached for verified outcomes.
- Status is correct and history records the decision.
