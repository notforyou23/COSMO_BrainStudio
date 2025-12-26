# Verifier Benchmark Harness (Stage 1)

This project benchmarks **generate → verify → revise** pipelines on a grounded QA dataset with **cited evidence**, comparing verifier patterns and their failure modes.

## Verifier patterns implemented (select 2–3)

All patterns share a unified interface: given (question, evidence), produce an answer plus verifier signals (pass/fail, score, rationale, attributions).

1) **Best-of-N + Verifier rerank**
- Generate N candidate answers (same question/evidence, different seed).
- Verifier scores each candidate for faithfulness/attribution and selects the best.
- Useful to separate *generation variance* from *verification capacity*.

2) **Entailment/Attribution check over retrieved evidence**
- Decompose answer into atomic claims; for each claim, check whether it is entailed/supported by provided evidence snippets.
- Outputs: supported/unsupported/uncertain labels, citation coverage, and an overall pass/fail gate.
- Can trigger revision: regenerate constrained to cite supporting snippets.

3) **Self-consistency + critique gating**
- Sample multiple solutions, ask a critique/verifier to identify contradictions, missing citations, and unsupported claims.
- Gate final answer on critique score; optionally revise with targeted fixes (add citations/remove unsupported content).

## Dataset schema (grounded QA with citations)

Input is a JSONL file with one record per question. Minimal fields:

- `id` (string): stable unique example id
- `question` (string)
- `gold_answer` (string): reference answer (may be short or long-form)
- `evidence` (array of objects):
  - `evidence_id` (string): stable id for snippet/document chunk
  - `title` (string, optional)
  - `text` (string): snippet content used for grounding
  - `source` (string, optional): URL/path/collection name
- `gold_citations` (array of objects, optional):
  - `evidence_id` (string)
  - `span` (string, optional): quote/substring aligned to gold

Model outputs should include citations pointing to `evidence_id` values, e.g. `[cite:evidence_id]` or a structured `citations` list.

## Benchmark tasks & metrics

### Primary task: error detection by verifier
We treat the verifier as a classifier over generated answers:
- Positive = “answer has a grounding error” (unsupported claim, wrong citation, or contradiction with evidence)
- Negative = “answer is grounded/supported”

Metrics:
- **Precision/Recall/F1** for error detection (verifier pass/fail vs. gold error labels)
- **AUROC / AUPRC** when a continuous verifier score is available
- **Coverage vs. accuracy** (selective prediction): fraction answered after gating vs. correctness/groundedness

### Attribution / grounding metrics
- **Citation coverage**: % of answer claims with at least one evidence citation
- **Supported-claim rate**: supported claims / total claims
- **Citation precision**: citations that truly support the claim / total citations (requires claim↔evidence checks)

### Calibration
For any probabilistic verifier score `p(error)` or `p(grounded)`:
- Reliability diagrams / calibration curves
- **ECE** (Expected Calibration Error) and **Brier score**
Interpretation: a well-calibrated verifier enables threshold selection with predictable tradeoffs.

## Running the benchmark

Entry point:
- `python scripts/verifier_benchmark.py --data <path_to_jsonl> --pattern <best_of_n|entailment|self_consistency> [args]`

Typical options (see script help):
- `--n 5` (best-of-N / self-consistency sample count)
- `--seed 0` (deterministic sampling)
- `--max_examples 200` (quick runs)
- `--out_dir runs/<run_name>` (artifacts)

Backends:
- Use an OpenAI-compatible HTTP backend or a local stub backend for dry runs.
- Both generation and verification calls should support retries/timeouts and deterministic seeding where applicable.

## Produced artifacts (standardized)

Each run writes a directory containing:
- `results.jsonl`: per-example records with fields like:
  - ids, question, selected_answer, candidates (optional), verifier_score, verifier_pass, revision_used, citations, claim_checks
- `summary.json`: aggregate metrics (precision/recall, AUROC/AUPRC, ECE/Brier, coverage curves)
- `plots/`:
  - `calibration.png` (reliability diagram)
  - `pr_curve.png`, `roc_curve.png`
  - `coverage_accuracy.png`

## How to interpret failure modes

Use `results.jsonl` slices to compare patterns:
- Best-of-N helps when *some* samples are grounded and the verifier can pick them; it fails when all candidates share the same hallucination.
- Entailment/attribution checks expose “looks plausible” errors: missing citations, wrong evidence, or partially supported composites; it can over-flag when evidence is paraphrastic or incomplete.
- Self-consistency + critique gating catches internal contradictions and missing support, but may be sensitive to critique prompt style and can under-detect subtle misattribution.

A good benchmark report includes:
- Metrics (detection, grounding, calibration) + plots
- Qualitative buckets: unsupported claim, wrong citation, overgeneralization beyond evidence, and evidence omission.
