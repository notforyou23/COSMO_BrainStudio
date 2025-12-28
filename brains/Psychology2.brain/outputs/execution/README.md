# Atomic Claims (Stage 1)

This repo defines an *atomic-claim* schema, a 3-way evidence labeling rubric, and a small curated reference corpus with gold annotations intended for early “borderline-confidence” evaluation.
## What is an atomic claim?

An **atomic claim** is a minimal, self-contained proposition that:
- asserts exactly one verifiable relation (no “and/or” bundling),
- makes the **subject** explicit (who/what the claim is about),
- makes the **predicate** explicit (what is being asserted),
- states the **scope** (time, geography, population, modality, quantifiers),
- specifies **provenance requirements** (what evidence would count).

Atomic claims are designed for consistent labeling under cognitive load by reducing ambiguity and by surfacing required context and evidence needs.
## Schema (conceptual)

Each claim instance is represented as a structured object with the following fields:

- `id` (string): stable identifier.
- `text` (string): the natural-language claim (single proposition).
- `subject` (object):
  - `entity` (string): canonical subject name.
  - `type` (string): e.g., person/org/place/product/concept.
- `predicate` (object):
  - `relation` (string): canonical relation label (e.g., "increases", "is", "located_in").
  - `polarity` (string): `affirm` or `negate`.
  - `object` (string|object): what the relation targets.
- `scope` (object): constraints required to interpret the claim:
  - `time` (string|null): e.g., "2020", "as of 2024-01", "in the 19th century".
  - `location` (string|null): e.g., "US", "global".
  - `population` (string|null): e.g., "adults", "patients with X".
  - `quantifier` (string|null): e.g., "all", "most", "at least 10%".
  - `modality` (string|null): e.g., "can", "must", "likely".
- `provenance` (object): what evidence is required to evaluate:
  - `required` (list[string]): required evidence types (e.g., "primary_source", "official_statistic", "peer_reviewed").
  - `notes` (string): special requirements/edge conditions.
- `metadata` (object): optional annotator and curation info.

A machine-readable version of this schema is implemented in `src/atomic_claims/schema.py` (JSON serialization + validation).
## Labeling rubric: supported / contradicted / insufficient

Given a claim `C` and a set of retrieved references `R` (snippets, documents, citations), assign exactly one label:

### 1) SUPPORTED
Label **supported** iff the available references *clearly entail* the claim under the claim’s stated scope.
Rules:
- All key constraints in `scope` must be satisfied (time/place/population/quantifier/modality).
- Minor paraphrases are fine; meaning must match.
- If evidence supports a weaker/stronger statement than claimed, do **not** mark supported.

### 2) CONTRADICTED
Label **contradicted** iff the references *clearly entail the negation* of the claim under the same scope.
Rules:
- Contradiction must be direct (not merely “no mention”).
- If references dispute only a sub-scope (different year/place/population), prefer **insufficient** unless the claim is explicitly universal.
- If both strong support and strong contradiction exist for the same scope, flag as **insufficient** unless one is clearly authoritative per provenance requirements.

### 3) INSUFFICIENT
Label **insufficient** when evidence is missing, ambiguous, out-of-scope, or too weak to decide.
Common cases:
- Evidence references a different scope (wrong time/place/population).
- Evidence supports only part of the claim (missing quantifier or modality).
- Evidence is non-authoritative relative to `provenance.required` (e.g., blog post when official stats are required).
- Evidence is suggestive/correlational but claim is causal (or vice versa).

Programmatic checks and edge-case guidance are defined in `src/atomic_claims/rubric.py`.
## Borderline-confidence dataset slice (gold)

Purpose: a small, curated set of *borderline* examples where naive heuristics fail (scope mismatch, quantifier drift, causality vs correlation, definition changes).

### Dataset format (JSONL)
Two primary JSONL files are expected:

1) `corpus.jsonl` (reference corpus)
Each line:
- `doc_id` (string)
- `title` (string)
- `source` (string; publisher or dataset name)
- `url` (string; optional)
- `published` (string; ISO date or year; optional)
- `text` (string; full text or excerpt)
- `license` (string; optional)

2) `annotations.jsonl` (gold labels)
Each line:
- `claim` (object): atomic claim per schema
- `evidence` (list[object]): pointers into the corpus:
  - `doc_id` (string)
  - `quote` (string): minimal supporting/contradicting span
  - `offsets` (object; optional): `{ "start": int, "end": int }`
- `label` (string): `supported` | `contradicted` | `insufficient`
- `rationale` (string): short justification focusing on scope + entailment
- `annotator` (string; optional)
- `version` (string; optional)

The gold slice should include at least:
- scope collisions (year/place/population),
- quantifier collisions (some vs most vs all),
- causal vs associational phrasing,
- definitional shifts (metric or category changes),
- provenance sensitivity (official vs informal).
## End-to-end: curation + validation workflow

The intended workflow is:

1) Create/extend the reference corpus:
- Add documents/snippets to `corpus.jsonl`.
- Keep each document internally coherent; prefer primary or authoritative sources.

2) Write atomic claims and gold annotations:
- Add claim objects and evidence pointers to `annotations.jsonl`.
- Ensure each claim is a single proposition; split conjunctions into multiple claims.

3) Validate:
- Run schema validation (JSON structure + required fields).
- Run rubric consistency checks (e.g., evidence present for supported/contradicted, scope keys present when needed).

4) Iterate:
- Add “borderline” items when label disagreements occur.
- Record rationale to make the decision boundary explicit.

Entry points are expected to be provided via console scripts in `pyproject.toml` once the package is installed (e.g., `atomic-claims validate ...`).
## Curation principles (quick checklist)

- **One claim, one decision**: if you need two citations for different sub-claims, split it.
- **Make scope explicit**: if time/place/population matters, state it in `scope`.
- **Prefer entailment**: label supported/contradicted only when the references *force* the conclusion.
- **Respect provenance requirements**: if the claim requires official stats, informal commentary is insufficient.
- **Store minimal quotes**: keep evidence spans short but decisive.

This README describes Stage 1 documentation; code and dataset files referenced above are created in subsequent stages.
