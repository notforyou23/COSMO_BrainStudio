# Research Summary

**Agent:** agent_1766880818574_gm00o82
**Mission:** QA found borderline confidence - research agent should verify claims
**Completed:** 2025-12-28T00:15:37.714Z

## Summary

The research converges on a practical verification toolkit for 2025 that separates (a) fast, claim-level news verification, (b) deeper verification of scientific findings, and (c) retrieval of authoritative primary data/official statistics. For news claims, the most reliable approach is to rely on major fact-checking operations with transparent methods (e.g., Reuters/AP and established nonprofit/newsroom fact-checkers) and to validate conclusions by reading the underlying evidence chain rather than trusting platform labels.

For scientific and statistical claims, the actionable throughline is “traceability”: verify whether a study was prospectively registered, whether outcomes/analyses match the registration and protocol, and whether data/code artifacts exist to reproduce results. For official statistics, use authoritative catalogs/portals (U.S. and international) that publish methodology, stable identifiers, and machine-readable access (APIs/downloads), and always record the release/vintage for reproducibility.

## Key Findings

1. News-claim verification workflow (actionable): search the exact claim on at least two independent, reputable fact-checkers (e.g., Reuters Fact Check, AP Fact Check, FactCheck.org, PolitiFact, Snopes; plus AFP Fact Check/Full Fact internationally). If no direct match is found, use the IFCN directory to identify vetted local fact-checkers, then evaluate the evidence trail (primary documents, data, context) rather than relying on a single “true/false” label.

2. Scientific-claim verification (clinical trials): check whether the trial was prospectively registered per ICMJE expectations, then compare the publication’s primary/secondary outcomes, timepoints, and analyses to the registry/protocol to detect outcome switching or selective reporting.

3. Scientific-claim auditability: use study-type reporting checklists (CONSORT for RCTs, STROBE for observational studies, PRISMA for systematic reviews) to confirm the paper includes the minimum details needed to independently assess methods and results (e.g., eligibility criteria, missing-data handling, effect sizes/uncertainty).

4. Bias/validity assessment: apply structured risk-of-bias tools aligned to design (RoB 2 for randomized trials; ROBINS-I for nonrandomized intervention studies) to translate “is this credible?” into explicit, reviewable judgments. Note: the research asserts a “ROBINS-I version 2 released during 2025,” which should be double-checked against Cochrane’s official pages/releases before treating as settled.

5. Primary data sourcing for statistics: for U.S. official datasets start with Data.gov for discovery, then use agency systems of record like data.census.gov and BLS’s Public Data API for official series. For international official statistics, common primary portals include World Bank Open Data, OECD Data, and IMF data platforms; record series IDs and release/vintage for reproducibility. Note: the claim about an IMF legacy portal retirement date in 2025 should be verified on IMF documentation.

## Research Queries

1. best fact-checking websites for verifying news claims 2025
2. how to verify scientific study claims primary data sources guide
3. databases for current statistics and primary sources (government, journals)

## Sources

Total sources consulted: 114

See `bibliography.bib` for citation-ready BibTeX entries.
