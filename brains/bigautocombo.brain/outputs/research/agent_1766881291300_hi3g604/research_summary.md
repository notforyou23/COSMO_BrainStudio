# Research Summary

**Agent:** agent_1766881291300_hi3g604
**Mission:** QA found borderline confidence - research agent should verify claims
**Completed:** 2025-12-28T00:23:29.311Z

## Summary

Across 2023 QA research, confidence calibration work concentrated on (a) eliciting a confidence score from LLMs that correlates with correctness, and (b) using uncertainty to drive safer behaviors such as abstention, answer-set prediction, or filtering. A notable EMNLP 2023 finding (“Just Ask for Calibration”) reports that for RLHF-tuned chat models, token log-probabilities can be poorly calibrated on QA benchmarks, while eliciting an explicit probability/confidence from the model can yield better calibration on datasets including TriviaQA, SciQ, and TruthfulQA. In parallel, work on conformal methods for language modeling showed distribution-free uncertainty quantification can be adapted to generative QA to output sets of candidate responses with statistical coverage guarantees.

For production handling of borderline-confidence QA, the research aligns with a triage pipeline: calibrated confidence (often augmented by additional signals like retrieval support or consistency checks) is mapped into decision bands—auto-answer, human-review, and abstain/deferral. Because global calibration metrics can mask miscalibration near the operating threshold, thresholding should be supported by local/threshold-region calibration diagnostics (e.g., zoomed reliability diagrams, region ECE, or smoothed estimators like SmoothECE). A pragmatic refinement is a cheap second-pass evidence step (e.g., retrieval-augmented verification or targeted follow-up prompts) to “recover” some borderline cases before routing to humans, then using human outcomes as feedback to tighten calibration and reduce future review load.

## Key Findings

1. EMNLP 2023 (“Just Ask for Calibration”) reports that for RLHF-tuned chat LLMs, token log-probabilities may be poorly calibrated for QA, while elicited self-reported confidence/probability can be better calibrated on QA benchmarks (e.g., TriviaQA, SciQ, TruthfulQA), reducing calibration error (per the cited EMNLP 2023 paper).

2. A 2023 multilingual calibration study reports QA confidence calibration can degrade substantially outside English, and that post-hoc calibration or light regularized tuning using a small set of translated samples can improve calibration (per the cited arXiv study).

3. Conformal prediction adapted to LMs (“Conformal Language Modeling”, 2023) can provide distribution-free uncertainty quantification for generative tasks including open-domain QA by returning a set of candidate responses with statistical coverage guarantees that a satisfactory answer is included with high probability (per the cited arXiv paper).

4. Borderline-confidence handling in deployed QA systems is best framed as selective prediction/deferral: route low-confidence to abstention or humans, answer high-confidence automatically, and send the middle band to structured human review—this only works well if the confidence score is calibrated or explicitly calibrated/elicited before thresholds are applied (supported by the EMNLP 2023 calibration finding).

5. Threshold selection should not rely solely on global ECE/reliability summaries because calibration can be acceptable overall yet wrong near the decision cutoff; use reliability diagrams and local/threshold-region calibration checks, and consider smoothed estimators (e.g., SmoothECE) to reduce binning fragility (supported by Guo et al. 2017 and later calibration-evaluation work).

## Research Queries

1. QA model confidence calibration methods 2023
2. Handling borderline-confidence QA predictions human review workflow
3. Threshold selection reliability diagrams expected calibration error

## Sources

Total sources consulted: 56

See `bibliography.bib` for citation-ready BibTeX entries.
