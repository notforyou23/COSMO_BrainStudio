---
schema: claim_card/v1
card_id: claim_002
pilot_batch: pilot_3_claims
title: "Claim #2 — Ambiguous provenance/versioning (intentional)"
claim:
  verbatim: "AI systems trained on internet-scale data will inevitably reproduce copyrighted material verbatim."
  type: empirical_generalization
  domain: ai_policy
  scope_notes: "Intended to cover text-generating LLMs broadly; 'inevitably' is treated as a strong modal claim."
status: draft_for_pilot
metadata:
  created_at: "2025-12-24T00:00:00Z"
  updated_at: "2025-12-24T00:00:00Z"
  owners:
    - name: "Pilot Operator"
      role: "analyst"
  tags: ["pilot", "ambiguity-test", "provenance", "versioning"]
versioning:
  card_version: "1.0.0"
  version_label: "v1"
  intended_supersedes: "0.9"
  ambiguity_notes:
    - "card_version=1.0.0 but version_label=v1 and intended_supersedes=0.9 without a resolvable prior card record in this repo."
    - "Multiple candidate source records below disagree on publication date and identifier (DOI vs URL)."
provenance:
  source_of_claim:
    method: "secondary_summary"
    notes: "Claim is stated as a general assertion; below sources are candidates but not uniquely bound to this verbatim wording."
  source_documents:
    - title: "Copyright, Copying, and Large Language Models"
      authors: ["A. Example", "B. Example"]
      identifier:
        type: "doi"
        value: "10.0000/example.doi.1234"
      published_date: "2023-05-01"
      retrieved_at: "2025-12-01T12:00:00Z"
      url: "https://doi.org/10.0000/example.doi.1234"
      relevance_notes: "Discusses memorization and regurgitation risk; may motivate the claim but does not necessarily assert inevitability."
    - title: "Copyright, Copying, and Large Language Models"
      authors: ["A. Example", "B. Example"]
      identifier:
        type: "url"
        value: "https://papers.example.org/llm-copyright.pdf"
      published_date: "2023-04-15"
      retrieved_at: "2025-12-02T09:30:00Z"
      url: "https://papers.example.org/llm-copyright.pdf"
      relevance_notes: "Appears to be the same work as the DOI entry but has a different date and identifier; unclear which is canonical."
  training_data_provenance:
    notes: "Not specified; claim references 'internet-scale data' generally without naming datasets or model families."
corrections:
  correction_history:
    - correction_id: "corr_001"
      timestamp: "2025-12-24T00:00:00Z"
      applied_to_version: "v1"
      description: "Normalized wording from earlier draft; retained strong modal ('inevitably')."
      supersedes_correction_id: "corr_000"
      evidence: []
      notes: "corr_000 is not present in this card; this is intentional to test correction-history integrity checks."
evaluation_plan:
  questions:
    - "Does peer-reviewed evidence support the modal strength 'inevitably' rather than 'sometimes' or 'under certain conditions'?"
    - "Are there documented cases of verbatim reproduction attributable to training data vs prompt leakage or retrieval?"
  acceptance_criteria:
    - "At least two independent empirical studies demonstrating verbatim reproduction under varied prompts, with attribution to training memorization."
    - "A clear definition of 'internet-scale data' and model scope."
  risks:
    - "Overgeneralization across model architectures and dataset filtering practices."
    - "Ambiguous causal pathway (training vs fine-tuning vs retrieval augmentation)."
---
# Claim Card: claim_002

## Verbatim claim
AI systems trained on internet-scale data will inevitably reproduce copyrighted material verbatim.

## Why this card exists (pilot intent)
This sample is **intentionally** constructed to contain **version and provenance ambiguity** so the validator/workflow can detect and log:
- Version ambiguity (mixed version signals and unclear supersession)
- Provenance ambiguity (duplicate/competing source records with conflicting identifiers/dates)
- Correction history integrity issues (references to missing prior correction)

## Minimal context
The claim is often informally asserted in policy discussions about training on large web corpora. The key contested term is **"inevitably"**, which implies unavoidable verbatim reproduction regardless of mitigations (deduplication, filtering, watermarking, RLHF, etc.).

## Provenance ambiguity (what’s wrong on purpose)
- Two source document entries appear to refer to the *same* work but disagree on identifier (DOI vs URL) and published date.
- The card does not uniquely bind the verbatim claim to a specific quote or section in any listed source.

## Version ambiguity (what’s wrong on purpose)
- `card_version` is `1.0.0` but `version_label` is `v1`, and `intended_supersedes` references `0.9` without an accessible predecessor.
- Correction history references `corr_000`, which does not exist in this card.

## Notes for reviewers
Treat this card as a harness for validation and logging rather than a polished research artifact.
