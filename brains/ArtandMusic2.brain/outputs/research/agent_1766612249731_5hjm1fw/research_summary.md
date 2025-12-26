# Research Summary

**Agent:** agent_1766612249731_5hjm1fw
**Mission:** QA found borderline confidence - research agent should verify claims
**Completed:** 2025-12-24T21:38:50.730Z

## Summary

Borderline-confidence QA outputs are best handled with a two-part strategy: (1) make uncertainty actionable via calibration and selective answering (answer/abstain/escalate), and (2) add an explicit verification stage instead of trusting single-pass generations. Research and practice converge on pipelines that generate candidate answers, verify them against evidence or consistency checks, then revise or abstain when reliability thresholds are not met.

Operationally, this is reinforced by risk-based human review: define clear triggers for escalation (low confidence, weak/missing citations, high-impact domains, novel queries) and use structured rubrics/scorecards with anchored examples to reduce reviewer variance. Tooling supports this workflow by measuring and improving calibration (ECE, reliability diagrams, post-hoc scaling) and, increasingly, by using conformal/risk-controlled methods to ensure error rates stay below targets or to abstain when guarantees can’t be met.

## Key Findings

1. Selective answering requires calibrated confidence: teams commonly calibrate model scores so the system can abstain or trigger extra checks when uncertainty is near a decision boundary, and apply risk-controlled filtering to keep expected error below a target (including conformal-style “sample-then-filter” approaches for open-ended QA).

2. Verification is increasingly implemented as “generate → verify → revise” rather than single-shot answering; common patterns include multi-sample self-consistency, best-of-N with a verifier, and retrieve-then-verify (checking entailment/support from retrieved evidence before finalizing).

3. Verifier quality matters: research notes that rationale-aware verification better distinguishes “lucky correct” answers from genuinely valid reasoning, motivating specialized verifiers beyond brittle prompt/regex checks.

4. Human review works best when selective and rubric-driven: define review triggers (low confidence, weak citations in RAG, high-risk/policy-sensitive queries) and use scorecards with anchored examples plus pass/fail gates; treat annotator disagreement as a signal for escalation or stronger evidence requirements.

5. Practical calibration tooling exists: netcal supports post-hoc calibration (e.g., temperature scaling) and reliability metrics; uncertainty-calibration adds bootstrap CIs for calibration error; MAPIE enables conformal prediction sets/intervals when QA can be cast as candidate classification/reranking, supporting risk-controlled deployment.

## Research Queries

1. methods to verify borderline-confidence answers in QA systems
2. best practices for human review of uncertain QA outputs
3. tools to calibrate and measure model confidence in QA

## Sources

Total sources consulted: 49

See `bibliography.bib` for citation-ready BibTeX entries.
