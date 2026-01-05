# Research Summary

**Agent:** agent_1766724332780_auwey5f
**Mission:** QA found borderline confidence - research agent should verify claims
**Completed:** 2025-12-26T04:46:54.936Z

## Summary

Borderline-confidence QA outputs should be handled as a selective prediction and risk-management problem, not as a prompt to the model to “be more sure.” The most reliable operational pattern is to require verifiable support for answers (grounded in retrieved evidence with attribution) and otherwise abstain or defer to a human or a slower verification pipeline. This aligns with NIST’s AI RMF / GenAI profile and TEVV framing: calibrate, test in-context, and measure failure modes continuously.

Practically, teams combine evidence-first verification (retrieve-then-verify, claim-by-claim checking, and strict citation requirements) with robustness checks (multi-sample consistency, verifier models, rule-based constraint checks). When integrating external “fact-checking APIs,” the current ecosystem primarily supports (a) retrieval of existing published fact-checks via ClaimReview feeds (notably Google Fact Check Tools API) and (b) workflow automation such as claim spotting/triage (e.g., ClaimBuster) and review operations tooling (e.g., Meedan’s Check). For statistical claims, best practice is to locate and cite primary datasets/tables (often via `site:.gov` and `site:.edu` query patterns and tools like data.census.gov’s citation workflow), capturing dataset/table identifiers, vintage, and methodology notes.

## Key Findings

1. Borderline-confidence QA is best treated as a selective prediction workflow: require strong, verifiable evidence for acceptance; otherwise abstain/defer (human review or a verification pipeline), with risk-tiered thresholds and calibrated confidence aligned to observed accuracy (NIST AI RMF / TEVV framing).

2. Evidence-first verification outperforms “self-confidence prompting”: implement retrieve-then-verify with strict source requirements (quote/attribution checks) and reject answers lacking strong retrieval support; optionally decompose answers into atomic claims and verify/correct each against retrieved sources.

3. Robustness in the borderline band can be improved with multi-sample consistency (independent generations compared for stability) and/or separate verifier models plus deterministic checks (constraints, units, entity resolution) to catch common failure modes.

4. Most practical ‘fact-checking APIs’ in 2024–2025 are not end-to-end truth engines: Google Fact Check Tools API mainly retrieves existing ClaimReview-tagged fact-checks; ClaimBuster supports claim spotting/triage and KB querying; Meedan’s Check supports collaborative verification workflows rather than automated adjudication.

5. For statistical claim verification, the reliable path is to find primary producing agencies/datasets using targeted search (e.g., `site:.gov`/`site:.edu` plus methodology/documentation terms), then cite dataset landing pages/tables with identifiers, release/vintage dates, geography, and methodology notes (e.g., data.census.gov’s built-in citation tools and Census citation guidance).

## Research Queries

1. best practices verify borderline-confidence QA model outputs
2. fact-checking APIs automated claim verification 2024-2025
3. search primary sources for statistical claims site:gov site:edu

## Sources

Total sources consulted: 53

See `bibliography.bib` for citation-ready BibTeX entries.
